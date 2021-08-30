#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os

import pytest

from cmk.base import notify


def test_os_environment_does_not_override_notification_script_env(monkeypatch):
    """Regression test for Werk #7339"""
    monkeypatch.setattr(os, 'environ', {'NOTIFY_CONTACTEMAIL': ''})
    script_env = notify.notification_script_env({'CONTACTEMAIL': 'ab@test.de'})
    assert script_env == {'NOTIFY_CONTACTEMAIL': 'ab@test.de'}


@pytest.mark.parametrize("environ,expected", [
    ({}, {}),
    (
        {
            'TEST': 'test'
        },
        {},
    ),
    (
        {
            'NOTIFY_TEST': 'test'
        },
        {
            'TEST': 'test'
        },
    ),
    (
        {
            'NOTIFY_SERVICEOUTPUT': 'LONGSERVICEOUTPUT=with_light_vertical_bar_\u2758'
        },
        {
            'SERVICEOUTPUT': 'LONGSERVICEOUTPUT=with_light_vertical_bar_|'
        },
    ),
    (
        {
            'NOTIFY_LONGSERVICEOUTPUT': 'LONGSERVICEOUTPUT=with_light_vertical_bar_\u2758'
        },
        {
            'LONGSERVICEOUTPUT': 'LONGSERVICEOUTPUT=with_light_vertical_bar_|'
        },
    ),
])
def test_raw_context_from_env_pipe_decoding(environ, expected):
    assert notify.raw_context_from_env(environ) == expected


