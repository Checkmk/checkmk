#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
from collections.abc import Mapping
from typing import Final

import pytest
from pytest import MonkeyPatch

from cmk.base import notify
from cmk.events.event_context import EnrichedEventContext, EventContext
from cmk.utils.http_proxy_config import EnvironmentProxyConfig
from cmk.utils.notify_types import (
    Contact,
    ContactName,
    EventRule,
    NotificationContext,
    NotificationRuleID,
    NotifyPluginParamsDict,
)

HTTP_PROXY: Final = EnvironmentProxyConfig()


def test_os_environment_does_not_override_notification_script_env(monkeypatch: MonkeyPatch) -> None:
    """Regression test for Werk #7339"""
    monkeypatch.setattr(os, "environ", {"NOTIFY_CONTACTEMAIL": ""})
    notification_context = NotificationContext({"CONTACTEMAIL": "ab@test.de"})
    script_env = notify.notification_script_env(notification_context)
    assert script_env == {"NOTIFY_CONTACTEMAIL": "ab@test.de"}


@pytest.mark.parametrize(
    "environ,expected",
    [
        ({}, {}),
        (
            {"TEST": "test"},
            {},
        ),
        (
            {"NOTIFY_TEST": "test"},
            {"TEST": "test"},
        ),
        (
            {"NOTIFY_SERVICEOUTPUT": "LONGSERVICEOUTPUT=with_light_vertical_bar_\u2758"},
            {"SERVICEOUTPUT": "LONGSERVICEOUTPUT=with_light_vertical_bar_|"},
        ),
        (
            {"NOTIFY_LONGSERVICEOUTPUT": "LONGSERVICEOUTPUT=with_light_vertical_bar_\u2758"},
            {"LONGSERVICEOUTPUT": "LONGSERVICEOUTPUT=with_light_vertical_bar_|"},
        ),
    ],
)
def test_raw_context_from_env_pipe_decoding(
    environ: Mapping[str, str], expected: EventContext
) -> None:
    assert notify.raw_context_from_env(environ) == expected


@pytest.mark.parametrize(
    "enriched_context,params,expected",
    [
        (
            {},
            {
                "from": {"address": "from@lala.com", "display_name": "from_display_name"},
                "reply_to": {"address": "reply@lala.com", "display_name": "reply_display_name"},
                "host_subject": "Check_MK: $HOSTNAME$ - $EVENT_TXT$",
                "service_subject": "Check_MK: $HOSTNAME$/$SERVICEDESC$ $EVENT_TXT$",
            },
            {
                "PARAMETER_FROM_ADDRESS": "from@lala.com",
                "PARAMETER_FROM_DISPLAY_NAME": "from_display_name",
                "PARAMETER_REPLY_TO_ADDRESS": "reply@lala.com",
                "PARAMETER_REPLY_TO_DISPLAY_NAME": "reply_display_name",
                "PARAMETER_HOST_SUBJECT": "Check_MK: $HOSTNAME$ - $EVENT_TXT$",
                "PARAMETER_SERVICE_SUBJECT": "Check_MK: $HOSTNAME$/$SERVICEDESC$ $EVENT_TXT$",
            },
        ),
    ],
)
def test_create_plugin_context(
    enriched_context: EnrichedEventContext,
    params: NotifyPluginParamsDict,
    expected: NotificationContext,
) -> None:
    assert (
        notify.create_plugin_context(
            enriched_context,
            params,
            lambda *args, **kw: HTTP_PROXY,
        )
        == expected
    )


@pytest.fixture(name="user_groups")
def fixture_user_groups() -> Mapping[ContactName, list[str]]:
    return {
        "ding": ["foo"],
        "dong": ["bar", "all"],
        "harry": ["foo"],
    }


def test_rbn_groups_contacts(user_groups: Mapping[ContactName, list[str]]) -> None:
    contacts = {name: Contact({"contactgroups": groups}) for name, groups in user_groups.items()}
    assert notify.rbn_groups_contacts([], config_contacts=contacts) == set()
    assert notify.rbn_groups_contacts(["nono"], config_contacts=contacts) == set()
    assert notify.rbn_groups_contacts(["all"], config_contacts=contacts) == {"dong"}
    assert notify.rbn_groups_contacts(["foo"], config_contacts=contacts) == {"ding", "harry"}
    assert notify.rbn_groups_contacts(["foo", "all"], config_contacts=contacts) == {
        "ding",
        "dong",
        "harry",
    }


