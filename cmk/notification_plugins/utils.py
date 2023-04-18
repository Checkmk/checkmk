#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import re
import sys
from collections.abc import Callable, Iterable
from email.utils import formataddr
from http.client import responses as http_responses
from quopri import encodestring
from typing import Any, NamedTuple, NoReturn

import requests

import cmk.utils.password_store
import cmk.utils.paths
from cmk.utils.escaping import escape, escape_permissive
from cmk.utils.http_proxy_config import deserialize_http_proxy_config
from cmk.utils.misc import typeshed_issue_7724
from cmk.utils.notify import find_wato_folder, NotificationContext
from cmk.utils.type_defs import PluginNotificationContext

from cmk.utils.html import (  # noqa: F401  # pylint: disable=unused-import  # isort:skip
    replace_state_markers as format_plugin_output,
)


def collect_context() -> PluginNotificationContext:
    return {var[7:]: value for var, value in os.environ.items() if var.startswith("NOTIFY_")}


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
        return ""

    try:
        display_name.encode("ascii")
    except UnicodeEncodeError:
        display_name = "=?utf-8?q?%s?=" % encodestring(display_name.encode("utf-8")).decode("ascii")
    return formataddr((display_name, email_address))


def _base_url(context: PluginNotificationContext) -> str:
    if context.get("PARAMETER_URL_PREFIX"):
        url_prefix = context["PARAMETER_URL_PREFIX"]
    elif context.get("PARAMETER_URL_PREFIX_MANUAL"):
        url_prefix = context["PARAMETER_URL_PREFIX_MANUAL"]
    elif context.get("PARAMETER_URL_PREFIX_AUTOMATIC") == "http":
        url_prefix = "http://{}/{}".format(context["MONITORING_HOST"], context["OMD_SITE"])
    elif context.get("PARAMETER_URL_PREFIX_AUTOMATIC") == "https":
        url_prefix = "https://{}/{}".format(context["MONITORING_HOST"], context["OMD_SITE"])
    else:
        url_prefix = ""

    return re.sub("/check_mk/?", "", url_prefix, count=1)


def host_url_from_context(context: PluginNotificationContext) -> str:
    base = _base_url(context)
    return base + context["HOSTURL"] if base else ""


def service_url_from_context(context: PluginNotificationContext) -> str:
    base = _base_url(context)
    return base + context["SERVICEURL"] if base and context["WHAT"] == "SERVICE" else ""


def html_escape_context(context: PluginNotificationContext) -> PluginNotificationContext:
    unescaped_variables = {
        "CONTACTALIAS",
        "CONTACTNAME",
        "CONTACTEMAIL",
        "PARAMETER_BULK_SUBJECT",
        "PARAMETER_HOST_SUBJECT",
        "PARAMETER_SERVICE_SUBJECT",
        "PARAMETER_FROM_ADDRESS",
        "PARAMETER_FROM_DISPLAY_NAME",
        "PARAMETER_REPLY_TO",
        "PARAMETER_REPLY_TO_ADDRESS",
        "PARAMETER_REPLY_TO_DISPLAY_NAME",
        "SERVICEDESC",
    }
    permissive_variables = {
        "PARAMETER_INSERT_HTML_SECTION",
    }
    if context.get("SERVICE_ESCAPE_PLUGIN_OUTPUT") == "0":
        unescaped_variables |= {"SERVICEOUTPUT", "LONGSERVICEOUTPUT"}
    if context.get("HOST_ESCAPE_PLUGIN_OUTPUT") == "0":
        unescaped_variables |= {"HOSTOUTPUT", "LONGHOSTOUTPUT"}

    def _escape_or_not_escape(varname: str, value: str) -> str:
        """currently we escape by default with a large list of exceptions.

        Next step is permissive escaping for certain fields..."""

        if varname in unescaped_variables:
            return value
        if varname in permissive_variables:
            return escape_permissive(value, escape_links=False)
        return escape(value)

    return {variable: _escape_or_not_escape(variable, value) for variable, value in context.items()}


def add_debug_output(template: str, context: PluginNotificationContext) -> str:
    ascii_output = ""
    html_output = "<table class=context>\n"
    elements = sorted(context.items())
    for varname, value in elements:
        ascii_output += f"{varname}={value}\n"
        html_output += "<tr><td class=varname>{}</td><td class=value>{}</td></tr>\n".format(
            varname,
            escape(value),
        )
    html_output += "</table>\n"
    return template.replace("$CONTEXT_ASCII$", ascii_output).replace("$CONTEXT_HTML$", html_output)


