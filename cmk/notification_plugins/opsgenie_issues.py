#!/usr/bin/env python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2019             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

import sys
from opsgenie.swagger_client import AlertApi  # type: ignore
from opsgenie.swagger_client import configuration  # type: ignore
from opsgenie.swagger_client.models import AcknowledgeAlertRequest  # type: ignore
from opsgenie.swagger_client.rest import ApiException  # type: ignore
from opsgenie.swagger_client.models import CloseAlertRequest  # type: ignore
from opsgenie.swagger_client.models import CreateAlertRequest  # type: ignore
from opsgenie.swagger_client.models import TeamRecipient  # type: ignore
from cmk.notification_plugins import utils
from cmk.notification_plugins.utils import retrieve_from_passwordstore


def main():
    context = utils.collect_context()
    priority = 'P3'
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
    alert_source = None or context.get('PARAMETER_SOURCE')
    owner = None or context.get('PARAMETER_OWNER')
    entity_value = None or context.get('PARAMETER_ENTITY')

    if context.get('PARAMETER_TAGSS'):
        tags_list = None or context.get('PARAMETER_TAGSS').split(" ")

    if context.get('PARAMETER_ACTIONSS'):
        action_list = None or context.get('PARAMETER_ACTIONSS').split(" ")

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
        )
    elif context['NOTIFICATIONTYPE'] == 'RECOVERY':
        handle_alert_deletion(key, owner, alias, alert_source, note_closed)
    elif context['NOTIFICATIONTYPE'] == 'ACKNOWLEDGEMENT':
        handle_alert_ack(key, ack_author, ack_comment, alias, alert_source)
    else:
        sys.stdout.write('Noticication type %s not supported\n' % (context['NOTIFICATIONTYPE']))
        return 0


def configure_authorization(key):
    configuration.api_key['Authorization'] = key
    configuration.api_key_prefix['Authorization'] = 'GenieKey'


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
):
    configure_authorization(key)

    body = CreateAlertRequest(  # type: ignore
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


def handle_alert_deletion(key, owner, alias, alert_source, note_closed):
    configure_authorization(key)

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


def handle_alert_ack(key, ack_author, ack_comment, alias, alert_source):
    configure_authorization(key)

    body = AcknowledgeAlertRequest(  # type: ignore
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
