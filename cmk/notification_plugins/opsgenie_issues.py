#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import sys
from typing import Optional

from six import ensure_str
from opsgenie.swagger_client import AlertApi  # type: ignore[import]  # pylint: disable=import-error
from opsgenie.swagger_client import configuration  # pylint: disable=import-error
from opsgenie.swagger_client.models import AcknowledgeAlertRequest  # type: ignore[import] # pylint: disable=import-error
from opsgenie.swagger_client.rest import ApiException  # type: ignore[import] # pylint: disable=import-error
from opsgenie.swagger_client.models import CloseAlertRequest  # pylint: disable=import-error
from opsgenie.swagger_client.models import CreateAlertRequest  # pylint: disable=import-error
from opsgenie.swagger_client.models import TeamRecipient  # pylint: disable=import-error

from cmk.notification_plugins import utils
from cmk.notification_plugins.utils import retrieve_from_passwordstore


def main():
    context = utils.collect_context()
    priority: Optional[str] = u'P3'
    teams_list = []
    tags_list = None
    action_list = None

    if 'PARAMETER_PASSWORD' not in context:
        sys.stderr.write("API key not set\n")
        return 2

    key = retrieve_from_passwordstore(context['PARAMETER_PASSWORD'])
    note_created = 'Alert created by Check_MK' or context.get('PARAMETER_NOTE_CREATED')
    note_closed = 'Alert closed by Check_MK' or context.get('PARAMETER_NOTE_CLOSED')
    priority = context.get('PARAMETER_PRIORITY')
    alert_source = context.get('PARAMETER_SOURCE')
    owner = context.get('PARAMETER_OWNER')
    entity_value = context.get('PARAMETER_ENTITY')
    host_url = context.get("PARAMETER_URL")
    proxy_url = context.get("PARAMETER_PROXY_URL")

    if context.get('PARAMETER_TAGSS'):
        tags_list = None or context.get('PARAMETER_TAGSS', u'').split(" ")

    if context.get('PARAMETER_ACTIONSS'):
        action_list = None or context.get('PARAMETER_ACTIONSS', u'').split(" ")

    if context.get('PARAMETER_TEAMSS'):
        for team in context['PARAMETER_TEAMSS'].split(" "):
            teams_list.append(TeamRecipient(name=str(team), type='team'))

    if context['WHAT'] == 'HOST':
        tmpl_host_msg = "Check_MK: $HOSTNAME$ - $HOSTSHORTSTATE$"
        tmpl_host_desc = """Host: $HOSTNAME$
Event:    $EVENT_TXT$
Output:   $HOSTOUTPUT$
Perfdata: $HOSTPERFDATA$
$LONGHOSTOUTPUT$
"""
        desc = context.get('PARAMETER_HOST_DESC') or tmpl_host_desc
        msg = context.get('PARAMETER_HOST_MSG') or tmpl_host_msg
        alias = 'HOST_PROBLEM_ID: %s' % context['HOSTPROBLEMID']
        ack_author = context['HOSTACKAUTHOR']
        ack_comment = context['HOSTACKCOMMENT']
    else:
        tmpl_svc_msg = 'Check_MK: $HOSTNAME$/$SERVICEDESC$ $SERVICESHORTSTATE$'
        tmpl_svc_desc = """Host: $HOSTNAME$
Service:  $SERVICEDESC$
Event:    $EVENT_TXT$
Output:   $SERVICEOUTPUT$
Perfdata: $SERVICEPERFDATA$
$LONGSERVICEOUTPUT$
"""
        desc = context.get('PARAMETER_SVC_DESC') or tmpl_svc_desc
        msg = context.get('PARAMETER_SVC_MSG') or tmpl_svc_msg
        alias = 'SVC_PROBLEM_ID: %s' % context['SERVICEPROBLEMID']
        ack_author = context['SERVICEACKAUTHOR']
        ack_comment = context['SERVICEACKCOMMENT']

    desc = utils.substitute_context(desc, context)
    msg = utils.substitute_context(msg, context)

    if context['NOTIFICATIONTYPE'] == 'PROBLEM':
        handle_alert_creation(
            key,
            note_created,
            action_list,
            desc,
            alert_source,
            msg,
            priority,
            teams_list,
            tags_list,
            alias,
            owner,
            entity_value,
            host_url,
            proxy_url,
        )
    elif context['NOTIFICATIONTYPE'] == 'RECOVERY':
        handle_alert_deletion(key, owner, alias, alert_source, note_closed, host_url, proxy_url)
    elif context['NOTIFICATIONTYPE'] == 'ACKNOWLEDGEMENT':
        handle_alert_ack(key, ack_author, ack_comment, alias, alert_source, host_url, proxy_url)
    else:
        sys.stdout.write(
            ensure_str('Notification type %s not supported\n' % (context['NOTIFICATIONTYPE'])))
        return 0


def configure_authorization(key, host_url, proxy_url):
    configuration.api_key['Authorization'] = key
    configuration.api_key_prefix['Authorization'] = 'GenieKey'
    if host_url is not None:
        configuration.host = '%s' % host_url
    if proxy_url is not None:
        configuration.proxy = proxy_url


def handle_alert_creation(
    key,
    note_created,
    action_list,
    desc,
    alert_source,
    msg,
    priority,
    teams_list,
    tags_list,
    alias,
    owner,
    entity_value,
    host_url,
    proxy_url,
):
    configure_authorization(key, host_url, proxy_url)

    body = CreateAlertRequest(
        note=note_created,
        actions=action_list,
        description=desc,
        source=alert_source,
        message=msg,
        priority=priority,
        teams=teams_list,
        tags=tags_list,
        alias=alias,
        user=owner,
        entity=entity_value,
    )

    try:
        response = AlertApi().create_alert(body=body)

        sys.stdout.write('Request id: %s, successfully created alert.\n' % response.request_id)
        return 0
    except ApiException as err:
        sys.stderr.write('Exception when calling AlertApi->create_alert: %s\n' % err)
        return 2


def handle_alert_deletion(key, owner, alias, alert_source, note_closed, host_url, proxy_url):
    configure_authorization(key, host_url, proxy_url)

    body = CloseAlertRequest(
        source=alert_source,
        user=owner,
        note=note_closed,
    )

    try:
        response = AlertApi().close_alert(identifier=alias, identifier_type='alias', body=body)
        sys.stdout.write('Request id: %s, successfully closed alert.\n' % response.request_id)
        return 0

    except ApiException as err:
        sys.stderr.write('Exception when calling AlertApi->close_alert: %s\n' % err)
        return 2


def handle_alert_ack(key, ack_author, ack_comment, alias, alert_source, host_url, proxy_url):
    configure_authorization(key, host_url, proxy_url)

    body = AcknowledgeAlertRequest(
        source=alert_source,
        user=ack_author,
        note=ack_comment,
    )

    try:
        response = AlertApi().acknowledge_alert(identifier=alias,
                                                identifier_type='alias',
                                                body=body)

        sys.stdout.write('Request id: %s, successfully added acknowledgedment.\n' %
                         response.request_id)
        return 0
    except ApiException as err:
        sys.stderr.write('Exception when calling AlertApi->acknowledge_alert: %s\n' % err)
        return 2
