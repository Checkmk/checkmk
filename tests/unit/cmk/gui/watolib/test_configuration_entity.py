#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.watolib.configuration_entity import configuration_entity as ce
from cmk.shared_typing.configuration_entity import ConfigEntityType


@pytest.mark.parametrize(
    "specifier, expected",
    [
        ("asciimail", "ASCII Email parameter"),
        ("cisco_webex_teams", "Cisco Webex Teams parameter"),
        ("ilert", "iLert parameter"),
        ("jira_issues", "JIRA (Commercial editions only) parameter"),
        ("mail", "HTML Email parameter"),
        ("mkeventd", "Forward Notification to Event Console parameter"),
        ("msteams", "Microsoft Teams parameter"),
        ("opsgenie_issues", "Opsgenie parameter"),
        ("pagerduty", "PagerDuty parameter"),
        ("pushover", "Push Notifications (using Pushover) parameter"),
        ("servicenow", "Servicenow (Enterprise only) parameter"),
        ("signl4", "SIGNL4 Alerting parameter"),
        ("slack", "Slack or Mattermost parameter"),
        ("sms", "SMS (using smstools) parameter"),
        ("sms_api", "SMS (using modem API) parameter"),
        ("spectrum", "Spectrum Server parameter"),
        ("victorops", "Splunk On-Call parameter"),
        pytest.param("unknown", "unknown parameter", id="Fallback to specifier when not found."),
    ],
)
def test_get_readable_entity_selection__notification_parameter(
    specifier: str, expected: str
) -> None:
    value = ce.get_readable_entity_selection(
        entity_type=ConfigEntityType.notification_parameter,
        entity_type_specifier=specifier,
    )
    assert value == expected
