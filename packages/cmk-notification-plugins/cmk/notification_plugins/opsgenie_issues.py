#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pprint import pformat
from typing import NoReturn
from urllib.parse import quote

import requests
import urllib3
from requests.adapters import HTTPAdapter
from requests.utils import get_environ_proxies, select_proxy
from urllib3.util import Retry

from cmk.ccc.jsontype import JsonPayload
from cmk.events.notify_types import PluginNotificationContext
from cmk.notification_plugins import utils
from cmk.notification_plugins.utils import get_password_from_env_or_context
from cmk.utils.http_proxy_config import (
    deserialize_http_proxy_config,
    HTTPProxyConfig,
    redact_proxy_url,
)
from cmk.utils.macros import replace_macros_in_str
from cmk.utils.paths import trusted_ca_file

_DEFAULT_URL = "https://api.opsgenie.com"
_BY_ALIAS = {"identifierType": "alias"}
_BY_ID = {"identifierType": "id"}
# Same policy as the former opsgenie-sdk: up to 5 retries on 429, 500, 502-599
# and connection errors, about 15 s of backoff in total, Retry-After ignored.
_RETRY = Retry(
    total=5,
    backoff_factor=0.5,
    status_forcelist=(429, 500, *range(502, 600)),
    allowed_methods=None,
    respect_retry_after_header=False,
    raise_on_status=False,
)


@dataclass(frozen=True)
class ExistingAlert:
    id: str
    message: str
    description: str


def _alert_path(identifier: str, action: str = "") -> str:
    return f"/v2/alerts/{quote(identifier, safe='')}{action}"


# https://docs.opsgenie.com/docs/alert-api
class Connector:
    def __init__(
        self, api_key: str, host_url: str | None, proxy: HTTPProxyConfig, ignore_ssl: bool
    ) -> None:
        self._base_url = (host_url or _DEFAULT_URL).rstrip("/")
        self._session = requests.Session()
        self._session.headers["Authorization"] = f"GenieKey {api_key}"
        self._session.mount(self._base_url, HTTPAdapter(max_retries=_RETRY))
        # Proxies and verify are passed per request, session defaults would lose
        # against the environment (HTTPS_PROXY, REQUESTS_CA_BUNDLE).
        self._proxies = proxy.to_requests_proxies()
        if used_proxy := select_proxy(
            self._base_url, self._proxies or get_environ_proxies(self._base_url)
        ):
            sys.stdout.write(f"Using proxy: {redact_proxy_url(used_proxy)}\n")

        self._verify: bool | str
        if ignore_ssl:
            sys.stdout.write("Ignoring SSL certificate verification\n")
            self._verify = False
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        else:
            sys.stdout.write(f"Using trust store: {trusted_ca_file}\n")
            self._verify = str(trusted_ca_file)

        sys.stdout.flush()

    def _send(
        self,
        api_call_name: str,
        method: str,
        path: str,
        body: Mapping[str, JsonPayload] | None,
        params: Mapping[str, str | None],
    ) -> requests.Response:
        try:
            return self._session.request(
                method,
                self._base_url + path,
                json=None if body is None else {k: v for k, v in body.items() if v is not None},
                params=params,
                proxies=self._proxies,
                verify=self._verify,
                timeout=110,
            )
        except requests.exceptions.RequestException as e:
            sys.stderr.write(f"Opsgenie API call {api_call_name} failed: {e}\n")
            sys.exit(1)

    def _request(
        self,
        api_call_name: str,
        method: str,
        path: str,
        success: str,
        *,
        params: Mapping[str, str | None],
        body: Mapping[str, JsonPayload] | None = None,
    ) -> None:
        response = self._send(api_call_name, method, path, body, params)
        if not response.ok:
            _abort(api_call_name, response)
        request_id = _json_object(response).get("requestId", "?")
        sys.stdout.write(f"Request id: {request_id}, successfully {success}.\n")

    def get_existing_alert(self, alias: str) -> ExistingAlert | None:
        response = self._send("get_alert", "GET", _alert_path(alias), None, _BY_ALIAS)
        if response.status_code == requests.codes.not_found:
            sys.stdout.write(f'Alert with alias "{alias}" not found.\n')
            return None
        if not response.ok:
            _abort("get_alert", response)

        data = _json_object(response).get("data")
        alert = data if isinstance(data, Mapping) else {}
        if not (alert_id := alert.get("id")):
            sys.stdout.write(f'Alert with alias "{alias}" not found in response.\n')
            return None
        existing = ExistingAlert(
            id=str(alert_id),
            message=str(alert.get("message", "")),
            description=str(alert.get("description", "")),
        )
        sys.stdout.write(f'Alert with alias "{alias}" found, id: {existing.id}.\n')
        return existing

    def handle_alert_update_description(self, identifier: str, description: str) -> None:
        self._request(
            "update_alert_description",
            "PUT",
            _alert_path(identifier, "/description"),
            "updated alert description",
            body={"description": description},
            params=_BY_ID,
        )

    def handle_alert_update_message(self, identifier: str, message: str) -> None:
        self._request(
            "update_alert_message",
            "PUT",
            _alert_path(identifier, "/message"),
            "updated alert message",
            body={"message": message},
            params=_BY_ID,
        )

    def handle_alert_creation(self, payload: Mapping[str, JsonPayload]) -> None:
        self._request(
            "create_alert", "POST", "/v2/alerts", "created alert", body=payload, params={}
        )

    def handle_alert_deletion(self, alias: str, payload: Mapping[str, JsonPayload]) -> None:
        self._request(
            "close_alert",
            "POST",
            _alert_path(alias, "/close"),
            "closed alert",
            params=_BY_ALIAS,
            body=payload,
        )

    def handle_alert_ack(self, alias: str, payload: Mapping[str, JsonPayload]) -> None:
        self._request(
            "acknowledge_alert",
            "POST",
            _alert_path(alias, "/acknowledge"),
            "acknowledged alert",
            params=_BY_ALIAS,
            body=payload,
        )

    def add_note(self, alias: str, payload: Mapping[str, JsonPayload]) -> None:
        self._request(
            "add_note",
            "POST",
            _alert_path(alias, "/notes"),
            "added note",
            params=_BY_ALIAS,
            body=payload,
        )

    def add_tags(self, alias: str, payload: Mapping[str, JsonPayload]) -> None:
        self._request(
            "add_tags",
            "POST",
            _alert_path(alias, "/tags"),
            "added tags",
            params=_BY_ALIAS,
            body=payload,
        )

    def remove_tags(
        self, alias: str, tags: list[str], source: str | None, user: str | None, note: str | None
    ) -> None:
        self._request(
            "remove_tags",
            "DELETE",
            _alert_path(alias, "/tags"),
            "removed tags",
            params={
                **_BY_ALIAS,
                "tags": ",".join(tags),
                "source": source,
                "user": user,
                "note": note,
            },
        )


