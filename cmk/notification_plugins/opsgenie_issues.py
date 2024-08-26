#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import sys
from contextlib import contextmanager
from pprint import pformat
from typing import Iterator

from opsgenie_sdk import (  # type: ignore[import-untyped]
    AcknowledgeAlertPayload,
    AddNoteToAlertPayload,
    AddTagsToAlertPayload,
    AlertApi,
    ApiClient,
    ApiException,
    CloseAlertPayload,
    Configuration,
    CreateAlertPayload,
)
from opsgenie_sdk.exceptions import AuthenticationException  # type: ignore[import-untyped]

from cmk.utils.macros import replace_macros_in_str
from cmk.utils.notify_types import PluginNotificationContext

from cmk.notification_plugins import utils
from cmk.notification_plugins.utils import retrieve_from_passwordstore


@contextmanager
def _handle_api_exceptions(api_call_name: str) -> Iterator[None]:
    try:
        yield
    except (ApiException, AuthenticationException) as err:
        sys.stderr.write(f"Exception when calling AlertApi -> {api_call_name}: {err}\n")
        sys.exit(2)
    except Exception as e:
        sys.stderr.write(f"Unhandled exception: {e}\n")
        sys.exit(2)


# https://docs.opsgenie.com/docs/opsgenie-python-api-v2-1
class Connector:
    def __init__(self, api_key: str, host_url: str | None, proxy_url: str | None) -> None:
        conf: "Configuration" = Configuration()
        conf.api_key["Authorization"] = api_key
        if host_url is not None:
            conf.host = "%s" % host_url
        if proxy_url is not None:
            conf.proxy = proxy_url

        api_client: "ApiClient" = ApiClient(configuration=conf)
        self.alert_api = AlertApi(api_client=api_client)

    def handle_alert_creation(self, create_alert_payload: CreateAlertPayload) -> None:
        with _handle_api_exceptions("create_alert"):
            response = self.alert_api.create_alert(create_alert_payload=create_alert_payload)

        sys.stdout.write(f"Request id: {response.request_id}, successfully created alert.\n")

    def handle_alert_deletion(
        self, alias: str | None, close_alert_payload: CloseAlertPayload
    ) -> None:
        with _handle_api_exceptions("close_alert"):
            response = self.alert_api.close_alert(
                identifier=alias,
                identifier_type="alias",
                close_alert_payload=close_alert_payload,
            )

        sys.stdout.write(f"Request id: {response.request_id}, successfully closed alert.\n")

    def handle_alert_ack(
        self, alias: str | None, acknowledge_alert_payload: AcknowledgeAlertPayload
    ) -> None:
        with _handle_api_exceptions("acknowledge_alert"):
            response = self.alert_api.acknowledge_alert(
                identifier=alias,
                identifier_type="alias",
                acknowledge_alert_payload=acknowledge_alert_payload,
            )

        sys.stdout.write(
            f"Request id: {response.request_id}, successfully added acknowledgedment.\n"
        )

    def add_note(self, alias: str, payload: AddNoteToAlertPayload) -> None:
        with _handle_api_exceptions("add_note"):
            response = self.alert_api.add_note(
                identifier=alias, identifier_type="alias", add_note_to_alert_payload=payload
            )

        sys.stdout.write(f"Request id: {response.request_id}, successfully added note.\n")

    def add_tags(self, alias: str, payload: AddTagsToAlertPayload) -> None:
        with _handle_api_exceptions("add_tags"):
            response = self.alert_api.add_tags(
                identifier=alias, identifier_type="alias", add_tags_to_alert_payload=payload
            )

        sys.stdout.write(f"Request id: {response.request_id}, successfully added tags.\n")

    def remove_tags(
        self, alias: str, tags: list[str], source: str | None, user: str | None, note: str | None
    ) -> None:
        with _handle_api_exceptions("remove_tags"):
            response = self.alert_api.remove_tags(
                identifier=alias,
                identifier_type="alias",
                tags=tags,
                source=source,
                user=user,
                note=note,
            )

        sys.stdout.write(f"Request id: {response.request_id}, successfully removed tags.\n")


def _get_connector(context: PluginNotificationContext) -> Connector:
    if "PARAMETER_PASSWORD" not in context:
        sys.stderr.write("API key not set\n")
        sys.exit(2)

    api_key = retrieve_from_passwordstore(context["PARAMETER_PASSWORD"])
    return Connector(api_key, context.get("PARAMETER_URL"), context.get("PARAMETER_PROXY_URL"))


def _get_alias(context: PluginNotificationContext) -> str:
    if context["WHAT"] == "HOST":
        return (
            f'HOST_PROBLEM_ID: {context["LASTHOSTPROBLEMID"]}'
            if context["HOSTPROBLEMID"] == "0"
            else f'HOST_PROBLEM_ID: {context["HOSTPROBLEMID"]}'
        )

    return (
        f'SVC_PROBLEM_ID: {context["LASTSERVICEPROBLEMID"]}'
        if context["SERVICEPROBLEMID"] == "0"
        else f'SVC_PROBLEM_ID: {context["SERVICEPROBLEMID"]}'
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
        "hosttags": ("Tags of the Host", "\n".join((context.get("HOST_TAGS", "").split()))),
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

    connector.handle_alert_creation(
        create_alert_payload=CreateAlertPayload(
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
        acknowledge_alert_payload=AcknowledgeAlertPayload(
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
        payload=AddNoteToAlertPayload(
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
                close_alert_payload=CloseAlertPayload(
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
                payload=AddTagsToAlertPayload(
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
                note=f"Flapping {"stopped" if nt == "FLAPPINGSTOP" else "disabled"}",
            )
        case "DOWNTIMESTART" as nt:
            _requires_integration_team(nt, integration_team)
            connector.add_tags(
                alias=alias,
                payload=AddTagsToAlertPayload(
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
                note=f"Downtime {"ended" if nt == "DOWNTIMEEND" else "cancelled"}",
            )
        case nt if nt.startswith("ALERTHANDLER"):
            _handle_alert_handler(
                context, connector, nt, integration_team, alias, alert_source, owner
            )
        case nt:
            sys.stdout.write(f"Notification type {nt} not supported\n")
