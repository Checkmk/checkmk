#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import re
import requests
import socket
import subprocess
import sys

from email.utils import formataddr, formatdate, parseaddr
from html import escape as html_escape
from http.client import responses as http_responses
from quopri import encodestring
from typing import Dict, List, NamedTuple, Optional, Tuple

import cmk.utils.password_store
import cmk.utils.paths
import cmk.utils.version as cmk_version
from cmk.utils.notify import find_wato_folder
from cmk.utils.store import load_text_from_file


def collect_context() -> Dict[str, str]:
    return {
        var[7:]: value  #
        for var, value in os.environ.items()
        if var.startswith("NOTIFY_")
    }


def format_link(template: str, url: str, text: str) -> str:
    return template % (url, text) if url else text


def format_address(display_name: str, email_address: str) -> str:
    """
    Returns an email address with an optional display name suitable for an email header like From or Reply-To.
    The function handles the following cases:

      * If an empty display name is given, only the email address is returned.
      * If a display name is given a, string of the form "display_name <email_address>" is returned.
      * If the display name contains non ASCII characters, it is converted to an encoded word (see RFC2231).
      * If the display_name contains special characters like e.g. '.' the display string is enclosed in quotes.
      * If the display_name contains backslashes or quotes, a backslash is prepended before these characters.
    """
    if not email_address:
        return ''

    try:
        display_name.encode('ascii')
    except UnicodeEncodeError:
        display_name = u'=?utf-8?q?%s?=' % encodestring(
            display_name.encode('utf-8')).decode('ascii')
    return formataddr((display_name, email_address))


def default_from_address():
    environ_default = os.environ.get("OMD_SITE", "checkmk") + "@" + socket.getfqdn()
    if cmk_version.is_cma():
        return load_text_from_file("/etc/nullmailer/default-from",
                                   environ_default).replace('\n', '')

    return environ_default


def _base_url(context: Dict[str, str]) -> str:
    if context.get("PARAMETER_URL_PREFIX"):
        url_prefix = context["PARAMETER_URL_PREFIX"]
    elif context.get("PARAMETER_URL_PREFIX_MANUAL"):
        url_prefix = context["PARAMETER_URL_PREFIX_MANUAL"]
    elif context.get("PARAMETER_URL_PREFIX_AUTOMATIC") == "http":
        url_prefix = "http://%s/%s" % (context["MONITORING_HOST"], context["OMD_SITE"])
    elif context.get("PARAMETER_URL_PREFIX_AUTOMATIC") == "https":
        url_prefix = "https://%s/%s" % (context["MONITORING_HOST"], context["OMD_SITE"])
    else:
        url_prefix = ''

    return re.sub('/check_mk/?', '', url_prefix, count=1)


def host_url_from_context(context: Dict[str, str]) -> str:
    base = _base_url(context)
    return base + context['HOSTURL'] if base else ''


def service_url_from_context(context: Dict[str, str]) -> str:
    base = _base_url(context)
    return base + context['SERVICEURL'] if base and context['WHAT'] == 'SERVICE' else ''


# There is common code with cmk/gui/view_utils:format_plugin_output(). Please check
# whether or not that function needs to be changed too
# TODO(lm): Find a common place to unify this functionality.
def format_plugin_output(output):
    ok_marker = '<b class="stmarkOK">OK</b>'
    warn_marker = '<b class="stmarkWARNING">WARN</b>'
    crit_marker = '<b class="stmarkCRITICAL">CRIT</b>'
    unknown_marker = '<b class="stmarkUNKNOWN">UNKN</b>'

    output = output.replace("(!)", warn_marker) \
              .replace("(!!)", crit_marker) \
              .replace("(?)", unknown_marker) \
              .replace("(.)", ok_marker)

    return output


def html_escape_context(context):
    unescaped_variables = {
        'CONTACTALIAS',
        'CONTACTNAME',
        'CONTACTEMAIL',
        'PARAMETER_INSERT_HTML_SECTION',
        'PARAMETER_BULK_SUBJECT',
        'PARAMETER_HOST_SUBJECT',
        'PARAMETER_SERVICE_SUBJECT',
        'PARAMETER_FROM_ADDRESS',
        'PARAMETER_FROM_DISPLAY_NAME',
        'PARAMETER_REPLY_TO',
        'PARAMETER_REPLY_TO_ADDRESS',
        'PARAMETER_REPLY_TO_DISPLAY_NAME',
    }
    if context.get("SERVICE_ESCAPE_PLUGIN_OUTPUT") == "0":
        unescaped_variables |= {"SERVICEOUTPUT", "LONGSERVICEOUTPUT"}
    if context.get("HOST_ESCAPE_PLUGIN_OUTPUT") == "0":
        unescaped_variables |= {"HOSTOUTPUT", "LONGHOSTOUTPUT"}

    for variable, value in context.items():
        if variable not in unescaped_variables:
            context[variable] = html_escape(value)