@pytest.mark.parametrize("context,params,expected", [
    (
        {
            'CONTACTS': 'cmkadmin',
            'NOTIFICATIONTYPE': 'PROBLEM',
            'NOTIFICATIONCOMMENT': '',
            'NOTIFICATIONAUTHOR': '',
            'NOTIFICATIONAUTHORNAME': '',
            'NOTIFICATIONAUTHORALIAS': '',
            'HOSTACKAUTHOR': '',
            'HOSTACKCOMMENT': '',
            'SERVICEACKAUTHOR': '',
            'SERVICEACKCOMMENT': '',
            'MICROTIME': '1630314980978764',
            'HOSTNOTIFICATIONNUMBER': '1',
            'LASTHOSTPROBLEMID': '0',
            'HOSTPROBLEMID': '0',
            'HOSTATTEMPT': '1',
            'MAXHOSTATTEMPTS': '1',
            'HOSTNAME': 'heute',
            'HOSTALIAS': 'heute',
            'HOSTADDRESS': '127.0.0.1',
            'HOSTOUTPUT': 'Packet received via smart PING',
            'HOSTPERFDATA': '',
            'HOSTSTATE': 'UP',
            'HOSTSTATEID': '0',
            'LASTHOSTSTATE': 'UP',
            'LASTHOSTSTATEID': '0',
            'PREVIOUSHOSTHARDSTATE': 'UP',
            'PREVIOUSHOSTHARDSTATEID': '0',
            'LONGHOSTOUTPUT': '',
            'HOSTCHECKCOMMAND': 'check-mk-host-smart',
            'LASTHOSTSTATECHANGE': '1630304184',
            'LASTHOSTUP': '1630314980',
            'HOSTDOWNTIME': '0',
            'HOSTGROUPNAMES': 'check_mk',
            'HOSTCONTACTGROUPNAMES': 'all',
            'HOSTTAGS': '/wato/ auto-piggyback cmk-agent ip-v4 ip-v4-only lan no-snmp prod site:heute tcp',
            'HOST_SL': '',
            'HOST_EC_CONTACT': '',
            'HOSTNOTESURL': '',
            'HOSTNOTES': '',
            'HOST_FILENAME': '/wato/hosts.mk',
            'HOST_ADDRESS_FAMILY': '4',
            'HOST_ADDRESS_4': '127.0.0.1',
            'HOST_ADDRESS_6': '',
            'HOST_TAGS': '/wato/ auto-piggyback cmk-agent ip-v4 ip-v4-only lan no-snmp prod site:heute tcp',
            'SERVICEDESC': 'CPU load',
            'SERVICEOUTPUT': 'Manually set to Critical by cmkadmin',
            'SERVICEPERFDATA': '',
            'SERVICENOTIFICATIONNUMBER': '1',
            'SERVICEPROBLEMID': '50',
            'LASTSERVICEPROBLEMID': '50',
            'SERVICEATTEMPT': '1',
            'MAXSERVICEATTEMPTS': '1',
            'SERVICESTATE': 'CRITICAL',
            'SERVICESTATEID': '2',
            'LASTSERVICESTATE': 'OK',
            'LASTSERVICESTATEID': '0',
            'PREVIOUSSERVICEHARDSTATE': 'OK',
            'PREVIOUSSERVICEHARDSTATEID': '0',
            'LASTSERVICESTATECHANGE': '1630314980',
            'LASTSERVICEOK': '1630314925',
            'SERVICEDOWNTIME': '0',
            'LONGSERVICEOUTPUT': '',
            'SERVICECHECKCOMMAND': 'check_mk-cpu_loads',
            'SERVICEGROUPNAMES': '',
            'SERVICECONTACTGROUPNAMES': 'all',
            'SVC_SL': '',
            'SERVICE_SL': '',
            'SERVICE_EC_CONTACT': '',
            'SERVICENOTESURL': '',
            'SERVICENOTES': '',
            'SERVICEDISPLAYNAME': 'CPU load',
            'LOGDIR': '/omd/sites/heute/var/check_mk/notify',
            'MAIL_COMMAND': "mail -s '$SUBJECT$' '$CONTACTEMAIL$'",
            'WHAT': 'SERVICE',
            'MONITORING_HOST': 'klappclub',
            'OMD_ROOT': '/omd/sites/heute',
            'OMD_SITE': 'heute',
            'DATE': '2021-08-30',
            'SHORTDATETIME': '2021-08-30 11:16:20',
            'LONGDATETIME': 'Mon Aug 30 11:16:20 CEST 2021',
            'HOSTURL': '/check_mk/index.py?start_url=view.py%3Fview_name%3Dhoststatus%26host%3Dheute%26site%3Dheute',
            'SERVICEURL': '/check_mk/index.py?start_url=view.py%3Fview_name%3Dservice%26host%3Dheute%26service%3DCPU%20load%26site%3Dheute',
            'LASTHOSTSTATECHANGE_REL': '0d 02:59:58',
            'LASTSERVICESTATECHANGE_REL': '0d 00:00:02',
            'LASTHOSTUP_REL': '0d 00:00:02',
            'LASTSERVICEOK_REL': '0d 00:00:57',
            'CONTACTNAME': 'check-mk-notify',
            'HOSTSHORTSTATE': 'UP',
            'LASTHOSTSHORTSTATE': 'UP',
            'PREVIOUSHOSTHARDSHORTSTATE': 'UP',
            'SERVICESHORTSTATE': 'CRIT',
            'LASTSERVICESHORTSTATE': 'OK',
            'PREVIOUSSERVICEHARDSHORTSTATE': 'OK',
            'SERVICEFORURL': 'CPU%20load',
            'HOSTFORURL': 'heute',
            'HOSTLABEL_cmk/os_family': 'linux'
        },
        {
            'from': {
                'address': 'from@lala.com',
                'display_name': 'from_display_name'
            },
            'reply_to': {
                'address': 'reply@lala.com',
                'display_name': 'reply_display_name'
            },
            'host_subject': 'Check_MK: $HOSTNAME$ - $EVENT_TXT$',
            'service_subject': 'Check_MK: $HOSTNAME$/$SERVICEDESC$ $EVENT_TXT$',
            'elements': [
                'omdsite', 'hosttags', 'address', 'abstime', 'reltime', 'longoutput', 'ack_author',
                'ack_comment', 'perfdata', 'graph', 'notesurl', 'context'
            ],
            'insert_html_section': '<HTMLTAG>CONTENT</HTMLTAG>\n',
            'url_prefix': {
                'manual': 'http://my_server/heute/check_mk/'
            },
            'no_floating_graphs': True,
            'bulk_sort_order': 'newest_first',
            'disable_multiplexing': True,
            'smtp': {
                'smarthosts': ['127.0.0.1'],
                'port': 25,
                'auth': {
                    'method': 'plaintext',
                    'user': 'user',
                    'password': 'password'
                },
                'encryption': 'starttls'
            },
            'graphs_per_notification': 42,
            'notifications_with_graphs': 42
        },
        {
            'CONTACTS': 'cmkadmin',
            'NOTIFICATIONTYPE': 'PROBLEM',
            'NOTIFICATIONCOMMENT': '',
            'NOTIFICATIONAUTHOR': '',
            'NOTIFICATIONAUTHORNAME': '',
            'NOTIFICATIONAUTHORALIAS': '',
            'HOSTACKAUTHOR': '',
            'HOSTACKCOMMENT': '',
            'SERVICEACKAUTHOR': '',
            'SERVICEACKCOMMENT': '',
            'MICROTIME': '1630314980978764',
            'HOSTNOTIFICATIONNUMBER': '1',
            'LASTHOSTPROBLEMID': '0',
            'HOSTPROBLEMID': '0',
            'HOSTATTEMPT': '1',
            'MAXHOSTATTEMPTS': '1',
            'HOSTNAME': 'heute',
            'HOSTALIAS': 'heute',
            'HOSTADDRESS': '127.0.0.1',
            'HOSTOUTPUT': 'Packet received via smart PING',
            'HOSTPERFDATA': '',
            'HOSTSTATE': 'UP',
            'HOSTSTATEID': '0',
            'LASTHOSTSTATE': 'UP',
            'LASTHOSTSTATEID': '0',
            'PREVIOUSHOSTHARDSTATE': 'UP',
            'PREVIOUSHOSTHARDSTATEID': '0',
            'LONGHOSTOUTPUT': '',
            'HOSTCHECKCOMMAND': 'check-mk-host-smart',
            'LASTHOSTSTATECHANGE': '1630304184',
            'LASTHOSTUP': '1630314980',
            'HOSTDOWNTIME': '0',
            'HOSTGROUPNAMES': 'check_mk',
            'HOSTCONTACTGROUPNAMES': 'all',
            'HOSTTAGS': '/wato/ auto-piggyback cmk-agent ip-v4 ip-v4-only lan no-snmp prod site:heute tcp',
            'HOST_SL': '',
            'HOST_EC_CONTACT': '',
            'HOSTNOTESURL': '',
            'HOSTNOTES': '',
            'HOST_FILENAME': '/wato/hosts.mk',
            'HOST_ADDRESS_FAMILY': '4',
            'HOST_ADDRESS_4': '127.0.0.1',
            'HOST_ADDRESS_6': '',
            'HOST_TAGS': '/wato/ auto-piggyback cmk-agent ip-v4 ip-v4-only lan no-snmp prod site:heute tcp',
            'SERVICEDESC': 'CPU load',
            'SERVICEOUTPUT': 'Manually set to Critical by cmkadmin',
            'SERVICEPERFDATA': '',
            'SERVICENOTIFICATIONNUMBER': '1',
            'SERVICEPROBLEMID': '50',
            'LASTSERVICEPROBLEMID': '50',
            'SERVICEATTEMPT': '1',
            'MAXSERVICEATTEMPTS': '1',
            'SERVICESTATE': 'CRITICAL',
            'SERVICESTATEID': '2',
            'LASTSERVICESTATE': 'OK',
            'LASTSERVICESTATEID': '0',
            'PREVIOUSSERVICEHARDSTATE': 'OK',
            'PREVIOUSSERVICEHARDSTATEID': '0',
            'LASTSERVICESTATECHANGE': '1630314980',
            'LASTSERVICEOK': '1630314925',
            'SERVICEDOWNTIME': '0',
            'LONGSERVICEOUTPUT': '',
            'SERVICECHECKCOMMAND': 'check_mk-cpu_loads',
            'SERVICEGROUPNAMES': '',
            'SERVICECONTACTGROUPNAMES': 'all',
            'SVC_SL': '',
            'SERVICE_SL': '',
            'SERVICE_EC_CONTACT': '',
            'SERVICENOTESURL': '',
            'SERVICENOTES': '',
            'SERVICEDISPLAYNAME': 'CPU load',
            'LOGDIR': '/omd/sites/heute/var/check_mk/notify',
            'MAIL_COMMAND': "mail -s '$SUBJECT$' '$CONTACTEMAIL$'",
            'WHAT': 'SERVICE',
            'MONITORING_HOST': 'klappclub',
            'OMD_ROOT': '/omd/sites/heute',
            'OMD_SITE': 'heute',
            'DATE': '2021-08-30',
            'SHORTDATETIME': '2021-08-30 11:16:20',
            'LONGDATETIME': 'Mon Aug 30 11:16:20 CEST 2021',
            'HOSTURL': '/check_mk/index.py?start_url=view.py%3Fview_name%3Dhoststatus%26host%3Dheute%26site%3Dheute',
            'SERVICEURL': '/check_mk/index.py?start_url=view.py%3Fview_name%3Dservice%26host%3Dheute%26service%3DCPU%20load%26site%3Dheute',
            'LASTHOSTSTATECHANGE_REL': '0d 02:59:58',
            'LASTSERVICESTATECHANGE_REL': '0d 00:00:02',
            'LASTHOSTUP_REL': '0d 00:00:02',
            'LASTSERVICEOK_REL': '0d 00:00:57',
            'CONTACTNAME': 'check-mk-notify',
            'HOSTSHORTSTATE': 'UP',
            'LASTHOSTSHORTSTATE': 'UP',
            'PREVIOUSHOSTHARDSHORTSTATE': 'UP',
            'SERVICESHORTSTATE': 'CRIT',
            'LASTSERVICESHORTSTATE': 'OK',
            'PREVIOUSSERVICEHARDSHORTSTATE': 'OK',
            'SERVICEFORURL': 'CPU%20load',
            'HOSTFORURL': 'heute',
            'HOSTLABEL_cmk/os_family': 'linux',
            'PARAMETER_FROM_ADDRESS': 'from@lala.com',
            'PARAMETER_FROM_DISPLAY_NAME': 'from_display_name',
            'PARAMETER_REPLY_TO_ADDRESS': 'reply@lala.com',
            'PARAMETER_REPLY_TO_DISPLAY_NAME': 'reply_display_name',
            'PARAMETER_HOST_SUBJECT': 'Check_MK: $HOSTNAME$ - $EVENT_TXT$',
            'PARAMETER_SERVICE_SUBJECT': 'Check_MK: $HOSTNAME$/$SERVICEDESC$ $EVENT_TXT$',
            'PARAMETER_ELEMENTSS': 'omdsite hosttags address abstime reltime longoutput ack_author ack_comment perfdata graph notesurl context',
            'PARAMETER_ELEMENTS_1': 'omdsite',
            'PARAMETER_ELEMENTS_2': 'hosttags',
            'PARAMETER_ELEMENTS_3': 'address',
            'PARAMETER_ELEMENTS_4': 'abstime',
            'PARAMETER_ELEMENTS_5': 'reltime',
            'PARAMETER_ELEMENTS_6': 'longoutput',
            'PARAMETER_ELEMENTS_7': 'ack_author',
            'PARAMETER_ELEMENTS_8': 'ack_comment',
            'PARAMETER_ELEMENTS_9': 'perfdata',
            'PARAMETER_ELEMENTS_10': 'graph',
            'PARAMETER_ELEMENTS_11': 'notesurl',
            'PARAMETER_ELEMENTS_12': 'context',
            'PARAMETER_INSERT_HTML_SECTION': '<HTMLTAG>CONTENT</HTMLTAG>\n',
            'PARAMETER_URL_PREFIX_MANUAL': 'http://my_server/heute/check_mk/',
            'PARAMETER_NO_FLOATING_GRAPHS': 'True',
            'PARAMETER_BULK_SORT_ORDER': 'newest_first',
            'PARAMETER_DISABLE_MULTIPLEXING': 'True',
            'PARAMETER_SMTP_SMARTHOSTSS': '127.0.0.1',
            'PARAMETER_SMTP_SMARTHOSTS_1': '127.0.0.1',
            'PARAMETER_SMTP_PORT': '25',
            'PARAMETER_SMTP_AUTH_METHOD': 'plaintext',
            'PARAMETER_SMTP_AUTH_USER': 'user',
            'PARAMETER_SMTP_AUTH_PASSWORD': 'password',
            'PARAMETER_SMTP_ENCRYPTION': 'starttls',
            'PARAMETER_GRAPHS_PER_NOTIFICATION': '42',
            'PARAMETER_NOTIFICATIONS_WITH_GRAPHS': '42'
        },
    ),
])
def test_create_plugin_context_html_email(context, params, expected):
    assert notify.create_plugin_context(context, params) == expected


