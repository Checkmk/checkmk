#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pprint import pformat
from typing import cast

import urllib3
from opsgenie_sdk import (
    AcknowledgeAlertPayload,
    AddNoteToAlertPayload,
    AddTagsToAlertPayload,
    Alert,
    AlertApi,
    ApiClient,
    ApiException,
    CloseAlertPayload,
    Configuration,
    CreateAlertPayload,
    UpdateAlertDescriptionPayload,
    UpdateAlertMessagePayload,
)
from opsgenie_sdk.exceptions import AuthenticationException
from requests.utils import get_environ_proxies
from tenacity import RetryError
from urllib3.util import parse_url

from cmk.notification_plugins import utils
from cmk.notification_plugins.utils import get_password_from_env_or_context
from cmk.utils.http_proxy_config import (
    deserialize_http_proxy_config,
    EnvironmentProxyConfig,
    ExplicitProxyConfig,
    NoProxyConfig,
)
from cmk.utils.macros import replace_macros_in_str
from cmk.utils.notify_types import PluginNotificationContext
from cmk.utils.paths import trusted_ca_file


@contextmanager
def _handle_api_exceptions(api_call_name: str, ignore_retry: bool = False) -> Iterator[None]:
    try:
        yield
    except (ApiException, AuthenticationException) as err:
        sys.stderr.write(f"Exception when calling AlertApi -> {api_call_name}: {err}\n")
        sys.exit(2)
    except Exception as e:
        if not ignore_retry and isinstance(e, RetryError):
            with _handle_api_exceptions(api_call_name, ignore_retry=True):
                e.reraise()
        sys.stderr.write(f"Unhandled exception when calling AlertApi -> {api_call_name}: {e}\n")
        sys.exit(2)


# https://docs.opsgenie.com/docs/opsgenie-python-api-v2-1
class Connector:
    def __init__(
        self, api_key: str, host_url: str | None, proxy_url: str | None, ignore_ssl: bool
    ) -> None:
        conf = Configuration()  # type: ignore[no-untyped-call]
        conf.api_key["Authorization"] = api_key
        if host_url is not None:
            conf.host = "%s" % host_url
        if proxy_url is not None:
            sys.stdout.write(f"Using proxy: {proxy_url}\n")
            conf.proxy = proxy_url

        if ignore_ssl:
            sys.stdout.write("Ignoring SSL certificate verification\n")
            conf.verify_ssl = False
            urllib3.disable_warnings(urllib3.connectionpool.InsecureRequestWarning)
        else:
            sys.stdout.write(f"Using trust store: {trusted_ca_file}\n")
            conf.ssl_ca_cert = trusted_ca_file

        sys.stdout.flush()

        api_client: ApiClient = ApiClient(configuration=conf)  # type: ignore[no-untyped-call]
        self.alert_api = AlertApi(api_client=api_client)  # type: ignore[no-untyped-call]

    def get_existing_alert(self, alias: str) -> Alert | None:
        with _handle_api_exceptions("get_alert"):
            try:
                response = self.alert_api.get_alert(  # type: ignore[no-untyped-call]
                    identifier=alias,
                    identifier_type="alias",
                )
            except ApiException:
                sys.stdout.write(f'Alert with alias "{alias}" not found.\n')
                return None

        alert = cast(Alert, response.data)
        sys.stdout.write(f'Alert with alias "{alias}" found, id: {alert.id}.\n')
        return alert

    def handle_alert_update_description(self, identifier: str, description: str) -> None:
        with _handle_api_exceptions("update_alert_description"):
            response = self.alert_api.update_alert_description(  # type: ignore[no-untyped-call]
                identifier,
                identifier_type="id",
                update_alert_description_payload=(
                    UpdateAlertDescriptionPayload(description=description)  # type: ignore[no-untyped-call]
                ),
            )

        sys.stdout.write(
            f"Request id: {response.request_id}, successfully updated alert description.\n"
        )

    def handle_alert_update_message(self, identifier: str, message: str) -> None:
        with _handle_api_exceptions("update_alert_message"):
            response = self.alert_api.update_alert_message(  # type: ignore[no-untyped-call]
                identifier,
                identifier_type="id",
                update_alert_message_payload=(
                    UpdateAlertMessagePayload(message=message)  # type: ignore[no-untyped-call]
                ),
            )

        sys.stdout.write(
            f"Request id: {response.request_id}, successfully updated alert message.\n"
        )

    def handle_alert_creation(self, create_alert_payload: CreateAlertPayload) -> None:
        with _handle_api_exceptions("create_alert"):
            response = self.alert_api.create_alert(  # type: ignore[no-untyped-call]
                create_alert_payload=create_alert_payload
            )

        sys.stdout.write(f"Request id: {response.request_id}, successfully created alert.\n")

    def handle_alert_deletion(
        self, alias: str | None, close_alert_payload: CloseAlertPayload
    ) -> None:
        with _handle_api_exceptions("close_alert"):
            response = self.alert_api.close_alert(  # type: ignore[no-untyped-call]
                identifier=alias,
                identifier_type="alias",
                close_alert_payload=close_alert_payload,
            )

        sys.stdout.write(f"Request id: {response.request_id}, successfully closed alert.\n")

    def handle_alert_ack(
        self, alias: str | None, acknowledge_alert_payload: AcknowledgeAlertPayload
    ) -> None:
        with _handle_api_exceptions("acknowledge_alert"):
            response = self.alert_api.acknowledge_alert(  # type: ignore[no-untyped-call]
                identifier=alias,
                identifier_type="alias",
                acknowledge_alert_payload=acknowledge_alert_payload,
            )

        sys.stdout.write(
            f"Request id: {response.request_id}, successfully added acknowledgedment.\n"
        )

    def add_note(self, alias: str, payload: AddNoteToAlertPayload) -> None:
        with _handle_api_exceptions("add_note"):
            response = self.alert_api.add_note(  # type: ignore[no-untyped-call]
                identifier=alias, identifier_type="alias", add_note_to_alert_payload=payload
            )

        sys.stdout.write(f"Request id: {response.request_id}, successfully added note.\n")

    def add_tags(self, alias: str, payload: AddTagsToAlertPayload) -> None:
        with _handle_api_exceptions("add_tags"):
            response = self.alert_api.add_tags(  # type: ignore[no-untyped-call]
                identifier=alias, identifier_type="alias", add_tags_to_alert_payload=payload
            )

        sys.stdout.write(f"Request id: {response.request_id}, successfully added tags.\n")

    def remove_tags(
        self, alias: str, tags: list[str], source: str | None, user: str | None, note: str | None
    ) -> None:
        with _handle_api_exceptions("remove_tags"):
            response = self.alert_api.remove_tags(  # type: ignore[no-untyped-call]
                identifier=alias,
                identifier_type="alias",
                tags=tags,
                source=source,
                user=user,
                note=note,
            )

        sys.stdout.write(f"Request id: {response.request_id}, successfully removed tags.\n")