def add_debug_output(template, context):
    ascii_output = ""
    html_output = "<table class=context>\n"
    elements = sorted(context.items())
    for varname, value in elements:
        ascii_output += "%s=%s\n" % (varname, value)
        html_output += "<tr><td class=varname>%s</td><td class=value>%s</td></tr>\n" % (
            varname, html_escape(value))
    html_output += "</table>\n"
    return template.replace("$CONTEXT_ASCII$", ascii_output).replace("$CONTEXT_HTML$", html_output)


def substitute_context(template, context):
    # First replace all known variables
    for varname, value in context.items():
        template = template.replace('$' + varname + '$', value)

    # Debugging of variables. Create content only on demand
    if "$CONTEXT_ASCII$" in template or "$CONTEXT_HTML$" in template:
        template = add_debug_output(template, context)

    if re.search(r"\$[A-Z_][A-Z_0-9]*\$", template):
        # Second pass to replace nested variables inside e.g. SERVICENOTESURL
        for varname, value in context.items():
            template = template.replace('$' + varname + '$', value)

    # Remove the rest of the variables and make them empty
    template = re.sub(r"\$[A-Z_][A-Z_0-9]*\$", "", template)
    return template


###############################################################################
# Mail


def set_mail_headers(target, subject, from_address, reply_to, mail):
    mail['Date'] = formatdate(localtime=True)
    mail['Subject'] = subject
    mail['To'] = target

    # Set a few configurable headers
    if from_address:
        mail['From'] = from_address

    if reply_to:
        mail['Reply-To'] = reply_to
    elif len(target.split(",")) > 1:
        mail['Reply-To'] = target

    return mail


def send_mail_sendmail(m, target, from_address):
    cmd = [_sendmail_path()]
    if from_address:
        # sendmail of the appliance can not handle "FULLNAME <my@mail.com>" format
        # TODO Currently we only see problems on appliances, so we just change
        # that handling for now.
        # If we see problems on other nullmailer sendmail implementations, we
        # could parse the man page for sendmail and see, if it contains "nullmailer" to
        # determine if nullmailer is used
        if cmk_version.is_cma():
            sender_full_name, sender_address = parseaddr(from_address)
            if sender_full_name:
                cmd += ['-F', sender_full_name]
            cmd += ["-f", sender_address]
        else:
            cmd += ['-F', from_address, "-f", from_address]
    cmd += ["-i", target]

    try:
        p = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            encoding="utf-8",
        )
    except OSError:
        raise Exception("Failed to send the mail: /usr/sbin/sendmail is missing")

    p.communicate(input=m.as_string())
    if p.returncode != 0:
        raise Exception("sendmail returned with exit code: %d" % p.returncode)

    sys.stdout.write("Spooled mail to local mail transmission agent\n")
    return 0


def _sendmail_path() -> str:
    # We normally don't deliver the sendmail command, but our notification integration tests
    # put some fake sendmail command into the site to prevent actual sending of mails.

    for path in [
            "%s/local/bin/sendmail" % cmk.utils.paths.omd_root,
            "/usr/sbin/sendmail",
    ]:
        if os.path.exists(path):
            return path

    raise Exception("Failed to send the mail: /usr/sbin/sendmail is missing")


def read_bulk_contexts() -> Tuple[Dict[str, str], List[Dict[str, str]]]:
    parameters = {}
    contexts = []
    in_params = True

    # First comes a section with global variables
    for line in sys.stdin:
        line = line.strip()
        if not line:
            in_params = False
            context: Dict[str, str] = {}
            contexts.append(context)
        else:
            try:
                key, value = line.split("=", 1)
                value = value.replace("\1", "\n")
            except ValueError:
                sys.stderr.write("Invalid line '%s' in bulked notification context\n" % line)
                continue

            if in_params:
                parameters[key] = value
            else:
                context[key] = value

    return parameters, contexts


def get_bulk_notification_subject(contexts, hosts):
    hosts = list(hosts)
    bulk_subject = None
    folder = None
    bulk_context = {}
    for context in contexts:
        if context.get("PARAMETER_BULK_SUBJECT"):
            bulk_context = context
            bulk_subject = context["PARAMETER_BULK_SUBJECT"]
            folder = find_wato_folder(context)
            break

    if bulk_subject:
        subject = bulk_subject
    elif len(hosts) == 1:
        subject = "Check_MK: $COUNT_NOTIFICATIONS$ notifications for %s" % hosts[0]
    else:
        subject = "Check_MK: $COUNT_NOTIFICATIONS$ notifications for $COUNT_HOSTS$ hosts"

    if "$FOLDER$" in subject and folder is not None:
        subject = subject.replace("$FOLDER$", folder)
    if "$COUNT_NOTIFICATIONS$" in subject:
        subject = subject.replace("$COUNT_NOTIFICATIONS$", str(len(contexts)))
    if "$COUNT_HOSTS$" in subject:
        subject = subject.replace("$COUNT_HOSTS$", str(len(hosts)))

    subject = substitute_context(subject, bulk_context)
    return subject