@pytest.mark.parametrize("context,params,expected", [
    ({}, {
        'from': {
            'address': 'from@lala.com',
            'display_name': 'my_from_disply_name'
        },
        'reply_to': {
            'address': 'reply@lala.com',
            'display_name': 'my_replay_disply_name'
        },
        'host_subject': 'host_subject',
        'service_subject': 'svc_subject',
        'common_body': 'body_host_and_svc\n',
        'host_body': 'body_tail_host\n',
        'service_body': 'body_tail_svc\n',
        'bulk_sort_order': 'newest_first',
        'disable_multiplexing': True
    }, {
        'PARAMETER_FROM_ADDRESS': 'from@lala.com',
        'PARAMETER_FROM_DISPLAY_NAME': 'my_from_disply_name',
        'PARAMETER_REPLY_TO_ADDRESS': 'reply@lala.com',
        'PARAMETER_REPLY_TO_DISPLAY_NAME': 'my_replay_disply_name',
        'PARAMETER_HOST_SUBJECT': 'host_subject',
        'PARAMETER_SERVICE_SUBJECT': 'svc_subject',
        'PARAMETER_COMMON_BODY': 'body_host_and_svc\n',
        'PARAMETER_HOST_BODY': 'body_tail_host\n',
        'PARAMETER_SERVICE_BODY': 'body_tail_svc\n',
        'PARAMETER_BULK_SORT_ORDER': 'newest_first',
        'PARAMETER_DISABLE_MULTIPLEXING': 'True'
    }),
])
def test_create_plugin_context_ascii_email(context, params, expected):
    assert notify.create_plugin_context(context, params) == expected