def _json_object(response: requests.Response) -> Mapping[str, object]:
    try:
        payload = response.json()
    except requests.exceptions.JSONDecodeError:
        return {}
    return payload if isinstance(payload, Mapping) else {}


def _abort(api_call_name: str, response: requests.Response) -> NoReturn:
    sys.stderr.write(
        f"Opsgenie API call {api_call_name} failed: {response.status_code} {response.reason}\n"
        f"Response: {response.text}\n"
    )
    retry_later = (
        response.status_code == requests.codes.too_many_requests or response.status_code >= 500
    )
    sys.exit(1 if retry_later else 2)


def _get_connector(context: PluginNotificationContext) -> Connector:
    if "PARAMETER_PASSWORD_1" not in context:
        sys.stderr.write("API key not set\n")
        sys.exit(2)

    api_key = get_password_from_env_or_context(
        key="PARAMETER_PASSWORD",
        context=context,
    )
    return Connector(
        api_key,
        context.get("PARAMETER_URL"),
        deserialize_http_proxy_config(context.get("PARAMETER_PROXY_URL")),
        ignore_ssl="PARAMETER_IGNORE_SSL" in context,
    )


def _get_alias(context: PluginNotificationContext) -> str:
    if context["WHAT"] == "HOST":
        return (
            f"HOST_PROBLEM_ID: {context['LASTHOSTPROBLEMID']}"
            if context["HOSTPROBLEMID"] == "0"
            else f"HOST_PROBLEM_ID: {context['HOSTPROBLEMID']}"
        )

    return (
        f"SVC_PROBLEM_ID: {context['LASTSERVICEPROBLEMID']}"
        if context["SERVICEPROBLEMID"] == "0"
        else f"SVC_PROBLEM_ID: {context['SERVICEPROBLEMID']}"
    )


