#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import sys
from typing import Dict, List, Optional

# ignore mypy error: "found module but no type hints or library stubs"
from opsgenie_sdk.api.alert import AlertApi  # type: ignore
from opsgenie_sdk.api.alert.acknowledge_alert_payload import AcknowledgeAlertPayload  # type: ignore
from opsgenie_sdk.api.alert.close_alert_payload import CloseAlertPayload  # type: ignore
from opsgenie_sdk.api.alert.create_alert_payload import CreateAlertPayload  # type: ignore
from opsgenie_sdk.api_client import ApiClient  # type: ignore
from opsgenie_sdk.configuration import Configuration  # type: ignore
from opsgenie_sdk.rest import ApiException  # type: ignore

from cmk.notification_plugins import utils
from cmk.notification_plugins.utils import retrieve_from_passwordstore


# https://docs.opsgenie.com/docs/opsgenie-python-api-v2-1
class Connector:
    def __init__(self, api_key: str, host_url: Optional[str], proxy_url: Optional[str]) -> None:
        conf: "Configuration" = Configuration()
        conf.api_key["Authorization"] = api_key
        if host_url is not None:
            conf.host = "%s" % host_url
        if proxy_url is not None:
            conf.proxy = proxy_url

        api_client: "ApiClient" = ApiClient(configuration=conf)
        self.alert_api = AlertApi(api_client=api_client)

    def handle_alert_creation(
        self,
        note_created: str,
        actions_list: List[str],
        desc: str,
        msg: str,
        priority: str,
        teams_list: List[Optional[Dict[str, str]]],
        tags_list: List[str],
        entity_value: str,
        alert_source: Optional[str],
        alias: Optional[str],
        owner: Optional[str],
    ) -> int:

        body = CreateAlertPayload(
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
        )

        try:
            response = self.alert_api.create_alert(create_alert_payload=body)

            sys.stdout.write("Request id: %s, successfully created alert.\n" % response.request_id)
            return 0
        except ApiException as err:
            sys.stderr.write("Exception when calling AlertApi->create_alert: %s\n" % err)
            return 2

    def handle_alert_deletion(
        self,
        note_closed: str,
        owner: Optional[str],
        alias: Optional[str],
        alert_source: Optional[str],
    ) -> int:

        body = CloseAlertPayload(
            source=alert_source,
            user=owner,
            note=note_closed,
        )

        try:
            response = self.alert_api.close_alert(
                identifier=alias, identifier_type="alias", close_alert_payload=body
            )
            sys.stdout.write("Request id: %s, successfully closed alert.\n" % response.request_id)
            return 0

        except ApiException as err:
            sys.stderr.write("Exception when calling AlertApi->close_alert: %s\n" % err)
            return 2

    def handle_alert_ack(
        self, ack_author: str, ack_comment: str, alias: Optional[str], alert_source: Optional[str]
    ) -> int:

        body = AcknowledgeAlertPayload(
            source=alert_source,
            user=ack_author,
            note=ack_comment,
        )

        try:
            response = self.alert_api.acknowledge_alert(
                identifier=alias, identifier_type="alias", acknowledge_alert_payload=body
            )

            sys.stdout.write(
                "Request id: %s, successfully added acknowledgedment.\n" % response.request_id
            )
            return 0
        except ApiException as err:
            sys.stderr.write("Exception when calling AlertApi->acknowledge_alert: %s\n" % err)
            return 2


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
    alert_source: Optional[str] = context.get("PARAMETER_SOURCE")
    owner: Optional[str] = context.get("PARAMETER_OWNER")
    host_url: Optional[str] = context.get("PARAMETER_URL")
    proxy_url: Optional[str] = context.get("PARAMETER_PROXY_URL")

    tags_list: List[str] = []
    if context.get("PARAMETER_TAGSS"):
        tags_list = context.get("PARAMETER_TAGSS", "").split(" ")

    actions_list: List[str] = []
    if context.get("PARAMETER_ACTIONSS"):
        actions_list = context.get("PARAMETER_ACTIONSS", "").split(" ")

    teams_list: List[Optional[Dict[str, str]]] = []
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
        alias = "HOST_PROBLEM_ID: %s" % context["HOSTPROBLEMID"]
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
        alias = "SVC_PROBLEM_ID: %s" % context["SERVICEPROBLEMID"]
        ack_author = context["SERVICEACKAUTHOR"]
        ack_comment = context["SERVICEACKCOMMENT"]

    desc = utils.substitute_context(desc, context)
    msg = utils.substitute_context(msg, context)

    connector = Connector(api_key, host_url, proxy_url)

    if context["NOTIFICATIONTYPE"] == "PROBLEM":
        return connector.handle_alert_creation(
            note_created,
            actions_list,
            desc,
            msg,
            priority,
            teams_list,
            tags_list,
            entity_value,
            alert_source,
            alias,
            owner,
        )
    if context["NOTIFICATIONTYPE"] == "RECOVERY":
        return connector.handle_alert_deletion(note_closed, owner, alias, alert_source)
    if context["NOTIFICATIONTYPE"] == "ACKNOWLEDGEMENT":
        return connector.handle_alert_ack(ack_author, ack_comment, alias, alert_source)

    sys.stdout.write("Notification type %s not supported\n" % (context["NOTIFICATIONTYPE"]))
    return 0