@pytest.mark.parametrize("context,params,expected", [
    ({}, {
        'webhook_url': ('webhook_url', 'https://mywebhook.com'),
        'url_prefix': {
            'manual': 'http://my_server/heute/check_mk/'
        },
        'ignore_ssl': True,
        'proxy_url': ('url', 'http://my_proxy')
    }, {
        'PARAMETER_WEBHOOK_URL': 'webhook_url\thttps://mywebhook.com',
        'PARAMETER_URL_PREFIX_MANUAL': 'http://my_server/heute/check_mk/',
        'PARAMETER_IGNORE_SSL': 'True',
        'PARAMETER_PROXY_URL': 'http://my_proxy'
    }),
])
def test_create_plugin_context_cisco_webex(context, params, expected):
    assert notify.create_plugin_context(context, params) == expected


@pytest.mark.parametrize("context,params,expected", [
    (
        {},
        {
            'facility': 3,
            'remote': '127.0.0.1'
        },
        {
            'PARAMETER_FACILITY': '3',
            'PARAMETER_REMOTE': '127.0.0.1'
        },
    ),
])
def test_create_plugin_context_mkeventd(context, params, expected):
    assert notify.create_plugin_context(context, params) == expected


@pytest.mark.parametrize("context,params,expected", [
    (
        {},
        {
            'ilert_api_key': ('ilert_api_key', 'my_api_key'),
            'ignore_ssl': True,
            'proxy_url': ('url', 'http://my_proxy'),
            'ilert_priority': 'LOW',
            'ilert_summary_host': 'host_summary',
            'ilert_summary_service': 'svc_summary',
            'url_prefix': {
                'automatic': 'https'
            }
        },
        {
            'PARAMETER_ILERT_API_KEY': 'ilert_api_key\tmy_api_key',
            'PARAMETER_IGNORE_SSL': 'True',
            'PARAMETER_PROXY_URL': 'http://my_proxy',
            'PARAMETER_ILERT_PRIORITY': 'LOW',
            'PARAMETER_ILERT_SUMMARY_HOST': 'host_summary',
            'PARAMETER_ILERT_SUMMARY_SERVICE': 'svc_summary',
            'PARAMETER_URL_PREFIX_AUTOMATIC': 'https'
        },
    ),
])
def test_create_plugin_context_ilert(context, params, expected):
    assert notify.create_plugin_context(context, params) == expected