def _get_proxy_url(proxy_setting: str | None, url: str | None) -> str | None:
    proxy = deserialize_http_proxy_config(proxy_setting)
    if isinstance(proxy, EnvironmentProxyConfig):
        parsed_url = parse_url(url or "https://api.opsgenie.com")
        proxies = get_environ_proxies(parsed_url.url)
        return proxies.get(parsed_url.scheme)

    if isinstance(proxy, NoProxyConfig):
        return None

    if isinstance(proxy, ExplicitProxyConfig):
        return proxy_setting

    sys.stderr.write(f"Unsupported proxy setting: {proxy_setting}\n")
    sys.exit(2)


def _get_connector(context: PluginNotificationContext) -> Connector:
    if "PARAMETER_PASSWORD_1" not in context:
        sys.stderr.write("API key not set\n")
        sys.exit(2)

    api_key = get_password_from_env_or_context(
        key="PARAMETER_PASSWORD",
        context=context,
    )
    url = context.get("PARAMETER_URL")
    return Connector(
        api_key,
        url,
        _get_proxy_url(context.get("PARAMETER_PROXY_URL"), url),
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
        create_alert_payload=CreateAlertPayload(  # type: ignore[no-untyped-call]
            note=note_created,
            actions=actions_list,
            description=desc,
            message=msg,
            priority=priority,
            responders=teams_list,
            visible_to=visible_to,
            tags=tags_list,
            entity=entity_value,
            source=alert_source,
            alias=alias,
            user=owner,
            details=_get_extra_properties(context),
        )
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
        alias=alias,
        acknowledge_alert_payload=AcknowledgeAlertPayload(  # type: ignore[no-untyped-call]
            source=alert_source,
            user=ack_author,
            note=ack_comment,
        ),
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
    connector.add_note(
        alias=alias,
        payload=AddNoteToAlertPayload(  # type: ignore[no-untyped-call]
            source=alert_source,
            user=owner,
            note=note,
        ),
    )


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
                alias=alias,
                close_alert_payload=CloseAlertPayload(  # type: ignore[no-untyped-call]
                    source=alert_source,
                    user=owner,
                    note=context.get("PARAMETER_NOTE_CLOSED") or "Alert closed by Check_MK",
                ),
            )
        case "ACKNOWLEDGEMENT":
            _handle_acknowledgement(context, connector, alias, alert_source)
        case "FLAPPINGSTART" as nt:
            _requires_integration_team(nt, integration_team)
            connector.add_tags(
                alias=alias,
                payload=AddTagsToAlertPayload(  # type: ignore[no-untyped-call]
                    tags=["Flapping"],
                    source=alert_source,
                    user=owner,
                    note="Flapping started",
                ),
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
                alias=alias,
                payload=AddTagsToAlertPayload(  # type: ignore[no-untyped-call]
                    tags=["Downtime"],
                    source=alert_source,
                    user=owner,
                    note="Downtime started",
                ),
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