def _requires_integration_team(notification_type: str, integration_team: str | None) -> None:
    # The integration that creates the alert isn't added to the "visible to" list by default.
    # This means that some API calls will fail due to missing permissions.
    # To avoid errors or warnings in both the Checkmk and Opsgenie logs,
    # we require the integration team to be set for those calls.
    # (Unfortunately there is no way to query the team name the integration belongs to)
    if not integration_team:
        sys.stdout.write(
            f"Notification type {notification_type} requires integration team to be set\n"
        )
        sys.exit(0)


def _get_extra_properties(context: PluginNotificationContext) -> dict[str, str]:
    all_elements: dict[str, tuple[str, str]] = {
        "omdsite": ("Site ID", os.environ["OMD_SITE"]),
        "hosttags": ("Tags of the Host", "\n".join(context.get("HOST_TAGS", "").split())),
        "address": ("IP address of host", context.get("HOSTADDRESS", "")),
        "abstime": ("Absolute time of alert", context.get("LONGDATETIME", "")),
        "reltime": ("Relative time of alert", context.get("LASTHOSTSTATECHANGE_REL", "")),
        "longoutput": ("Additional plug-in output", context.get("LONGSERVICEOUTPUT$", "")),
        "ack_author": ("Acknowledgement author", context.get("SERVICEACKAUTHOR", "")),
        "ack_comment": ("Acknowledgement comment", context.get("SERVICEACKCOMMENT", "")),
        "notification_author": ("Notification Author", context.get("NOTIFICATIONAUTHOR", "")),
        "notification_comment": ("Notification comment", context.get("NOTIFICATIONCOMMENT", "")),
        "perfdata": ("Metrics", context.get("HOSTPERFDATA", "")),
        "notesurl": ("Custom host/service notes URL", context.get("SERVICENOTESURL", "")),
        "context": ("Complete variable list (for testing)", str(pformat(context))),
    }

    subset_of_elements: dict[str, str] = {
        all_elements[param][0]: all_elements[param][1]
        for param in context.get("PARAMETER_ELEMENTSS", "").split()
        if all_elements[param][1]
    }
    return subset_of_elements


def _get_description_and_message(context: PluginNotificationContext) -> tuple[str, str]:
    if context["WHAT"] == "HOST":
        tmpl_host_msg: str = "Check_MK: $HOSTNAME$ - $HOSTSHORTSTATE$"
        tmpl_host_desc: str = """Host: $HOSTNAME$
    Event:    $EVENT_TXT$
    Output:   $HOSTOUTPUT$
    Perfdata: $HOSTPERFDATA$
    $LONGHOSTOUTPUT$
    """
        desc = context.get("PARAMETER_HOST_DESC") or tmpl_host_desc
        msg = context.get("PARAMETER_HOST_MSG") or tmpl_host_msg
    else:
        tmpl_svc_msg = "Check_MK: $HOSTNAME$/$SERVICEDESC$ $SERVICESHORTSTATE$"
        tmpl_svc_desc = """Host: $HOSTNAME$
    Service:  $SERVICEDESC$
    Event:    $EVENT_TXT$
    Output:   $SERVICEOUTPUT$
    Perfdata: $SERVICEPERFDATA$
    $LONGSERVICEOUTPUT$
    """
        desc = context.get("PARAMETER_SVC_DESC") or tmpl_svc_desc
        msg = context.get("PARAMETER_SVC_MSG") or tmpl_svc_msg

    desc = utils.substitute_context(desc, context)
    msg = utils.substitute_context(msg, context)

    return desc, msg


def _handle_problem(
    context: PluginNotificationContext,
    connector: Connector,
    alias: str,
    integration_team: str | None,
    alert_source: str | None,
    owner: str | None,
) -> None:
    entity_value = context.get("PARAMETER_ENTITY", "")
    note_created = context.get("PARAMETER_NOTE_CREATED") or "Alert created by Check_MK"
    priority = context.get("PARAMETER_PRIORITY", "P3")
    desc, msg = _get_description_and_message(context)

    actions_list: list[str] = []
    if context.get("PARAMETER_ACTIONSS"):
        actions_list = context.get("PARAMETER_ACTIONSS", "").split(" ")

    tags_list: list[str] = []
    if (tags := context.get("PARAMETER_TAGSS")) is not None:
        tags_list = replace_macros_in_str(
            string=tags, macro_mapping={f"${k}$": v for k, v in context.items()}
        ).split()

    teams_list: list[dict[str, str]] = []
    if context.get("PARAMETER_TEAMSS"):
        teams_list = [
            {"name": str(context[k]), "type": "team"}
            for k in context
            if k.startswith("PARAMETER_TEAMS_")
        ]

    visible_to: list[dict[str, str]] = list(teams_list)
    if integration_team and not any(t["name"] == integration_team for t in visible_to):
        visible_to.append({"name": integration_team, "type": "team"})

    existing_alert = connector.get_existing_alert(alias) if integration_team else None

    connector.handle_alert_creation(
        {
            "note": note_created,
            "actions": actions_list,
            "description": desc,
            "message": msg,
            "priority": priority,
            "responders": teams_list,
            "visibleTo": visible_to,
            "tags": tags_list,
            "entity": entity_value,
            "source": alert_source,
            "alias": alias,
            "user": owner,
            "details": _get_extra_properties(context),
        }
    )

    if existing_alert:
        if existing_alert.description != desc:
            connector.handle_alert_update_description(existing_alert.id, desc)
        if existing_alert.message != msg:
            connector.handle_alert_update_message(existing_alert.id, msg)