@pytest.mark.parametrize("context,params,expected", [
    (
        {},
        {
            'url': 'http://my_jira_url',
            'username': 'user',
            'password': 'password',
            'project': '1001',
            'issuetype': '1002',
            'host_customid': '1003',
            'service_customid': '1004',
            'site_customid': '1005',
            'monitoring': 'http://my_server(check_mk/',
            'priority': '1006',
            'host_summary': 'host_summary',
            'service_summary': 'svc_summary',
            'label': 'label',
            'resolution': '42',
            'timeout': '24'
        },
        {
            'PARAMETER_URL': 'http://my_jira_url',
            'PARAMETER_USERNAME': 'user',
            'PARAMETER_PASSWORD': 'password',
            'PARAMETER_PROJECT': '1001',
            'PARAMETER_ISSUETYPE': '1002',
            'PARAMETER_HOST_CUSTOMID': '1003',
            'PARAMETER_SERVICE_CUSTOMID': '1004',
            'PARAMETER_SITE_CUSTOMID': '1005',
            'PARAMETER_MONITORING': 'http://my_server(check_mk/',
            'PARAMETER_PRIORITY': '1006',
            'PARAMETER_HOST_SUMMARY': 'host_summary',
            'PARAMETER_SERVICE_SUMMARY': 'svc_summary',
            'PARAMETER_LABEL': 'label',
            'PARAMETER_RESOLUTION': '42',
            'PARAMETER_TIMEOUT': '24'
        },
    ),
])
def test_create_plugin_context_jira(context, params, expected):
    assert notify.create_plugin_context(context, params) == expected


