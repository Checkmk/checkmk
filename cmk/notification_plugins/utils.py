#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import base64
import os
import re
import sys
from abc import ABC, abstractmethod
from collections.abc import Callable, Container, Iterable
from dataclasses import dataclass
from email.utils import formataddr
from http.client import responses as http_responses
from quopri import encodestring
from typing import Any, NamedTuple, NoReturn

import requests
from requests import JSONDecodeError

from cmk.ccc import site

import cmk.utils.password_store
import cmk.utils.paths
from cmk.utils.escaping import escape, escape_permissive
from cmk.utils.html import (  # noqa: F401
    replace_state_markers as format_plugin_output,
)
from cmk.utils.http_proxy_config import deserialize_http_proxy_config
from cmk.utils.local_secrets import SiteInternalSecret
from cmk.utils.notify import find_wato_folder, NotificationContext
from cmk.utils.notify_types import PluginNotificationContext
from cmk.utils.paths import omd_root


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


def graph_url_from_context(context: PluginNotificationContext) -> str:
    base = _base_url(context)
    view_url = base + "/check_mk/view.py?"
    if context["WHAT"] == "HOST":
        return (
            view_url + f"siteopt={context['OMD_SITE']}&"
            f"view_name=host_graphs&"
            f"host={context['HOSTNAME']}"
        )
    return (
        view_url + f"siteopt={context['OMD_SITE']}&"
        f"view_name=service_graphs&"
        f"host={context['HOSTNAME']}&"
        f"service={context['SERVICEDESC']}"
    )


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

    def _escape_or_not_escape(context: PluginNotificationContext, varname: str, value: str) -> str:
        """currently we escape by default with a large list of exceptions.

        Next step is permissive escaping for certain fields..."""

        if varname in unescaped_variables:
            # HACK for HTML output of ps check
            if (
                varname == "LONGSERVICEOUTPUT"
                and context.get("SERVICECHECKCOMMAND") == "check_mk-ps"
            ):
                return value.replace("&bsol;", "\\")
            return value
        if varname in permissive_variables:
            return escape_permissive(value, escape_links=False)
        return escape(value)

    return {
        variable: _escape_or_not_escape(context, variable, value)
        for variable, value in context.items()
    }


def add_debug_output(template: str, context: PluginNotificationContext) -> str:
    ascii_output = ""
    html_output = "<table class=context>\n"
    elements = sorted(context.items())
    for varname, value in elements:
        ascii_output += f"{varname}={value}\n"
        html_output += (
            f"<tr><td class=varname>{varname}</td><td class=value>{escape(value)}</td></tr>\n"
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
def retrieve_from_passwordstore(parameter: str | list[str]) -> str:
    if isinstance(parameter, list):
        if "explicit_password" in parameter:
            value: str | None = parameter[-1]
        else:
            value = cmk.utils.password_store.extract(parameter[-2])
            if value is None:
                sys.stderr.write("Unable to retrieve password from passwordstore")
                sys.exit(2)
    else:
        # old valuespec style
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

    assert value is not None
    return value


def get_password_from_env_or_context(key: str, context: dict[str, str] | None = None) -> str:
    """
    Since 2.4 the passwords are stored in FormSpec format, this leads to
    multiple keys in the notification context
    """
    source = context if context else os.environ
    password_parameter_list = [source[k] for k in source if k.startswith(key)]
    return retrieve_from_passwordstore(password_parameter_list)


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
            proxies=deserialize_http_proxy_config(serialized_proxy_config).to_requests_proxies(),
            headers=headers,
            verify=verify,
            timeout=110,
        )
    except requests.exceptions.ProxyError:
        sys.stderr.write("Cannot connect to proxy: %s\n" % serialized_proxy_config)
        sys.exit(2)
    except requests.exceptions.Timeout:
        # Not expose the url in the error, as it might contain sensitive information
        sys.stderr.write("Connection timeout in notification plugin \n")
        sys.exit(2)

    return response


def process_by_status_code(
    response: requests.Response, success_code: int | Container[int] = 200
) -> int:
    status_code = response.status_code
    summary = f"{status_code}: {http_responses[status_code]}"

    if isinstance(success_code, int):
        if status_code == success_code:
            sys.stderr.write(summary)
            return 0
    elif status_code in success_code:
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
JsonOrText = dict | str


class ResponseMatcher(ABC):
    __slots__ = ()

    @abstractmethod
    def matches(self, response: requests.Response, body: JsonOrText) -> bool: ...

    def and_(self, other: "ResponseMatcher") -> "CombinedMatcher":
        return CombinedMatcher(matchers=[self, other])


@dataclass(frozen=True, slots=True)
class CombinedMatcher(ResponseMatcher):
    matchers: list[ResponseMatcher]

    def matches(self, response: requests.Response, body: JsonOrText) -> bool:
        return all(matcher.matches(response, body) for matcher in self.matchers)

    def and_(self, other: "ResponseMatcher") -> "CombinedMatcher":
        return CombinedMatcher(matchers=[*self.matchers, other])