@pytest.mark.parametrize(
    "event_rule, context, expected",
    [
        pytest.param(
            EventRule(
                rule_id=NotificationRuleID("1"),
                allow_disable=False,
                contact_all=False,
                contact_all_with_email=False,
                contact_object=False,
                description="Test rule 1",
                disabled=False,
                notify_plugin=("mail", None),
            ),
            {
                "EC_ID": "test1",
            },
            "Notification has been created by the Event Console.",
            id="Do not match Event Console alerts, notification from Event Console",
        ),
        pytest.param(
            EventRule(
                rule_id=NotificationRuleID("2"),
                allow_disable=False,
                contact_all=False,
                contact_all_with_email=False,
                contact_object=False,
                description="Test rule 2",
                disabled=False,
                notify_plugin=("mail", None),
                match_ec={},
            ),
            {
                "PARAMETER_FROM_ADDRESS": "from@lala.com",
            },
            "Notification has not been created by the Event Console.",
            id="Match only Event Console alerts, no notification from Event Console",
        ),
        pytest.param(
            EventRule(
                rule_id=NotificationRuleID("3"),
                allow_disable=False,
                contact_all=False,
                contact_all_with_email=False,
                contact_object=False,
                description="Test rule 3",
                disabled=False,
                notify_plugin=("mail", None),
            ),
            {
                "EC_ID": "test3",
            },
            "Notification has been created by the Event Console.",
            id="No matching on Event Console alerts (option unchecked), notification from Event Console",
        ),
        pytest.param(
            EventRule(
                rule_id=NotificationRuleID("4"),
                allow_disable=False,
                contact_all=False,
                contact_all_with_email=False,
                contact_object=False,
                description="Test rule 4",
                disabled=False,
                notify_plugin=("mail", None),
            ),
            {
                "PARAMETER_FROM_ADDRESS": "from@lala.com",
            },
            None,
            id="No matching on Event Console alerts (option unchecked), no notification from Event Console",
        ),
        pytest.param(
            EventRule(
                rule_id=NotificationRuleID("5"),
                allow_disable=False,
                contact_all=False,
                contact_all_with_email=False,
                contact_object=False,
                description="Test rule 5",
                disabled=False,
                notify_plugin=("mail", None),
                match_ec={"match_rule_id": ["test_rule_id_5"]},
            ),
            {
                "EC_ID": "test5",
                "EC_RULE_ID": "test_rule_id_5",
            },
            None,
            id="Match on Event Console rule ID",
        ),
        pytest.param(
            EventRule(
                rule_id=NotificationRuleID("6"),
                allow_disable=False,
                contact_all=False,
                contact_all_with_email=False,
                contact_object=False,
                description="Test rule 6",
                disabled=False,
                notify_plugin=("mail", None),
                match_ec={"match_rule_id": ["test_rule_id_6"]},
            ),
            {
                "EC_ID": "test6",
                "EC_RULE_ID": "test_rule_id_11",
            },
            "EC Event has rule ID 'test_rule_id_11', but '['test_rule_id_6']' is required",
            id="No match on Event Console rule ID",
        ),
        pytest.param(
            EventRule(
                rule_id=NotificationRuleID("7"),
                allow_disable=False,
                contact_all=False,
                contact_all_with_email=False,
                contact_object=False,
                description="Test rule 7",
                disabled=False,
                notify_plugin=("mail", None),
                match_ec={"match_priority": (4, 0)},
            ),
            {
                "EC_ID": "test7",
                "EC_PRIORITY": "2",
            },
            None,
            id="Match on Event Console syslog priority",
        ),
        pytest.param(
            EventRule(
                rule_id=NotificationRuleID("8"),
                allow_disable=False,
                contact_all=False,
                contact_all_with_email=False,
                contact_object=False,
                description="Test rule 8",
                disabled=False,
                notify_plugin=("mail", None),
                match_ec={"match_priority": (4, 0)},
            ),
            {
                "EC_ID": "test8",
                "EC_PRIORITY": "5",
            },
            "Event has priority 5, but matched range is 0 .. 4",
            id="No match on Event Console syslog priority",
        ),
        pytest.param(
            EventRule(
                rule_id=NotificationRuleID("9"),
                allow_disable=False,
                contact_all=False,
                contact_all_with_email=False,
                contact_object=False,
                description="Test rule 9",
                disabled=False,
                notify_plugin=("mail", None),
                match_ec={"match_facility": 0},
            ),
            {
                "EC_ID": "test9",
                "EC_FACILITY": "0",
            },
            None,
            id="Match on Event Console syslog facility",
        ),
        pytest.param(
            EventRule(
                rule_id=NotificationRuleID("10"),
                allow_disable=False,
                contact_all=False,
                contact_all_with_email=False,
                contact_object=False,
                description="Test rule 10",
                disabled=False,
                notify_plugin=("mail", None),
                match_ec={"match_facility": 3},
            ),
            {
                "EC_ID": "test10",
                "EC_FACILITY": "0",
            },
            "Wrong syslog facility 0, required is 3",
            id="No match on Event Console syslog facility",
        ),
        pytest.param(
            EventRule(
                rule_id=NotificationRuleID("11"),
                allow_disable=False,
                contact_all=False,
                contact_all_with_email=False,
                contact_object=False,
                description="Test rule 11",
                disabled=False,
                notify_plugin=("mail", None),
                match_ec={"match_comment": "some test comment"},
            ),
            {
                "EC_ID": "test11",
                "EC_COMMENT": "some test comment",
            },
            None,
            id="Match on Event Console comment",
        ),
        pytest.param(
            EventRule(
                rule_id=NotificationRuleID("12"),
                allow_disable=False,
                contact_all=False,
                contact_all_with_email=False,
                contact_object=False,
                description="Test rule 12",
                disabled=False,
                notify_plugin=("mail", None),
                match_ec={"match_comment": "some test comment"},
            ),
            {
                "EC_ID": "test12",
                "EC_COMMENT": "some other comment",
            },
            "The event comment 'some other comment' does not match the regular expression 'some test comment'",
            id="No match on Event Console comment",
        ),
    ],
)
def test_rbn_match_event_console(
    event_rule: EventRule,
    context: EventContext,
    expected: str | None,
) -> None:
    assert (
        notify.rbn_match_event_console(
            rule=event_rule,
            context=context,
            _analyse=False,
            _all_timeperiods={},
        )
        == expected
    )