@pytest.mark.parametrize("context,params,expected", [
    (
        {},
        {
            'password': ('password', 'tsrhhtesh5636546djhrejrt'),
            'url': 'https://my_domain',
            'proxy_url': ('url', 'http://my_proxy'),
            'owner': 'ower',
            'source': 'source',
            'priority': 'P2',
            'note_created': 'open note',
            'note_closed': 'close note',
            'host_msg': 'host_desc',
            'svc_msg': 'service_desc',
            'host_desc': 'host_msg\n',
            'svc_desc': 'svc_msg\n',
            'teams': ['team1', 'team2', 'team3'],
            'actions': ['action1', 'actin2', 'action3'],
            'tags': ['tag1', 'tag2', 'tag3'],
            'entity': 'entity'
        },
        {
            'PARAMETER_PASSWORD': 'password\ttsrhhtesh5636546djhrejrt',
            'PARAMETER_URL': 'https://my_domain',
            'PARAMETER_PROXY_URL': 'http://my_proxy',
            'PARAMETER_OWNER': 'ower',
            'PARAMETER_SOURCE': 'source',
            'PARAMETER_PRIORITY': 'P2',
            'PARAMETER_NOTE_CREATED': 'open note',
            'PARAMETER_NOTE_CLOSED': 'close note',
            'PARAMETER_HOST_MSG': 'host_desc',
            'PARAMETER_SVC_MSG': 'service_desc',
            'PARAMETER_HOST_DESC': 'host_msg\n',
            'PARAMETER_SVC_DESC': 'svc_msg\n',
            'PARAMETER_TEAMSS': 'team1 team2 team3',
            'PARAMETER_TEAMS_1': 'team1',
            'PARAMETER_TEAMS_2': 'team2',
            'PARAMETER_TEAMS_3': 'team3',
            'PARAMETER_ACTIONSS': 'action1 actin2 action3',
            'PARAMETER_ACTIONS_1': 'action1',
            'PARAMETER_ACTIONS_2': 'actin2',
            'PARAMETER_ACTIONS_3': 'action3',
            'PARAMETER_TAGSS': 'tag1 tag2 tag3',
            'PARAMETER_TAGS_1': 'tag1',
            'PARAMETER_TAGS_2': 'tag2',
            'PARAMETER_TAGS_3': 'tag3',
            'PARAMETER_ENTITY': 'entity'
        },
    ),
])
def test_create_plugin_context_opsgenie(context, params, expected):
    assert notify.create_plugin_context(context, params) == expected