#################################################################################################
# REST
def retrieve_from_passwordstore(parameter):
    value = parameter.split()

    if len(value) == 2:
        if value[0] == 'store':
            value = cmk.utils.password_store.extract(value[1])
        else:
            value = value[1]
    else:
        value = value[0]

    return value


def post_request(message_constructor, url=None, headers=None):
    context = collect_context()

    if not url:
        url = retrieve_from_passwordstore(context.get("PARAMETER_WEBHOOK_URL"))
    proxy_url = context.get("PARAMETER_PROXY_URL")
    proxies = {"http": proxy_url, "https": proxy_url} if proxy_url is not None else None

    verify: bool = True
    if "PARAMETER_IGNORE_SSL" in context:
        verify = False

    try:
        response = requests.post(url=url,
                                 json=message_constructor(context),
                                 proxies=proxies,
                                 headers=headers,
                                 verify=verify)
    except requests.exceptions.ProxyError:
        sys.stderr.write("Cannot connect to proxy: %s\n" % proxy_url)
        sys.exit(2)

    return response


def process_by_status_code(response: requests.models.Response, success_code: int = 200):
    status_code = response.status_code
    summary = f"{status_code}: {http_responses[status_code]}"

    if status_code == success_code:
        sys.stderr.write(summary)
        sys.exit(0)
    elif 500 <= status_code <= 599:
        sys.stderr.write(summary)
        sys.exit(1)  # Checkmk gives a retry if exited with 1. Makes sense in case of a server error
    else:
        sys.stderr.write(f"Failed to send notification.\nResponse: {response.text}\n{summary}")
        sys.exit(2)


StateInfo = NamedTuple('StateInfo', [('state', int), ('type', str), ('title', str)])
StatusCodeRange = Tuple[int, int]


def process_by_result_map(response: requests.models.Response, result_map: Dict[StatusCodeRange,
                                                                               StateInfo]):
    def get_details_from_json(json_response, what):
        for key, value in json_response.items():
            if key == what:
                return value
            if isinstance(value, dict):
                result = get_details_from_json(value, what)
                if result:
                    return result

    status_code = response.status_code
    summary = f"{status_code}: {http_responses[status_code]}"
    details = ""

    for status_code_range, state_info in result_map.items():
        if status_code_range[0] <= status_code <= status_code_range[1]:
            if state_info.type == 'json':
                details = response.json()
                details = get_details_from_json(details, state_info.title)
            elif state_info.type == 'str':
                details = response.text

            sys.stderr.write(f"{state_info.title}: {details}\n{summary}\n")
            sys.exit(state_info.state)

    sys.stderr.write(f"Details for Status Code are not defined\n{summary}\n")
    sys.exit(3)


def get_sms_message_from_context(raw_context: Dict[str, str]) -> str:
    notification_type = raw_context["NOTIFICATIONTYPE"]
    max_len = 160
    message = raw_context["HOSTNAME"] + " "
    if raw_context["WHAT"] == "SERVICE":
        if notification_type in ["PROBLEM", "RECOVERY"]:
            message += raw_context["SERVICESTATE"][:2] + " "
            avail_len = max_len - len(message)
            message += raw_context["SERVICEDESC"][:avail_len] + " "
            avail_len = max_len - len(message)
            message += raw_context["SERVICEOUTPUT"][:avail_len]
        else:
            message += raw_context["SERVICEDESC"]
    else:
        if notification_type in ["PROBLEM", "RECOVERY"]:
            message += "is " + raw_context["HOSTSTATE"]

    if notification_type.startswith("FLAP"):
        if "START" in notification_type:
            message += " Started Flapping"
        else:
            message += " Stopped Flapping"

    elif notification_type.startswith("DOWNTIME"):
        what = notification_type[8:].title()
        message += " Downtime " + what
        message += " " + raw_context["NOTIFICATIONCOMMENT"]

    elif notification_type == "ACKNOWLEDGEMENT":
        message += " Acknowledged"
        message += " " + raw_context["NOTIFICATIONCOMMENT"]

    elif notification_type == "CUSTOM":
        message += " Custom Notification"
        message += " " + raw_context["NOTIFICATIONCOMMENT"]

    return message


def quote_message(message: str, max_length: Optional[int] = None):
    if max_length:
        return "'" + message.replace("'", "'\"'\"'")[:max_length - 2] + "'"
    return "'" + message.replace("'", "'\"'\"'") + "'"
