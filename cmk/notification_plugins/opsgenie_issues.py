#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import sys
from pprint import pformat

from opsgenie_sdk.api.alert import AlertApi  # type: ignore[import-untyped]
from opsgenie_sdk.api.alert.acknowledge_alert_payload import (  # type: ignore[import-untyped]
    AcknowledgeAlertPayload,
)
from opsgenie_sdk.api.alert.close_alert_payload import (  # type: ignore[import-untyped]
    CloseAlertPayload,
)
from opsgenie_sdk.api.alert.create_alert_payload import (  # type: ignore[import-untyped]
    CreateAlertPayload,
)
from opsgenie_sdk.api_client import ApiClient  # type: ignore[import-untyped]
from opsgenie_sdk.configuration import Configuration  # type: ignore[import-untyped]
from opsgenie_sdk.exceptions import (  # type: ignore[import-untyped]
    ApiException,
    AuthenticationException,
)

from cmk.utils.macros import replace_macros_in_str
from cmk.utils.notify_types import PluginNotificationContext

from cmk.notification_plugins import utils
from cmk.notification_plugins.utils import retrieve_from_passwordstore


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

    def handle_alert_creation(self, create_alert_payload: CreateAlertPayload) -> int:
        try:
            response = self.alert_api.create_alert(create_alert_payload=create_alert_payload)
        except (ApiException, AuthenticationException) as err:
            sys.stderr.write(f"Exception when calling AlertApi -> create_alert: {err}\n")
            return 2
        except Exception as e:
            sys.stderr.write(f"Unhandled exception: {e}\n")
            return 2

        sys.stdout.write(f"Request id: {response.request_id}, successfully created alert.\n")
        return 0

    def handle_alert_deletion(
        self, alias: str | None, close_alert_payload: CloseAlertPayload
    ) -> int:
        try:
            response = self.alert_api.close_alert(
                identifier=alias,
                identifier_type="alias",
                close_alert_payload=close_alert_payload,
            )
        except (ApiException, AuthenticationException) as err:
            sys.stderr.write(f"Exception when calling AlertApi -> close_alert: {err}\n")
            return 2
        except Exception as e:
            sys.stderr.write(f"Unhandled exception: {e}\n")
            return 2

        sys.stdout.write(f"Request id: {response.request_id}, successfully closed alert.\n")
        return 0

    def handle_alert_ack(
        self, alias: str | None, acknowledge_alert_payload: CloseAlertPayload
    ) -> int:
        try:
            response = self.alert_api.acknowledge_alert(
                identifier=alias,
                identifier_type="alias",
                acknowledge_alert_payload=acknowledge_alert_payload,
            )
        except (ApiException, AuthenticationException) as err:
            sys.stderr.write(f"Exception when calling AlertApi -> acknowledge_alert: {err}\n")
            return 2
        except Exception as e:
            sys.stderr.write(f"Unhandled exception: {e}\n")
            return 2

        sys.stdout.write(
            f"Request id: {response.request_id}, successfully added acknowledgedment.\n"
        )
        return 0


def get_extra_properties(context: PluginNotificationContext) -> dict[str, str]:
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


def main() -> int:
    context = utils.collect_context()

    if "PARAMETER_PASSWORD" not in context:
        sys.stderr.write("API key not set\n")
        return 2

    api_key = retrieve_from_passwordstore(context["PARAMETER_PASSWORD"])
    note_created = context.get("PARAMETER_NOTE_CREATED") or "Alert created by Check_MK"
    note_closed = context.get("PARAMETER_NOTE_CLOSED") or "Alert closed by Check_MK"
    priority = context.get("PARAMETER_PRIORITY", "P3")
    entity_value = context.get("PARAMETER_ENTITY", "")
    alert_source: str | None = context.get("PARAMETER_SOURCE")
    owner: str | None = context.get("PARAMETER_OWNER")
    host_url: str | None = context.get("PARAMETER_URL")
    proxy_url: str | None = context.get("PARAMETER_PROXY_URL")

    tags_list: list[str] = []
    if (tags := context.get("PARAMETER_TAGSS")) is not None:
        tags_list = replace_macros_in_str(
            string=tags, macro_mapping={f"${k}$": v for k, v in context.items()}
        ).split()

    actions_list: list[str] = []
    if context.get("PARAMETER_ACTIONSS"):
        actions_list = context.get("PARAMETER_ACTIONSS", "").split(" ")

    teams_list: list[dict[str, str] | None] = []
    if context.get("PARAMETER_TEAMSS"):
        teams_list = [
            {"name": str(context[k]), "type": "team"}
            for k in context
            if k.startswith("PARAMETER_TEAMS_")
        ]

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
        alias = (
            f'HOST_PROBLEM_ID: {context["LASTHOSTPROBLEMID"]}'
            if context["HOSTPROBLEMID"] == "0"
            else f'HOST_PROBLEM_ID: {context["HOSTPROBLEMID"]}'
        )
        ack_author = context["HOSTACKAUTHOR"]
        ack_comment = context["HOSTACKCOMMENT"]
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
        alias = (
            f'SVC_PROBLEM_ID: {context["LASTSERVICEPROBLEMID"]}'
            if context["SERVICEPROBLEMID"] == "0"
            else f'SVC_PROBLEM_ID: {context["SERVICEPROBLEMID"]}'
        )
        ack_author = context["SERVICEACKAUTHOR"]
        ack_comment = context["SERVICEACKCOMMENT"]

    desc = utils.substitute_context(desc, context)
    msg = utils.substitute_context(msg, context)

    connector = Connector(api_key, host_url, proxy_url)

    if context["NOTIFICATIONTYPE"] == "PROBLEM":
        return connector.handle_alert_creation(
            create_alert_payload=CreateAlertPayload(
                note=note_created,
                actions=actions_list,
                description=desc,
                message=msg,
                priority=priority,
                responders=teams_list,
                tags=tags_list,
                entity=entity_value,
                source=alert_source,
                alias=alias,
                user=owner,
                details=get_extra_properties(context),
            )
        )

    if context["NOTIFICATIONTYPE"] == "RECOVERY":
        return connector.handle_alert_deletion(
            alias=alias,
            close_alert_payload=CloseAlertPayload(
                source=alert_source,
                user=owner,
                note=note_closed,
            ),
        )

    if context["NOTIFICATIONTYPE"] == "ACKNOWLEDGEMENT":
        return connector.handle_alert_ack(
            alias=alias,
            acknowledge_alert_payload=AcknowledgeAlertPayload(
                source=alert_source,
                user=ack_author,
                note=ack_comment,
            ),
        )

    sys.stdout.write("Notification type %s not supported\n" % (context["NOTIFICATIONTYPE"]))
    return 0