@pytest.mark.parametrize("context,params,expected", [
    (
        {},
        {
            'routing_key': ('routing_key', 'aewgwaeg86969698698ewfa'),
            'webhook_url': 'https://events.pagerduty.com/v2/enqueue',
            'ignore_ssl': True,
            'proxy_url': ('environment', 'environment'),
            'url_prefix': {
                'automatic': 'https'
            }
        },
        {
            'PARAMETER_ROUTING_KEY': 'routing_key\taewgwaeg86969698698ewfa',
            'PARAMETER_WEBHOOK_URL': 'https://events.pagerduty.com/v2/enqueue',
            'PARAMETER_IGNORE_SSL': 'True',
            'PARAMETER_URL_PREFIX_AUTOMATIC': 'https'
        },
    ),
])
def test_create_plugin_context_pagerduty(context, params, expected):
    assert notify.create_plugin_context(context, params) == expected


@pytest.mark.parametrize("context,params,expected", [
    (
        {},
        {
            'api_key': 'ahdksowirp38pt49jh48lkjhgfdswe',
            'recipient_key': 'lkiopowirp38pt49jh48lkjhgfdswe',
            'url_prefix': 'http://my_server/heute/check_mk/',
            'proxy_url': ('environment', 'environment'),
            'priority': '-1',
            'sound': 'classical'
        },
        {
            'PARAMETER_API_KEY': 'ahdksowirp38pt49jh48lkjhgfdswe',
            'PARAMETER_RECIPIENT_KEY': 'lkiopowirp38pt49jh48lkjhgfdswe',
            'PARAMETER_URL_PREFIX': 'http://my_server/heute/check_mk/',
            'PARAMETER_PRIORITY': '-1',
            'PARAMETER_SOUND': 'classical'
        },
    ),
])
def test_create_plugin_context_push_notifications(context, params, expected):
    assert notify.create_plugin_context(context, params) == expected


