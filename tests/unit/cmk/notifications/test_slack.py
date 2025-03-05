#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.notification_plugins.slack import _message


@pytest.mark.parametrize(
    "context, result",
    [
        (
            {
                "PARAMETER_WEBHOOK_URL": "webhook_url\texample.slack.com/not-real",  # slack format
                "PARAMETER_URL_PREFIX_1": "automatic_http",
                "MONITORING_HOST": "localhost",
                "OMD_SITE": "testsite",
                "HOSTURL": "/view?key=val",
                "SERVICEURL": "/view?key=val2",
                "HOSTNAME": "site1",
                "SERVICEDESC": "first",
                "SERVICESTATE": "CRITICAL",
                "NOTIFICATIONTYPE": "PROBLEM",
                "HOSTADDRESS": "127.0.0.1",
                "SERVICEOUTPUT": "Service Down",
                "WHAT": "SERVICE",
                "CONTACTNAME": "John,Doe",
                "MICROTIME": "1537363754000000",
                "LONGDATETIME": "Wed Sep 19 15:29:14 CEST 2018",
            },
            {
                "blocks": [
                    {
                        "type": "rich_text",
                        "elements": [
                            {
                                "type": "rich_text_section",
                                "elements": [
                                    {"name": "rotating_light", "type": "emoji"},
                                    {
                                        "type": "text",
                                        "text": " Problem (Critical): Service ",
                                        "style": {"bold": True},
                                    },
                                    {
                                        "type": "link",
                                        "text": "first",
                                        "url": "http://localhost/testsite/view?key=val2",
                                        "style": {"bold": True},
                                    },
                                    {"type": "text", "text": " on ", "style": {"bold": True}},
                                    {
                                        "type": "link",
                                        "text": "site1",
                                        "url": "http://localhost/testsite/view?key=val",
                                        "style": {"bold": True},
                                    },
                                    {
                                        "type": "text",
                                        "text": "\nAdditional Info\n",
                                        "style": {"bold": True},
                                    },
                                    {"type": "text", "text": "Service Down\n"},
                                    {"type": "text", "text": "Please take a look: "},
                                    {"type": "user", "user_id": "John"},
                                    {"type": "text", "text": ", "},
                                    {"type": "user", "user_id": "Doe"},
                                    {"type": "text", "text": "\n"},
                                    {"type": "text", "text": "Check_MK notification: "},
                                    {
                                        "type": "date",
                                        "timestamp": 1537363754,
                                        "format": "{date_short_pretty} {time_secs}, {ago}",
                                        "fallback": "Wed Sep 19 15:29:14 CEST 2018",
                                    },
                                ],
                            }
                        ],
                    }
                ]
            },
        ),
        (
            {
                "PARAMETER_WEBHOOK_URL": "webhook_url\texample.mattermost.com/not-real",  # mattermost format
                "PARAMETER_URL_PREFIX_1": "automatic_http",
                "MONITORING_HOST": "localhost",
                "OMD_SITE": "testsite",
                "HOSTURL": "/view?key=val",
                "SERVICEURL": "/view?key=val2",
                "HOSTNAME": "site1",
                "SERVICEDESC": "first",
                "SERVICESTATE": "CRITICAL",
                "NOTIFICATIONTYPE": "PROBLEM",
                "HOSTADDRESS": "127.0.0.1",
                "SERVICEOUTPUT": "Service Down",
                "WHAT": "SERVICE",
                "CONTACTNAME": "John,Doe",
                "LONGDATETIME": "Wed Sep 19 15:29:14 CEST 2018",
            },
            {
                "attachments": [
                    {
                        "color": "#EE0000",
                        "title": "Problem (Critical): Service first",
                        "title_link": "http://localhost/testsite/view?key=val2",
                        "text": (
                            "Host: [site1](http://localhost/testsite/view?key=val)\n"
                            "**Additional Info**\nService Down\n"
                            "Please take a look: @John, @Doe"
                        ),
                        "footer": "Check_MK notification: Wed Sep 19 15:29:14 CEST 2018",
                    }
                ]
            },
        ),
        (
            {
                "PARAMETER_WEBHOOK_URL": "webhook_url\texample.slack.com/not-real",  # slack format
                "PARAMETER_URL_PREFIX_1": "automatic_https",
                "MONITORING_HOST": "localhost",
                "OMD_SITE": "testsite",
                "HOSTURL": "/view?key=val",
                "HOSTNAME": "site1",
                "HOSTSTATE": "DOWN",
                "HOSTOUTPUT": "Manually set to Down by cmkadmin",
                "NOTIFICATIONTYPE": "PROBLEM",
                "HOSTADDRESS": "127.0.0.1",
                "WHAT": "HOST",
                "CONTACTNAME": "John",
                "MICROTIME": "1537363754000000",
                "LONGDATETIME": "Wed Sep 19 15:29:14 CEST 2018",
            },
            {
                "blocks": [
                    {
                        "type": "rich_text",
                        "elements": [
                            {
                                "type": "rich_text_section",
                                "elements": [
                                    {"name": "rotating_light", "type": "emoji"},
                                    {
                                        "type": "text",
                                        "text": " Problem (Down): Host ",
                                        "style": {"bold": True},
                                    },
                                    {
                                        "type": "link",
                                        "text": "site1",
                                        "url": "https://localhost/testsite/view?key=val",
                                        "style": {"bold": True},
                                    },
                                    {
                                        "type": "text",
                                        "text": "\nAdditional Info\n",
                                        "style": {"bold": True},
                                    },
                                    {"type": "text", "text": "Manually set to Down by cmkadmin\n"},
                                    {"type": "text", "text": "Please take a look: "},
                                    {"type": "user", "user_id": "John"},
                                    {"type": "text", "text": "\n"},
                                    {"type": "text", "text": "Check_MK notification: "},
                                    {
                                        "type": "date",
                                        "timestamp": 1537363754,
                                        "format": "{date_short_pretty} {time_secs}, {ago}",
                                        "fallback": "Wed Sep 19 15:29:14 CEST 2018",
                                    },
                                ],
                            }
                        ],
                    }
                ]
            },
        ),
        (
            {
                "PARAMETER_WEBHOOK_URL": "webhook_url\texample.mattermost.com/not-real",  # mattermost format
                "PARAMETER_URL_PREFIX_1": "automatic_https",
                "MONITORING_HOST": "localhost",
                "OMD_SITE": "testsite",
                "HOSTURL": "/view?key=val",
                "HOSTNAME": "site1",
                "HOSTSTATE": "DOWN",
                "HOSTOUTPUT": "Manually set to Down by cmkadmin",
                "NOTIFICATIONTYPE": "PROBLEM",
                "HOSTADDRESS": "127.0.0.1",
                "WHAT": "HOST",
                "CONTACTNAME": "John",
                "LONGDATETIME": "Wed Sep 19 15:29:14 CEST 2018",
            },
            {
                "attachments": [
                    {
                        "color": "#EE0000",
                        "title": "Problem (Down): Host site1",
                        "title_link": "https://localhost/testsite/view?key=val",
                        "text": (
                            "**Additional Info**\nManually set to Down by cmkadmin\n"
                            "Please take a look: @John"
                        ),
                        "footer": "Check_MK notification: Wed Sep 19 15:29:14 CEST 2018",
                    }
                ]
            },
        ),
    ],
)
def test_slack_message(context: dict[str, str], result: dict[str, list[dict[str, str]]]) -> None:
    msg = _message(context)
    assert msg == result
