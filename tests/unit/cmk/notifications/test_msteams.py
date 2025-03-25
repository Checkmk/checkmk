#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.notification_plugins.msteams import _msteams_msg


@pytest.mark.parametrize(
    "context, result",
    [
        (
            {
                "NOTIFICATIONTYPE": "PROBLEM",
                "WHAT": "SERVICE",
                "PARAMETER_URL_PREFIX_1": "automatic_http",
                "MONITORING_HOST": "localhost",
                "OMD_SITE": "testsite",
                "HOSTNAME": "test-host",
                "SERVICEDESC": "Systemd Service Summary",
                "SERVICESTATE": "CRITICAL",
                "SERVICESHORTSTATE": "CRIT",
                "SERVICEOUTPUT": "Total: 174, Disabled: 6, Failed: 3, 2 services failed (apache2, omd)(!!), 1 static service failed (apport-autoreport)(!!)",
                "SERVICEPERFDATA": "Service perfdata",
                "LONGSERVICEOUTPUT": "Total: 174\\nDisabled: 6\\nFailed: 3\\n2 services failed (apache2, omd)(!!)\\n1 static service failed (apport-autoreport)(!!)",
                "SERVICEURL": "/view?key=test-service",
                "EVENT_TXT": "Event text",
                "NOTIFICATIONAUTHOR": "John Doe",
                "NOTIFICATIONCOMMENT": "Some comment",
            },
            {
                "type": "message",
                "attachments": [
                    {
                        "contentType": "application/vnd.microsoft.card.adaptive",
                        "contentUrl": "null",
                        "content": {
                            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                            "msteams": {"width": "Full"},
                            "type": "AdaptiveCard",
                            "version": "1.3",
                            "actions": [
                                {
                                    "type": "Action.OpenUrl",
                                    "role": "Button",
                                    "title": "View service details in Checkmk",
                                    "url": "http://localhost/testsite/view?key=test-service",
                                }
                            ],
                            "body": [
                                {
                                    "type": "TextBlock",
                                    "text": "Checkmk: test-host/Systemd Service Summary CRIT",
                                    "size": "large",
                                    "style": "heading",
                                    "weight": "bolder",
                                    "wrap": True,
                                },
                                {
                                    "type": "TextBlock",
                                    "text": "Problem notification",
                                    "weight": "bolder",
                                    "wrap": True,
                                },
                                {
                                    "type": "TextBlock",
                                    "text": "Checkmk: test-host/Systemd Service Summary Event text",
                                    "wrap": True,
                                },
                                {
                                    "type": "ColumnSet",
                                    "separator": True,
                                    "columns": [
                                        {
                                            "type": "Column",
                                            "width": "auto",
                                            "items": [
                                                {
                                                    "type": "TextBlock",
                                                    "text": "Details",
                                                    "wrap": True,
                                                    "weight": "bolder",
                                                }
                                            ],
                                        },
                                        {
                                            "type": "Column",
                                            "width": "stretch",
                                            "items": [
                                                {
                                                    "type": "TextBlock",
                                                    "text": "__Host__: test-host",
                                                    "spacing": "none",
                                                    "wrap": True,
                                                },
                                                {
                                                    "type": "TextBlock",
                                                    "text": "__Service__:  Systemd Service Summary",
                                                    "spacing": "none",
                                                    "wrap": True,
                                                },
                                                {
                                                    "type": "TextBlock",
                                                    "text": "__Event__:    Event text",
                                                    "spacing": "none",
                                                    "wrap": True,
                                                },
                                                {
                                                    "type": "TextBlock",
                                                    "text": (
                                                        "__Output__:   Total: 174, Disabled: 6, Failed: 3, 2 "
                                                        "services failed (apache2, omd)(!!), 1 static service "
                                                        "failed (apport-autoreport)(!!)"
                                                    ),
                                                    "spacing": "none",
                                                    "wrap": True,
                                                },
                                                {
                                                    "type": "TextBlock",
                                                    "text": "__Perfdata__: Service perfdata",
                                                    "spacing": "none",
                                                    "wrap": True,
                                                },
                                                {
                                                    "type": "TextBlock",
                                                    "text": "Total: 174",
                                                    "separator": True,
                                                    "wrap": True,
                                                },
                                                {
                                                    "type": "TextBlock",
                                                    "text": "Disabled: 6",
                                                    "spacing": "none",
                                                    "wrap": True,
                                                },
                                                {
                                                    "type": "TextBlock",
                                                    "text": "Failed: 3",
                                                    "spacing": "none",
                                                    "wrap": True,
                                                },
                                                {
                                                    "type": "TextBlock",
                                                    "text": "2 services failed (apache2, omd)(!!)",
                                                    "spacing": "none",
                                                    "wrap": True,
                                                },
                                                {
                                                    "type": "TextBlock",
                                                    "text": "1 static service failed (apport-autoreport)(!!)\n",
                                                    "spacing": "none",
                                                    "wrap": True,
                                                },
                                            ],
                                        },
                                    ],
                                },
                                {
                                    "type": "FactSet",
                                    "separator": True,
                                    "facts": [
                                        {"title": "Author", "value": "John Doe"},
                                        {"title": "Comment", "value": "Some comment"},
                                    ],
                                },
                            ],
                        },
                    }
                ],
            },
        ),
        (
            {
                "NOTIFICATIONTYPE": "PROBLEM",
                "WHAT": "HOST",
                "MONITORING_HOST": "localhost",
                "OMD_SITE": "testsite",
                "HOSTNAME": "test-host",
                "HOSTSTATE": "DOWN",
                "HOSTSHORTSTATE": "DOWN",
                "LONGHOSTOUTPUT": "Host is down, long output",
                "HOSTPERFDATA": "Host perfdata",
                "HOSTOUTPUT": "Manually set to Down by cmkadmin",
                "EVENT_TXT": "Event text",
                "HOSTADDRESS": "127.0.0.1",
                "HOSTURL": "/view?key=test-host",
                "NOTIFICATIONAUTHOR": "",
            },
            {
                "type": "message",
                "attachments": [
                    {
                        "contentType": "application/vnd.microsoft.card.adaptive",
                        "contentUrl": "null",
                        "content": {
                            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                            "msteams": {"width": "Full"},
                            "type": "AdaptiveCard",
                            "version": "1.3",
                            "actions": [],
                            "body": [
                                {
                                    "type": "TextBlock",
                                    "text": "Checkmk: test-host - DOWN",
                                    "size": "large",
                                    "style": "heading",
                                    "weight": "bolder",
                                    "wrap": True,
                                },
                                {
                                    "type": "TextBlock",
                                    "text": "Problem notification",
                                    "weight": "bolder",
                                    "wrap": True,
                                },
                                {
                                    "type": "TextBlock",
                                    "text": "Checkmk: test-host - Event text",
                                    "wrap": True,
                                },
                                {
                                    "type": "ColumnSet",
                                    "separator": True,
                                    "columns": [
                                        {
                                            "type": "Column",
                                            "width": "auto",
                                            "items": [
                                                {
                                                    "type": "TextBlock",
                                                    "text": "Details",
                                                    "wrap": True,
                                                    "weight": "bolder",
                                                }
                                            ],
                                        },
                                        {
                                            "type": "Column",
                                            "width": "stretch",
                                            "items": [
                                                {
                                                    "type": "TextBlock",
                                                    "text": "__Host__: test-host",
                                                    "spacing": "none",
                                                    "wrap": True,
                                                },
                                                {
                                                    "type": "TextBlock",
                                                    "text": "__Event__:    Event text",
                                                    "spacing": "none",
                                                    "wrap": True,
                                                },
                                                {
                                                    "type": "TextBlock",
                                                    "text": "__Output__:   Manually set to Down by cmkadmin",
                                                    "spacing": "none",
                                                    "wrap": True,
                                                },
                                                {
                                                    "type": "TextBlock",
                                                    "text": "__Perfdata__: Host perfdata",
                                                    "spacing": "none",
                                                    "wrap": True,
                                                },
                                                {
                                                    "type": "TextBlock",
                                                    "text": "Host is down, long output\n",
                                                    "separator": True,
                                                    "wrap": True,
                                                },
                                            ],
                                        },
                                    ],
                                },
                            ],
                        },
                    }
                ],
            },
        ),
    ],
)
def test_msteams_message(context: dict[str, str], result: dict[str, list[dict[str, str]]]) -> None:
    msg = _msteams_msg(context)
    assert msg == result