@pytest.mark.parametrize("context,params,expected", [
    (
        {},
        {
            'url': 'http://my_url',
            'proxy_url': ('no_proxy', None),
            'username': 'user',
            'password': ('password', 'password'),
            'use_site_id': True,
            'caller': 'user',
            'host_short_desc': 'host_shot_desc',
            'svc_short_desc': 'svc_shot_desc',
            'host_desc': 'Host: $HOSTNAME$\nEvent:    $EVENT_TXT$\nOutput:   $HOSTOUTPUT$\nPerfdata: $HOSTPERFDATA$\n$LONGHOSTOUTPUT$\n',
            'svc_desc': 'Host: $HOSTNAME$\nService:  $SERVICEDESC$\nEvent:    $EVENT_TXT$\nOutput:   $SERVICEOUTPUT$\nPerfdata: $SERVICEPERFDATA$\n$LONGSERVICEOUTPUT$\n',
            'urgency': 'medium',
            'impact': 'medium',
            'ack_state': {
                'start': 'progress'
            },
            'recovery_state': {
                'start': 42
            },
            'dt_state': {
                'start': 'canceled'
            },
            'timeout': '42'
        },
        {
            'PARAMETER_URL': 'http://my_url',
            'PARAMETER_PROXY_URL': '',
            'PARAMETER_USERNAME': 'user',
            'PARAMETER_PASSWORD': 'password\tpassword',
            'PARAMETER_USE_SITE_ID': 'True',
            'PARAMETER_CALLER': 'user',
            'PARAMETER_HOST_SHORT_DESC': 'host_shot_desc',
            'PARAMETER_SVC_SHORT_DESC': 'svc_shot_desc',
            'PARAMETER_HOST_DESC': 'Host: $HOSTNAME$\nEvent:    $EVENT_TXT$\nOutput:   $HOSTOUTPUT$\nPerfdata: $HOSTPERFDATA$\n$LONGHOSTOUTPUT$\n',
            'PARAMETER_SVC_DESC': 'Host: $HOSTNAME$\nService:  $SERVICEDESC$\nEvent:    $EVENT_TXT$\nOutput:   $SERVICEOUTPUT$\nPerfdata: $SERVICEPERFDATA$\n$LONGSERVICEOUTPUT$\n',
            'PARAMETER_URGENCY': 'medium',
            'PARAMETER_IMPACT': 'medium',
            'PARAMETER_ACK_STATE_START': 'progress',
            'PARAMETER_RECOVERY_STATE_START': '42',
            'PARAMETER_DT_STATE_START': 'canceled',
            'PARAMETER_TIMEOUT': '42'
        },
    ),
])
def test_create_plugin_context_servicenow(context, params, expected):
    assert notify.create_plugin_context(context, params) == expected


@pytest.mark.parametrize("context,params,expected", [
    (
        {},
        {
            'password': ('password', 'scret'),
            'ignore_ssl': True,
            'proxy_url': ('no_proxy', None),
            'url_prefix': {
                'manual': 'http://my_server/heute/check_mk/'
            }
        },
        {
            'PARAMETER_PASSWORD': 'password\tscret',
            'PARAMETER_IGNORE_SSL': 'True',
            'PARAMETER_PROXY_URL': '',
            'PARAMETER_URL_PREFIX_MANUAL': 'http://my_server/heute/check_mk/'
        },
    ),
])
def test_create_plugin_context_signl4(context, params, expected):
    assert notify.create_plugin_context(context, params) == expected


@pytest.mark.parametrize("context,params,expected", [
    (
        {},
        {
            'webhook_url': ('webhook_url', 'https://_my_webhook_url'),
            'ignore_ssl': True,
            'url_prefix': {
                'manual': 'http://my_server/heute/check_mk/'
            },
            'proxy_url': ('url', 'http://my_proxy')
        },
        {
            'PARAMETER_WEBHOOK_URL': 'webhook_url\thttps://_my_webhook_url',
            'PARAMETER_IGNORE_SSL': 'True',
            'PARAMETER_URL_PREFIX_MANUAL': 'http://my_server/heute/check_mk/',
            'PARAMETER_PROXY_URL': 'http://my_proxy'
        },
    ),
])
def test_create_plugin_context_slack(context, params, expected):
    assert notify.create_plugin_context(context, params) == expected


@pytest.mark.parametrize("context,params,expected", [
    (
        {},
        ['myparameter'],
        {
            'PARAMETERS': 'myparameter',
            'PARAMETER_1': 'myparameter'
        },
    ),
])
def test_create_plugin_context_sms(context, params, expected):
    assert notify.create_plugin_context(context, params) == expected


@pytest.mark.parametrize("context,params,expected", [
    (
        {},
        {
            'destination': '127.0.0.1',
            'community': 'community',
            'baseoid': '1.3.6.1.4.1.1234'
        },
        {
            'PARAMETER_DESTINATION': '127.0.0.1',
            'PARAMETER_COMMUNITY': 'community',
            'PARAMETER_BASEOID': '1.3.6.1.4.1.1234'
        },
    ),
])
def test_create_plugin_context_spectrum(context, params, expected):
    assert notify.create_plugin_context(context, params) == expected