def substitute_context(template: str, context: PluginNotificationContext) -> str:
    # First replace all known variables
    for varname, value in context.items():
        template = template.replace("$" + varname + "$", value)

    # Debugging of variables. Create content only on demand
    if "$CONTEXT_ASCII$" in template or "$CONTEXT_HTML$" in template:
        template = add_debug_output(template, context)

    if re.search(r"\$[A-Z_][A-Z_0-9]*\$", template):
        # Second pass to replace nested variables inside e.g. SERVICENOTESURL
        for varname, value in context.items():
            template = template.replace("$" + varname + "$", value)

    # Remove the rest of the variables and make them empty
    template = re.sub(r"\$[A-Z_][A-Z_0-9]*\$", "", template)
    return template


###############################################################################
# Mail


def read_bulk_contexts() -> tuple[dict[str, str], list[dict[str, str]]]:
    parameters = {}
    contexts = []
    in_params = True

    # First comes a section with global variables
    for line in sys.stdin:
        line = line.strip()
        if not line:
            in_params = False
            context: PluginNotificationContext = {}
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


def get_bulk_notification_subject(contexts: list[dict[str, str]], hosts: Iterable) -> str:
    hosts = list(hosts)
    bulk_subject = None
    folder = None
    bulk_context = {}
    for context in contexts:
        if context.get("PARAMETER_BULK_SUBJECT"):
            bulk_context = context
            bulk_subject = context["PARAMETER_BULK_SUBJECT"]
            folder = find_wato_folder(NotificationContext(context))
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
def retrieve_from_passwordstore(parameter: str) -> str:
    values = parameter.split()

    if len(values) == 2:
        if values[0] == "store":
            value = cmk.utils.password_store.extract(values[1])
            if value is None:
                sys.stderr.write("Unable to retrieve password from passwordstore")
                sys.exit(2)
        else:
            value = values[1]
    else:
        value = values[0]

    return value


def post_request(
    message_constructor: Callable[[dict[str, str]], dict[str, str | object]],
    url: str | None = None,
    headers: dict[str, str] | None = None,
) -> requests.Response:
    context = collect_context()

    if not url:
        url = retrieve_from_passwordstore(context["PARAMETER_WEBHOOK_URL"])
        if url is None:
            sys.stderr.write("No URL was retrieved from passwordstore")
            sys.exit(2)

    serialized_proxy_config = context.get("PARAMETER_PROXY_URL")

    verify: bool = True
    if "PARAMETER_IGNORE_SSL" in context:
        verify = False

    try:
        response = requests.post(
            url=url,
            json=message_constructor(context),
            proxies=typeshed_issue_7724(
                deserialize_http_proxy_config(serialized_proxy_config).to_requests_proxies()
            ),
            headers=headers,
            verify=verify,
        )
    except requests.exceptions.ProxyError:
        sys.stderr.write("Cannot connect to proxy: %s\n" % serialized_proxy_config)
        sys.exit(2)

    return response


def process_by_status_code(response: requests.Response, success_code: int = 200) -> int:
    status_code = response.status_code
    summary = f"{status_code}: {http_responses[status_code]}"

    if status_code == success_code:
        sys.stderr.write(summary)
        return 0
    if 500 <= status_code <= 599:
        sys.stderr.write(summary)
        return 1  # Checkmk gives a retry if exited with 1. Makes sense in case of a server error
    sys.stderr.write(f"Failed to send notification.\nResponse: {response.text}\n{summary}")
    return 2


class StateInfo(NamedTuple):
    state: int
    type: str
    title: str


StatusCodeRange = tuple[int, int]


def process_by_result_map(
    response: requests.Response, result_map: dict[StatusCodeRange, StateInfo]
) -> NoReturn:
    def get_details_from_json(json_response: dict[str, Any], what: str) -> Any:
        if what in json_response:
            return json_response[what]

        for value in json_response.values():
            if isinstance(value, dict):
                result = get_details_from_json(value, what)
                if result:
                    return result
        return None

    status_code = response.status_code
    summary = f"{status_code}: {http_responses[status_code]}"
    details = ""

    for status_code_range, state_info in result_map.items():
        if status_code_range[0] <= status_code <= status_code_range[1]:
            if state_info.type == "json":
                details = get_details_from_json(response.json(), state_info.title)
            elif state_info.type == "str":
                details = response.text

            sys.stderr.write(f"{state_info.title}: {details}\n{summary}\n")
            sys.exit(state_info.state)

    sys.stderr.write(f"Details for Status Code are not defined\n{summary}\n")
    sys.exit(3)


# TODO this will be used by the smstools and the sms via IP scripts later
def get_sms_message_from_context(raw_context: PluginNotificationContext) -> str:
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


def quote_message(message: str, max_length: int | None = None) -> str:
    if max_length:
        return "'" + message.replace("'", "'\"'\"'")[: max_length - 2] + "'"
    return "'" + message.replace("'", "'\"'\"'") + "'"