@dataclass(frozen=True, slots=True)
class StatusCodeMatcher(ResponseMatcher):
    range: StatusCodeRange

    def __post_init__(self) -> None:
        if self.range[0] > self.range[1]:
            raise ValueError(f"Invalid range: {self.range[0]} - {self.range[1]}")

    def matches(self, response: requests.Response, body: JsonOrText) -> bool:
        return self.range[0] <= response.status_code <= self.range[1]


@dataclass(frozen=True, slots=True)
class JsonFieldMatcher(ResponseMatcher):
    field: str
    value: Any

    def matches(self, response: requests.Response, body: JsonOrText) -> bool:
        return isinstance(body, dict) and _get_details_from_json(body, self.field) == self.value


def _get_details_from_json(json_response: dict[str, Any], key: str) -> Any:
    if key in json_response:
        return json_response[key]

    for value in json_response.values():
        if isinstance(value, dict) and (result := _get_details_from_json(value, key)):
            return result
    return None


def process_by_matchers(
    response: requests.Response,
    matchers: Iterable[tuple[ResponseMatcher | StatusCodeRange, StateInfo]],
) -> NoReturn:
    status_code = response.status_code
    summary = f"{status_code}: {http_responses[status_code]}"
    details = ""

    try:
        body = response.json()
    except JSONDecodeError:
        body = response.text

    for matcher, state_info in matchers:
        if not isinstance(matcher, ResponseMatcher):
            matcher = StatusCodeMatcher(range=matcher)
        if matcher.matches(response, body):
            if state_info.type == "json":
                details = _get_details_from_json(body, state_info.title)
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
    elif notification_type in ["PROBLEM", "RECOVERY"]:
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


def pretty_notification_type(notification_type: str) -> str:
    if notification_type == "DOWNTIMESTART":
        return "Downtime Start"
    if notification_type == "DOWNTIMEEND":
        return "Downtime End"
    if notification_type == "DOWNTIMECANCELLED":
        return "Downtime Cancelled"
    if notification_type == "FLAPPINGSTART":
        return "Flapping Start"
    if notification_type == "FLAPPINGSTOP":
        return "Flapping Stop"
    if notification_type == "FLAPPINGDISABLED":
        return "Flapping Disabled"
    if notification_type.startswith("ALERTHANDLER"):
        if suffix := notification_type[12:].lstrip().title():
            return f"Alert Handler {suffix}"
        return "Alert Handler"
    return notification_type.title()


def pretty_state(state: str) -> str:
    if state == "OK":
        return state
    return state.title()


def _sanitize_filename(value: str) -> str:
    value = value.replace(" ", "_")
    # replace forbidden characters < > ? " : | \ / *
    for token in ("<", ">", "?", '"', ":", "|", "\\", "/", "*"):
        value = value.replace(token, "x%s" % ord(token))
    return value


class Graph(NamedTuple):
    filename: str
    data: bytes


def render_cmk_graphs(context: dict[str, str], raise_exception: bool = False) -> list[Graph]:
    if context["WHAT"] == "HOST":
        svc_desc = "_HOST_"
    else:
        svc_desc = context["SERVICEDESC"]

    request = requests.Request(
        "GET",
        f"http://localhost:{site.get_apache_port(omd_root)}/{os.environ['OMD_SITE']}/check_mk/ajax_graph_images.py",
        params={
            "host": context["HOSTNAME"],
            "service": svc_desc,
            "num_graphs": context["PARAMETER_GRAPHS_PER_NOTIFICATION"],
        },
        headers={"Authorization": f"InternalToken {SiteInternalSecret().secret.b64_str}"},
    ).prepare()

    timeout = 10
    try:
        response = requests.Session().send(
            request,
            timeout=timeout,
        )
    except requests.exceptions.ReadTimeout:
        if raise_exception:
            raise
        sys.stderr.write(f"ERROR: Timed out fetching graphs ({timeout} sec)\nURL: {request.url}\n")
        return []
    except Exception as e:
        if raise_exception:
            raise
        sys.stderr.write(f"ERROR: Failed to fetch graphs: {e}\nURL: {request.url}\n")
        return []

    try:
        base64_strings = response.json()
    except requests.exceptions.JSONDecodeError as e:
        if response.text == "":
            return []
        if raise_exception:
            raise
        sys.stderr.write(
            f"ERROR: Failed to decode graphs: {e}\nURL: {request.url}\nData: {response.text!r}\n"
        )
        return []

    file_prefix = _sanitize_filename(f"{context['HOSTNAME']}-{svc_desc}")
    return [
        Graph(filename=f"{file_prefix}-{i}.png", data=base64.b64decode(s))
        for i, s in enumerate(base64_strings)
    ]