def _handle_acknowledgement(
    context: PluginNotificationContext,
    connector: Connector,
    alias: str,
    alert_source: str | None,
) -> None:
    if context["WHAT"] == "HOST":
        ack_author = context["HOSTACKAUTHOR"]
        ack_comment = context["HOSTACKCOMMENT"]
    else:
        ack_author = context["SERVICEACKAUTHOR"]
        ack_comment = context["SERVICEACKCOMMENT"]
    connector.handle_alert_ack(
        alias, {"source": alert_source, "user": ack_author, "note": ack_comment}
    )


def _handle_alert_handler(
    context: PluginNotificationContext,
    connector: Connector,
    notification_type: str,
    integration_team: str | None,
    alias: str,
    alert_source: str | None,
    owner: str | None,
) -> None:
    _requires_integration_team(notification_type, integration_team)
    name = context.get("ALERTHANDLERNAME") or "unknown"
    state = context.get("ALERTHANDLERSTATE") or notification_type[14:-1]
    output = context.get("ALERTHANDLEROUTPUT", "")
    note = f"Alert handler ({name}): {state}\nOutput: {output}"
    if len(note) > 25000:  # API limit
        note = note[:24997] + "..."
    connector.add_note(alias, {"source": alert_source, "user": owner, "note": note})


def main() -> None:
    context = utils.collect_context()
    connector = _get_connector(context)
    integration_team: str | None = context.get("PARAMETER_INTEGRATION_TEAM")
    alert_source: str | None = context.get("PARAMETER_SOURCE")
    owner: str | None = context.get("PARAMETER_OWNER")
    alias = _get_alias(context)

    match context["NOTIFICATIONTYPE"]:
        case "PROBLEM":
            _handle_problem(context, connector, alias, integration_team, alert_source, owner)
        case "RECOVERY":
            connector.handle_alert_deletion(
                alias,
                {
                    "source": alert_source,
                    "user": owner,
                    "note": context.get("PARAMETER_NOTE_CLOSED") or "Alert closed by Check_MK",
                },
            )
        case "ACKNOWLEDGEMENT":
            _handle_acknowledgement(context, connector, alias, alert_source)
        case "FLAPPINGSTART" as nt:
            _requires_integration_team(nt, integration_team)
            connector.add_tags(
                alias,
                {
                    "tags": ["Flapping"],
                    "source": alert_source,
                    "user": owner,
                    "note": "Flapping started",
                },
            )
        case "FLAPPINGSTOP" | "FLAPPINGDISABLED" as nt:
            _requires_integration_team(nt, integration_team)
            connector.remove_tags(
                alias=alias,
                tags=["Flapping"],
                source=alert_source,
                user=owner,
                note=f"Flapping {'stopped' if nt == 'FLAPPINGSTOP' else 'disabled'}",
            )
        case "DOWNTIMESTART" as nt:
            _requires_integration_team(nt, integration_team)
            connector.add_tags(
                alias,
                {
                    "tags": ["Downtime"],
                    "source": alert_source,
                    "user": owner,
                    "note": "Downtime started",
                },
            )
        case "DOWNTIMEEND" | "DOWNTIMECANCELLED" as nt:
            _requires_integration_team(nt, integration_team)
            connector.remove_tags(
                alias=alias,
                tags=["Downtime"],
                source=alert_source,
                user=owner,
                note=f"Downtime {'ended' if nt == 'DOWNTIMEEND' else 'cancelled'}",
            )
        case nt if nt.startswith("ALERTHANDLER"):
            _handle_alert_handler(
                context, connector, nt, integration_team, alias, alert_source, owner
            )
        case nt:
            sys.stdout.write(f"Notification type {nt} not supported\n")
