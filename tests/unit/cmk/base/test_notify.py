#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
import os
import shlex
import time
import uuid
from collections.abc import Callable, Iterator, Mapping
from pathlib import Path
from typing import cast, Final, Literal, override
from unittest.mock import Mock

import pytest
from pytest import MonkeyPatch

import cmk.utils.paths
from cmk.base import notify
from cmk.ccc import store
from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.hostaddress import HostAddress
from cmk.ccc.version import Edition
from cmk.events.event_context import EnrichedEventContext, EventContext, HostName
from cmk.events.notification_result import NotificationContext
from cmk.events.notify_types import (
    AlwaysBulkParameters,
    Contact,
    ContactName,
    CustomPluginName,
    EventRule,
    NotificationParameterGeneralInfos,
    NotificationParameterID,
    NotificationParameterSpecs,
    NotificationRuleID,
    NotifyAnalysisInfo,
    NotifyBulkParameters,
    NotifyBulkType,
    NotifyPluginParamsDict,
    SyslogPriorityIntType,
    TimeperiodBulkParameters,
)
from cmk.livestatus_client import MKLivestatusException
from cmk.ruleset_matcher.labels import LabelManager
from cmk.ruleset_matcher.matcher import RulesetMatcher
from cmk.utils import log
from cmk.utils.http_proxy_config import EnvironmentProxyConfig

HTTP_PROXY: Final = EnvironmentProxyConfig()


def _environment_proxy(_proxy_spec: object) -> EnvironmentProxyConfig:
    return HTTP_PROXY


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
            _environment_proxy,
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


def _with_legacy_match_ec_none(rule: EventRule) -> EventRule:
    return cast(EventRule, dict(rule, match_ec=None))


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
            None,
            id="Match all events, notification from Event Console",
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
            None,
            id="Matching all events, notification from Event Console",
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
            id="Matching on all events, no notification from Event Console",
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
            id="Match on Event console alerts, no match on Event Console rule ID",
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
            id="Match on Event console alerts, match on Event Console syslog priority",
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
            id="Match on Even Console alerts, no match on Event Console syslog priority",
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
            id="Match on Even Console alerts , match on Event Console syslog facility",
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
        pytest.param(
            EventRule(
                rule_id=NotificationRuleID("13"),
                allow_disable=False,
                contact_all=False,
                contact_all_with_email=False,
                contact_object=False,
                description="Test rule 13",
                disabled=False,
                notify_plugin=("mail", None),
                match_service_event=["?c", "?w", "?r"],
            ),
            {
                "EC_ID": "test13",
                "EC_COMMENT": "some other comment",
            },
            "Notification has been created by the Event Console.",
            id="No match on Event Console alerts, only on service alerts",
        ),
        pytest.param(
            EventRule(
                rule_id=NotificationRuleID("14"),
                allow_disable=False,
                contact_all=False,
                contact_all_with_email=False,
                contact_object=False,
                description="Test rule 14",
                disabled=False,
                notify_plugin=("mail", None),
                match_host_event=["?d", "?r"],
            ),
            {
                "EC_ID": "test14",
                "EC_COMMENT": "some other comment",
            },
            "Notification has been created by the Event Console.",
            id="No match on Event Console alerts, only on host alerts",
        ),
        pytest.param(
            EventRule(
                rule_id=NotificationRuleID("15"),
                allow_disable=False,
                contact_all=False,
                contact_all_with_email=False,
                contact_object=False,
                description="Test rule 15",
                disabled=False,
                notify_plugin=("mail", None),
                match_host_event=["?d", "?r"],
                match_service_event=["?c", "?w", "?r"],
                match_ec={"match_facility": 3},
            ),
            {
                "EC_ID": "test15",
                "EC_FACILITY": "3",
            },
            None,
            id="Match on all events (all checked, not via All events), match on Event Console alert",
        ),
        pytest.param(
            EventRule(
                rule_id=NotificationRuleID("15"),
                allow_disable=False,
                contact_all=False,
                contact_all_with_email=False,
                contact_object=False,
                description="Test rule 15",
                disabled=False,
                notify_plugin=("mail", None),
                match_host_event=["?d", "?r"],
                match_service_event=["?c", "?w", "?r"],
                match_ec={"match_facility": 3},
            ),
            {
                "EC_ID": "test15",
                "EC_FACILITY": "0",
            },
            "Wrong syslog facility 0, required is 3",
            id="Match on all events (all checked, not via All events), no match on Event Console alert filter",
        ),
        pytest.param(
            EventRule(
                rule_id=NotificationRuleID("16"),
                allow_disable=False,
                contact_all=False,
                contact_all_with_email=False,
                contact_object=False,
                description="Test rule 15",
                disabled=False,
                notify_plugin=("mail", None),
                match_service_event=["?c", "?w", "?r"],
                match_ec={},
            ),
            {
                "SERVICESTATE": "w",
                "PREVIOUSSERVICEHARDSTATE": "r",
            },
            None,
            id="Match on service events and all event console alerts",
        ),
        pytest.param(
            EventRule(
                rule_id=NotificationRuleID("17"),
                allow_disable=False,
                contact_all=False,
                contact_all_with_email=False,
                contact_object=False,
                description="Test rule 15",
                disabled=False,
                notify_plugin=("mail", None),
                match_service_event=["?c", "?w", "?r"],
                match_ec={"match_comment": "some test comment"},
            ),
            {
                "SERVICESTATE": "w",
                "PREVIOUSSERVICEHARDSTATE": "r",
            },
            "Notification has not been created by the Event Console.",
            id="Match on service events and event console alerts with filter",
        ),
        pytest.param(
            EventRule(
                rule_id=NotificationRuleID("18"),
                allow_disable=False,
                contact_all=False,
                contact_all_with_email=False,
                contact_object=False,
                description="Test rule 18",
                disabled=False,
                notify_plugin=("mail", None),
                match_ec=False,
            ),
            {
                "EC_ID": "test18",
            },
            "Notification has been created by the Event Console.",
            id="Do not match Event Console alerts, notification from Event Console",
        ),
        pytest.param(
            EventRule(
                rule_id=NotificationRuleID("19"),
                allow_disable=False,
                contact_all=False,
                contact_all_with_email=False,
                contact_object=False,
                description="Test rule 19",
                disabled=False,
                notify_plugin=("mail", None),
                match_ec=False,
            ),
            {
                "PARAMETER_FROM_ADDRESS": "from@lala.com",
            },
            None,
            id="Do not match Event Console alerts, no notification from Event Console",
        ),
        pytest.param(
            EventRule(
                rule_id=NotificationRuleID("20"),
                allow_disable=False,
                contact_all=False,
                contact_all_with_email=False,
                contact_object=False,
                description="Test rule 20",
                disabled=False,
                notify_plugin=("mail", None),
                match_host_event=["?d", "?r"],
                match_service_event=["?c", "?w", "?r"],
                match_ec=False,
            ),
            {
                "EC_ID": "test20",
            },
            "Notification has been created by the Event Console.",
            id="Do not match Event Console alerts alongside host and service events, notification from Event Console",
        ),
        pytest.param(
            EventRule(
                rule_id=NotificationRuleID("21"),
                allow_disable=False,
                contact_all=False,
                contact_all_with_email=False,
                contact_object=False,
                description="Test rule 21",
                disabled=False,
                notify_plugin=("mail", None),
                match_service_event=["?c", "?w", "?r"],
                match_ec=False,
            ),
            {
                "SERVICESTATE": "w",
                "PREVIOUSSERVICEHARDSTATE": "r",
            },
            None,
            id="Do not match Event Console alerts alongside service events, service notification",
        ),
        pytest.param(
            _with_legacy_match_ec_none(
                EventRule(
                    rule_id=NotificationRuleID("22"),
                    allow_disable=False,
                    contact_all=False,
                    contact_all_with_email=False,
                    contact_object=False,
                    description="Test rule 22",
                    disabled=False,
                    notify_plugin=("mail", None),
                )
            ),
            {
                "EC_ID": "test22",
            },
            None,
            id="No Event Console condition configured, notification from Event Console",
        ),
        pytest.param(
            _with_legacy_match_ec_none(
                EventRule(
                    rule_id=NotificationRuleID("23"),
                    allow_disable=False,
                    contact_all=False,
                    contact_all_with_email=False,
                    contact_object=False,
                    description="Test rule 23",
                    disabled=False,
                    notify_plugin=("mail", None),
                    match_host_event=["?d", "?r"],
                )
            ),
            {
                "EC_ID": "test23",
            },
            "Notification has been created by the Event Console.",
            id="No Event Console condition configured alongside host events, notification from Event Console",
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


def _make_rule() -> EventRule:
    return {
        "rule_id": NotificationRuleID("test"),
        "allow_disable": False,
        "contact_all": False,
        "contact_all_with_email": False,
        "contact_object": False,
        "description": "Test rule",
        "disabled": False,
        "notify_plugin": ("mail", None),
    }


@pytest.mark.parametrize(
    "rule, expected",
    [
        pytest.param(_make_rule(), None, id="no disabled key → passes"),
        pytest.param(_make_rule() | {"disabled": False}, None, id="disabled=False → passes"),
        pytest.param(
            _make_rule() | {"disabled": True}, "This rule is disabled", id="disabled=True → blocked"
        ),
    ],
)
def test_rbn_match_rule_disabled(rule: EventRule, expected: str | None) -> None:
    assert notify.rbn_match_rule_disabled(rule, {}, False, {}) == expected


@pytest.mark.parametrize(
    "rule, context, expected",
    [
        pytest.param(_make_rule(), {"WHAT": "HOST"}, None, id="no match_escalation → passes"),
        pytest.param(
            _make_rule() | {"match_escalation": (1, 5)},
            {"WHAT": "HOST", "HOSTNOTIFICATIONNUMBER": "3"},
            None,
            id="HOST number in range → passes",
        ),
        pytest.param(
            _make_rule() | {"match_escalation": (1, 5)},
            {"WHAT": "HOST", "HOSTNOTIFICATIONNUMBER": "6"},
            "The notification number 6 does not lie in range 1 ... 5",
            id="HOST number out of range → blocked",
        ),
        pytest.param(
            _make_rule() | {"match_escalation": (1, 5)},
            {"WHAT": "SERVICE", "SERVICENOTIFICATIONNUMBER": "3"},
            None,
            id="SERVICE number in range → passes",
        ),
        pytest.param(
            _make_rule() | {"match_escalation": (1, 5)},
            {"WHAT": "SERVICE", "SERVICENOTIFICATIONNUMBER": "7"},
            "The notification number 7 does not lie in range 1 ... 5",
            id="SERVICE number out of range → blocked",
        ),
        pytest.param(
            _make_rule() | {"match_escalation": (1, 5)},
            {"WHAT": "HOST"},
            None,
            id="HOST with no HOSTNOTIFICATIONNUMBER defaults to 1 → passes",
        ),
    ],
)
def test_rbn_match_escalation(rule: EventRule, context: EventContext, expected: str | None) -> None:
    assert notify.rbn_match_escalation(rule, context, False, {}) == expected


@pytest.mark.parametrize(
    "rule, context, expected",
    [
        pytest.param(
            _make_rule(), {"WHAT": "HOST"}, None, id="no match_escalation_throttle → passes"
        ),
        pytest.param(
            _make_rule() | {"match_escalation_throttle": (10, 5)},
            {"WHAT": "HOST", "HOSTSTATE": "UP", "HOSTNOTIFICATIONNUMBER": "15"},
            None,
            id="HOST recovery (UP) → never throttled",
        ),
        pytest.param(
            _make_rule() | {"match_escalation_throttle": (10, 5)},
            {"WHAT": "SERVICE", "SERVICESTATE": "OK", "SERVICENOTIFICATIONNUMBER": "15"},
            None,
            id="SERVICE recovery (OK) → never throttled",
        ),
        pytest.param(
            _make_rule() | {"match_escalation_throttle": (10, 5)},
            {"WHAT": "HOST", "HOSTSTATE": "DOWN", "HOSTNOTIFICATIONNUMBER": "10"},
            None,
            id="HOST at from_number boundary → passes",
        ),
        pytest.param(
            _make_rule() | {"match_escalation_throttle": (10, 5)},
            {"WHAT": "HOST", "HOSTSTATE": "DOWN", "HOSTNOTIFICATIONNUMBER": "15"},
            None,
            id="HOST at from_number + rate → passes",
        ),
        pytest.param(
            _make_rule() | {"match_escalation_throttle": (10, 5)},
            {"WHAT": "HOST", "HOSTSTATE": "DOWN", "HOSTNOTIFICATIONNUMBER": "12"},
            "This notification is being skipped due to throttling. The next number will be 15",
            id="HOST notification throttled → blocked",
        ),
        pytest.param(
            _make_rule() | {"match_escalation_throttle": (10, 5)},
            {"WHAT": "SERVICE", "SERVICESTATE": "CRITICAL", "SERVICENOTIFICATIONNUMBER": "13"},
            "This notification is being skipped due to throttling. The next number will be 15",
            id="SERVICE notification throttled → blocked",
        ),
    ],
)
def test_rbn_match_escalation_throttle(
    rule: EventRule, context: EventContext, expected: str | None
) -> None:
    assert notify.rbn_match_escalation_throttle(rule, context, False, {}) == expected


@pytest.mark.parametrize(
    "rule, context, expected",
    [
        pytest.param(_make_rule(), {"WHAT": "HOST"}, None, id="no match_host_event → passes"),
        pytest.param(
            _make_rule() | {"match_host_event": ["dr"]},
            {
                "WHAT": "SERVICE",
                "NOTIFICATIONTYPE": "PROBLEM",
                "SERVICESTATE": "CRITICAL",
                "PREVIOUSSERVICEHARDSTATE": "OK",
            },
            "This is a service notification, but the rule just matches host events",
            id="SERVICE notification, rule only matches HOST → blocked",
        ),
        pytest.param(
            _make_rule() | {"match_host_event": ["dr"], "match_service_event": ["?c"]},
            {
                "WHAT": "SERVICE",
                "NOTIFICATIONTYPE": "PROBLEM",
                "SERVICESTATE": "CRITICAL",
                "PREVIOUSSERVICEHARDSTATE": "OK",
            },
            None,
            id="SERVICE notification, rule matches both → passes (delegated to service event)",
        ),
        pytest.param(
            _make_rule() | {"match_host_event": ["dr"]},
            {"WHAT": "SERVICE", "EC_ID": "ec1", "NOTIFICATIONTYPE": "PROBLEM"},
            None,
            id="EC notification, rule matches HOST → passes (handled by EC matcher)",
        ),
        pytest.param(
            _make_rule() | {"match_host_event": ["dr"]},
            {
                "WHAT": "HOST",
                "NOTIFICATIONTYPE": "RECOVERY",
                "HOSTSTATE": "UP",
                "PREVIOUSHOSTHARDSTATE": "DOWN",
            },
            None,
            id="HOST recovery DOWN→UP with 'dr' allowed → passes",
        ),
        pytest.param(
            _make_rule() | {"match_host_event": ["dr"]},
            {
                "WHAT": "HOST",
                "NOTIFICATIONTYPE": "RECOVERY",
                "HOSTSTATE": "UP",
                "PREVIOUSHOSTHARDSTATE": "UNREACHABLE",
            },
            "Event type 'ur' not handled by this rule. Allowed are: dr",
            id="HOST recovery UNREACHABLE→UP, only 'dr' allowed → blocked",
        ),
    ],
)
def test_rbn_match_host_event(rule: EventRule, context: EventContext, expected: str | None) -> None:
    assert notify.rbn_match_host_event(rule, context, False, {}) == expected


@pytest.mark.parametrize(
    "rule, context, expected",
    [
        pytest.param(_make_rule(), {"WHAT": "SERVICE"}, None, id="no match_service_event → passes"),
        pytest.param(
            _make_rule() | {"match_service_event": ["?c"]},
            {
                "WHAT": "HOST",
                "NOTIFICATIONTYPE": "PROBLEM",
                "HOSTSTATE": "DOWN",
                "PREVIOUSHOSTHARDSTATE": "UP",
            },
            "This is a host notification, but the rule just matches service events",
            id="HOST notification, rule only matches SERVICE → blocked",
        ),
        pytest.param(
            _make_rule() | {"match_service_event": ["?c"], "match_host_event": ["dr"]},
            {
                "WHAT": "HOST",
                "NOTIFICATIONTYPE": "PROBLEM",
                "HOSTSTATE": "DOWN",
                "PREVIOUSHOSTHARDSTATE": "UP",
            },
            None,
            id="HOST notification, rule matches both → passes (delegated to host event)",
        ),
        pytest.param(
            _make_rule() | {"match_service_event": ["?c"]},
            {
                "WHAT": "SERVICE",
                "NOTIFICATIONTYPE": "PROBLEM",
                "SERVICESTATE": "CRITICAL",
                "PREVIOUSSERVICEHARDSTATE": "OK",
            },
            None,
            id="SERVICE critical with '?c' allowed → passes",
        ),
        pytest.param(
            _make_rule() | {"match_service_event": ["?c"]},
            {
                "WHAT": "SERVICE",
                "NOTIFICATIONTYPE": "PROBLEM",
                "SERVICESTATE": "WARNING",
                "PREVIOUSSERVICEHARDSTATE": "OK",
            },
            "Event type 'rw' not handled by this rule. Allowed are: ?c",
            id="SERVICE warning, only '?c' allowed → blocked",
        ),
    ],
)
def test_rbn_match_service_event(
    rule: EventRule, context: EventContext, expected: str | None
) -> None:
    assert notify.rbn_match_service_event(rule, context, False, {}) == expected


@pytest.mark.parametrize(
    "rule, context, expected",
    [
        pytest.param(_make_rule(), {}, None, id="no match_notification_comment → passes"),
        pytest.param(
            _make_rule() | {"match_notification_comment": "^maintenance"},
            {"NOTIFICATIONCOMMENT": "maintenance window start"},
            None,
            id="comment matches regex → passes",
        ),
        pytest.param(
            _make_rule() | {"match_notification_comment": "^maintenance"},
            {"NOTIFICATIONCOMMENT": "urgent alert"},
            "The beginning of the notification comment 'urgent alert' is not matched by the regex '^maintenance'",
            id="comment does not match regex → blocked",
        ),
        pytest.param(
            _make_rule() | {"match_notification_comment": "^maintenance"},
            {},
            "The beginning of the notification comment '' is not matched by the regex '^maintenance'",
            id="no NOTIFICATIONCOMMENT in context (empty string) → blocked",
        ),
    ],
)
def test_rbn_match_notification_comment(
    rule: EventRule, context: EventContext, expected: str | None
) -> None:
    assert notify.rbn_match_notification_comment(rule, context, False, {}) == expected


@pytest.mark.parametrize(
    "rule, context, analyse, is_active, expected",
    [
        pytest.param(_make_rule(), {}, False, True, None, id="analyse=False → always passes"),
        pytest.param(
            _make_rule(),
            {"MICROTIME": "1234567890000000"},
            True,
            True,
            None,
            id="no match_timeperiod → passes",
        ),
        pytest.param(
            _make_rule() | {"match_timeperiod": "24X7"},
            {"MICROTIME": "1234567890000000"},
            True,
            True,
            None,
            id="24X7 timeperiod → always passes",
        ),
        pytest.param(
            _make_rule() | {"match_timeperiod": "work_hours"},
            {"MICROTIME": "1234567890000000"},
            True,
            True,
            None,
            id="timeperiod active → passes",
        ),
        pytest.param(
            _make_rule() | {"match_timeperiod": "work_hours"},
            {"MICROTIME": "1234567890000000"},
            True,
            False,
            "The notification does not match the timeperiod 'work_hours'",
            id="timeperiod not active → blocked",
        ),
    ],
)
def test_rbn_match_timeperiod(
    rule: EventRule,
    context: EventContext,
    analyse: bool,
    is_active: bool,
    expected: str | None,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setattr(notify, "is_timeperiod_active", lambda **kwargs: is_active)  # noqa: ARG005
    assert notify.rbn_match_timeperiod(rule, context, analyse, {}) == expected


@pytest.mark.parametrize(
    "rule, contactname, contact, expected",
    [
        pytest.param(
            _make_rule(), "user1", Contact({}), None, id="no contact_match_macros → passes"
        ),
        pytest.param(
            _make_rule() | {"contact_match_macros": [("alias", "ops")]},
            "user1",
            Contact({"_alias": "ops"}),  # type: ignore[typeddict-unknown-key]
            None,
            id="macro value matches regex → passes",
        ),
        pytest.param(
            _make_rule() | {"contact_match_macros": [("alias", "ops")]},
            "user1",
            Contact({"_alias": "dev"}),  # type: ignore[typeddict-unknown-key]
            "value 'dev' for macro 'alias' does not match 'ops$'. His macros are: alias=dev",
            id="macro value does not match regex → blocked",
        ),
        pytest.param(
            _make_rule() | {"contact_match_macros": [("alias", "ops")]},
            "user1",
            Contact({}),
            "value '' for macro 'alias' does not match 'ops$'. His macros are: ",
            id="macro absent (empty string) → blocked",
        ),
    ],
)
def test__rbn_match_contact_macros(
    rule: EventRule,
    contactname: str,
    contact: Contact,
    expected: str | None,
) -> None:
    assert notify._rbn_match_contact_macros(rule, contactname, contact) == expected  # noqa: SLF001


@pytest.mark.parametrize(
    "rule, contactname, contact, expected",
    [
        pytest.param(
            _make_rule(), "user1", Contact({}), None, id="no contact_match_groups → passes"
        ),
        pytest.param(
            _make_rule() | {"contact_match_groups": ["ops"]},
            "user1",
            Contact({"contactgroups": ["ops", "all"]}),
            None,
            id="contact in required group → passes",
        ),
        pytest.param(
            _make_rule() | {"contact_match_groups": ["ops"]},
            "user1",
            Contact({"contactgroups": ["dev", "all"]}),
            "he/she is not member of the contact group ops (his groups are dev, all)",
            id="contact not in required group → blocked",
        ),
        pytest.param(
            _make_rule() | {"contact_match_groups": ["ops"]},
            "user1",
            Contact({}),
            None,
            id="contact has no contactgroups → passes (warning logged, no restriction applied)",
        ),
    ],
)
def test__rbn_match_contact_groups(
    rule: EventRule,
    contactname: str,
    contact: Contact,
    expected: str | None,
) -> None:
    assert notify._rbn_match_contact_groups(rule, contactname, contact) == expected  # noqa: SLF001


def test__rbn_match_rule_disabled_rule() -> None:
    assert (
        notify._rbn_match_rule(  # noqa: SLF001
            _make_rule() | {"disabled": True},
            EnrichedEventContext({}),
            {},
            define_servicegroups={},
            analyse=False,
            timeperiods_active={},
        )
        == "This rule is disabled"
    )


def test__rbn_match_rule_passes_minimal() -> None:
    # WHAT and HOSTNAME are required because event_match_rule always accesses these:
    # - context["WHAT"] via _event_match_servicegroups (unconditionally)
    # - context["HOSTNAME"] via event_match_exclude_hosts (unconditionally)
    assert (
        notify._rbn_match_rule(  # noqa: SLF001
            _make_rule(),
            EnrichedEventContext({"WHAT": "HOST", "HOSTNAME": HostName("testhost")}),
            {},
            define_servicegroups={},
            analyse=False,
            timeperiods_active={},
        )
        is None
    )


def test__rbn_match_rule_do_not_match_ec_alerts_passes_host_notification() -> None:
    assert (
        notify._rbn_match_rule(  # noqa: SLF001
            _make_rule() | {"match_ec": False},
            EnrichedEventContext({"WHAT": "HOST", "HOSTNAME": HostName("testhost")}),
            {},
            define_servicegroups={},
            analyse=False,
            timeperiods_active={},
        )
        is None
    )


def test__rbn_match_rule_do_not_match_ec_alerts_blocks_ec_alert() -> None:
    assert (
        notify._rbn_match_rule(  # noqa: SLF001
            _make_rule() | {"match_ec": False},
            EnrichedEventContext({"WHAT": "HOST", "HOSTNAME": HostName("testhost"), "EC_ID": "42"}),
            {},
            define_servicegroups={},
            analyse=False,
            timeperiods_active={},
        )
        == "Notification has been created by the Event Console."
    )


def test_create_notifications_custom_script_with_call_parameters() -> None:
    """Regression test custom notification scripts with
    'Call with the following parameters'"""
    # In user notification rules with custom scripts and "Call with the following
    # parameters", the plugin_parameter_id is a list of strings, not a
    # NotificationParameterID string. This bypasses the normal typed parameter path.
    rule = _make_rule()
    rule["notify_plugin"] = ("my_custom_script", ["param1", "param2"])  # type: ignore[typeddict-item]
    rule["contact_users"] = ["testuser"]
    config_contacts = {
        ContactName("testuser"): Contact({"email": "test@example.com"}),
    }
    notifications, _rule_info = notify._create_notifications(  # noqa: SLF001
        enriched_context=EnrichedEventContext({"HOSTNAME": HostName("testhost"), "WHAT": "HOST"}),
        rule=rule,
        parameters={},
        notifications=[],
        rule_info=[],
        host_parameters_cb=lambda _host, _plugin: {},
        config_contacts=config_contacts,
        fallback_email="",
        rule_nr=0,
        timeperiods_active={},
    )
    # Should create exactly one notification without raising ValueError
    assert len(notifications) == 1
    assert notifications[0].parameters["params"] == ["param1", "param2"]  # type: ignore[typeddict-item]


def _count_contact_occurrences(notifications: notify.Notifications, contact: ContactName) -> int:
    """Count how many notification entries contain a given contact."""
    return sum(1 for entry in notifications if contact in entry.contacts)


_TEST_PLUGIN = CustomPluginName("my_script")
_TEST_PARAM_ID = NotificationParameterID("test_params")
_TEST_GENERAL = NotificationParameterGeneralInfos(description="test", comment="", docu_url="")
_TEST_PARAMETERS: NotificationParameterSpecs = {
    _TEST_PLUGIN: {
        _TEST_PARAM_ID: {
            "general": _TEST_GENERAL,
            "parameter_properties": {},
        }
    }
}


def _make_add_rule(
    *,
    contact_users: list[str],
    plugin: CustomPluginName = _TEST_PLUGIN,
    param_id: NotificationParameterID = _TEST_PARAM_ID,
    allow_disable: bool = True,
    contact: str | None = None,
) -> EventRule:
    """Create a notification rule for adding notifications using proper types."""
    rule = _make_rule()
    rule["notify_plugin"] = (plugin, param_id)
    rule["contact_users"] = contact_users
    rule["allow_disable"] = allow_disable
    if contact is not None:
        rule["contact"] = contact
    return rule


def _make_cancel_rule(
    *,
    contact_users: list[str],
    plugin: CustomPluginName = _TEST_PLUGIN,
    contact: str | None = None,
) -> EventRule:
    """Create a notification rule for cancelling notifications."""
    rule = _make_rule()
    rule["notify_plugin"] = (plugin, None)
    rule["contact_users"] = contact_users
    if contact is not None:
        rule["contact"] = contact
    return rule


def test_cancellation_removes_contacts() -> None:
    """A cancel rule removes contacts from an existing notification entry."""
    config_contacts = {
        ContactName("userX"): Contact({"email": "x@example.com"}),
        ContactName("userY"): Contact({"email": "y@example.com"}),
    }
    enriched_context = EnrichedEventContext({"HOSTNAME": HostName("testhost"), "WHAT": "HOST"})

    notifications, rule_info = notify._create_notifications(  # noqa: SLF001
        enriched_context=enriched_context,
        rule=_make_add_rule(contact_users=["userX", "userY"]),
        parameters=_TEST_PARAMETERS,
        notifications=[],
        rule_info=[],
        host_parameters_cb=lambda _host, _plugin: {},
        config_contacts=config_contacts,
        fallback_email="",
        rule_nr=0,
        timeperiods_active={},
    )
    assert len(notifications) == 1

    notifications, rule_info = notify._create_notifications(  # noqa: SLF001
        enriched_context=enriched_context,
        rule=_make_cancel_rule(contact_users=["userX"]),
        parameters=_TEST_PARAMETERS,
        notifications=notifications,
        rule_info=rule_info,
        host_parameters_cb=lambda _host, _plugin: {},
        config_contacts=config_contacts,
        fallback_email="",
        rule_nr=1,
        timeperiods_active={},
    )

    assert len(notifications) == 1
    assert _count_contact_occurrences(notifications, ContactName("userX")) == 0
    assert _count_contact_occurrences(notifications, ContactName("userY")) == 1


def test_cancellation_of_all_contacts_removes_entry() -> None:
    """Cancelling all contacts removes the notification entry entirely."""
    config_contacts = {
        ContactName("userX"): Contact({"email": "x@example.com"}),
    }
    enriched_context = EnrichedEventContext({"HOSTNAME": HostName("testhost"), "WHAT": "HOST"})

    notifications, rule_info = notify._create_notifications(  # noqa: SLF001
        enriched_context=enriched_context,
        rule=_make_add_rule(contact_users=["userX"]),
        parameters=_TEST_PARAMETERS,
        notifications=[],
        rule_info=[],
        host_parameters_cb=lambda _host, _plugin: {},
        config_contacts=config_contacts,
        fallback_email="",
        rule_nr=0,
        timeperiods_active={},
    )
    assert len(notifications) == 1

    notifications, rule_info = notify._create_notifications(  # noqa: SLF001
        enriched_context=enriched_context,
        rule=_make_cancel_rule(contact_users=["userX"]),
        parameters=_TEST_PARAMETERS,
        notifications=notifications,
        rule_info=rule_info,
        host_parameters_cb=lambda _host, _plugin: {},
        config_contacts=config_contacts,
        fallback_email="",
        rule_nr=1,
        timeperiods_active={},
    )

    assert len(notifications) == 0


def test_locked_notification_cannot_be_cancelled_by_user_rule() -> None:
    """A user rule cannot cancel a locked notification from a global rule."""
    config_contacts = {
        ContactName("userX"): Contact({"email": "x@example.com"}),
    }
    enriched_context = EnrichedEventContext({"HOSTNAME": HostName("testhost"), "WHAT": "HOST"})

    notifications, rule_info = notify._create_notifications(  # noqa: SLF001
        enriched_context=enriched_context,
        rule=_make_add_rule(allow_disable=False, contact_users=["userX"]),
        parameters=_TEST_PARAMETERS,
        notifications=[],
        rule_info=[],
        host_parameters_cb=lambda _host, _plugin: {},
        config_contacts=config_contacts,
        fallback_email="",
        rule_nr=0,
        timeperiods_active={},
    )
    assert len(notifications) == 1

    notifications, rule_info = notify._create_notifications(  # noqa: SLF001
        enriched_context=enriched_context,
        rule=_make_cancel_rule(contact="userX", contact_users=["userX"]),
        parameters=_TEST_PARAMETERS,
        notifications=notifications,
        rule_info=rule_info,
        host_parameters_cb=lambda _host, _plugin: {},
        config_contacts=config_contacts,
        fallback_email="",
        rule_nr=1,
        timeperiods_active={},
    )

    assert len(notifications) == 1
    assert _count_contact_occurrences(notifications, ContactName("userX")) == 1


def test_different_plugins_create_separate_entries() -> None:
    """Same contacts with different plugins should create separate entries."""
    config_contacts = {
        ContactName("userX"): Contact({"email": "x@example.com"}),
    }
    enriched_context = EnrichedEventContext({"HOSTNAME": HostName("testhost"), "WHAT": "HOST"})
    plugin_a = CustomPluginName("plugin_a")
    plugin_b = CustomPluginName("plugin_b")
    parameters: NotificationParameterSpecs = {
        plugin_a: {_TEST_PARAM_ID: {"general": _TEST_GENERAL, "parameter_properties": {}}},
        plugin_b: {_TEST_PARAM_ID: {"general": _TEST_GENERAL, "parameter_properties": {}}},
    }

    notifications, rule_info = notify._create_notifications(  # noqa: SLF001
        enriched_context=enriched_context,
        rule=_make_add_rule(contact_users=["userX"], plugin=plugin_a),
        parameters=parameters,
        notifications=[],
        rule_info=[],
        host_parameters_cb=lambda _host, _plugin: {},
        config_contacts=config_contacts,
        fallback_email="",
        rule_nr=0,
        timeperiods_active={},
    )
    notifications, rule_info = notify._create_notifications(  # noqa: SLF001
        enriched_context=enriched_context,
        rule=_make_add_rule(contact_users=["userX"], plugin=plugin_b),
        parameters=parameters,
        notifications=notifications,
        rule_info=rule_info,
        host_parameters_cb=lambda _host, _plugin: {},
        config_contacts=config_contacts,
        fallback_email="",
        rule_nr=1,
        timeperiods_active={},
    )

    assert len(notifications) == 2


def test_no_duplicate_notifications_for_overlapping_contacts() -> None:
    """User X is in two contact groups. Two rules target these groups with the
    same plugin and params. X should get exactly one notification."""
    config_contacts = {
        ContactName("userX"): Contact({"email": "x@example.com"}),
        ContactName("userY"): Contact({"email": "y@example.com"}),
        ContactName("userZ"): Contact({"email": "z@example.com"}),
    }
    enriched_context = EnrichedEventContext({"HOSTNAME": HostName("testhost"), "WHAT": "HOST"})

    notifications, rule_info = notify._create_notifications(  # noqa: SLF001
        enriched_context=enriched_context,
        rule=_make_add_rule(contact_users=["userX", "userY"]),
        parameters=_TEST_PARAMETERS,
        notifications=[],
        rule_info=[],
        host_parameters_cb=lambda _host, _plugin: {},
        config_contacts=config_contacts,
        fallback_email="",
        rule_nr=0,
        timeperiods_active={},
    )
    notifications, rule_info = notify._create_notifications(  # noqa: SLF001
        enriched_context=enriched_context,
        rule=_make_add_rule(contact_users=["userX", "userZ"]),
        parameters=_TEST_PARAMETERS,
        notifications=notifications,
        rule_info=rule_info,
        host_parameters_cb=lambda _host, _plugin: {},
        config_contacts=config_contacts,
        fallback_email="",
        rule_nr=1,
        timeperiods_active={},
    )

    assert len(notifications) == 1
    assert _count_contact_occurrences(notifications, ContactName("userX")) == 1


def test_no_parameter_overwrite_for_same_contacts_and_plugin() -> None:
    """Two rules for the same contacts and plugin but different params.
    Both notifications should be preserved."""
    config_contacts = {
        ContactName("userX"): Contact({"email": "x@example.com"}),
    }
    enriched_context = EnrichedEventContext({"HOSTNAME": HostName("testhost"), "WHAT": "HOST"})
    param_alpha = NotificationParameterID("alpha")
    param_beta = NotificationParameterID("beta")
    parameters: NotificationParameterSpecs = {
        _TEST_PLUGIN: {
            param_alpha: {
                "general": _TEST_GENERAL,
                "parameter_properties": {"mode": "alpha"},
            },
            param_beta: {
                "general": _TEST_GENERAL,
                "parameter_properties": {"mode": "beta"},
            },
        }
    }

    notifications, rule_info = notify._create_notifications(  # noqa: SLF001
        enriched_context=enriched_context,
        rule=_make_add_rule(contact_users=["userX"], param_id=param_alpha),
        parameters=parameters,
        notifications=[],
        rule_info=[],
        host_parameters_cb=lambda _host, _plugin: {},
        config_contacts=config_contacts,
        fallback_email="",
        rule_nr=0,
        timeperiods_active={},
    )
    notifications, rule_info = notify._create_notifications(  # noqa: SLF001
        enriched_context=enriched_context,
        rule=_make_add_rule(contact_users=["userX"], param_id=param_beta),
        parameters=parameters,
        notifications=notifications,
        rule_info=rule_info,
        host_parameters_cb=lambda _host, _plugin: {},
        config_contacts=config_contacts,
        fallback_email="",
        rule_nr=1,
        timeperiods_active={},
    )

    assert len(notifications) == 2


def test_no_duplicate_bulk_notifications_for_overlapping_contacts() -> None:
    """Same as contact dedup test but with bulk enabled.
    Contact X should appear in exactly one bulk notification entry."""
    config_contacts = {
        ContactName("userX"): Contact({"email": "x@example.com"}),
        ContactName("userY"): Contact({"email": "y@example.com"}),
        ContactName("userZ"): Contact({"email": "z@example.com"}),
    }
    enriched_context = EnrichedEventContext({"HOSTNAME": HostName("testhost"), "WHAT": "HOST"})

    bulk_params = AlwaysBulkParameters(interval=60, count=10, groupby=[])
    bulk_rule = _make_add_rule(contact_users=["userX", "userY"])
    bulk_rule["bulk"] = ("always", bulk_params)
    notifications, rule_info = notify._create_notifications(  # noqa: SLF001
        enriched_context=enriched_context,
        rule=bulk_rule,
        parameters=_TEST_PARAMETERS,
        notifications=[],
        rule_info=[],
        host_parameters_cb=lambda _host, _plugin: {},
        config_contacts=config_contacts,
        fallback_email="",
        rule_nr=0,
        timeperiods_active={"24X7": True},
    )

    bulk_rule2 = _make_add_rule(contact_users=["userX", "userZ"])
    bulk_rule2["bulk"] = ("always", bulk_params)
    notifications, rule_info = notify._create_notifications(  # noqa: SLF001
        enriched_context=enriched_context,
        rule=bulk_rule2,
        parameters=_TEST_PARAMETERS,
        notifications=notifications,
        rule_info=rule_info,
        host_parameters_cb=lambda _host, _plugin: {},
        config_contacts=config_contacts,
        fallback_email="",
        rule_nr=1,
        timeperiods_active={"24X7": True},
    )

    assert _count_contact_occurrences(notifications, ContactName("userX")) == 1


def test_identical_rules_merge_contacts() -> None:
    """Two separate rules with identical config should merge their contacts."""
    config_contacts = {
        ContactName("userX"): Contact({"email": "x@example.com"}),
        ContactName("userY"): Contact({"email": "y@example.com"}),
    }
    enriched_context = EnrichedEventContext({"HOSTNAME": HostName("testhost"), "WHAT": "HOST"})

    notifications, rule_info = notify._create_notifications(  # noqa: SLF001
        enriched_context=enriched_context,
        rule=_make_add_rule(contact_users=["userX"]),
        parameters=_TEST_PARAMETERS,
        notifications=[],
        rule_info=[],
        host_parameters_cb=lambda _host, _plugin: {},
        config_contacts=config_contacts,
        fallback_email="",
        rule_nr=0,
        timeperiods_active={},
    )
    notifications, rule_info = notify._create_notifications(  # noqa: SLF001
        enriched_context=enriched_context,
        rule=_make_add_rule(contact_users=["userY"]),
        parameters=_TEST_PARAMETERS,
        notifications=notifications,
        rule_info=rule_info,
        host_parameters_cb=lambda _host, _plugin: {},
        config_contacts=config_contacts,
        fallback_email="",
        rule_nr=1,
        timeperiods_active={},
    )

    assert len(notifications) == 1
    assert notifications[0].contacts == {ContactName("userX"), ContactName("userY")}


def test_identical_rules_same_contact_no_duplicate() -> None:
    """Two rules with identical config targeting the same contact
    should result in exactly one notification for that contact."""
    config_contacts = {
        ContactName("userX"): Contact({"email": "x@example.com"}),
    }
    enriched_context = EnrichedEventContext({"HOSTNAME": HostName("testhost"), "WHAT": "HOST"})

    notifications, rule_info = notify._create_notifications(  # noqa: SLF001
        enriched_context=enriched_context,
        rule=_make_add_rule(contact_users=["userX"]),
        parameters=_TEST_PARAMETERS,
        notifications=[],
        rule_info=[],
        host_parameters_cb=lambda _host, _plugin: {},
        config_contacts=config_contacts,
        fallback_email="",
        rule_nr=0,
        timeperiods_active={},
    )
    notifications, rule_info = notify._create_notifications(  # noqa: SLF001
        enriched_context=enriched_context,
        rule=_make_add_rule(contact_users=["userX"]),
        parameters=_TEST_PARAMETERS,
        notifications=notifications,
        rule_info=rule_info,
        host_parameters_cb=lambda _host, _plugin: {},
        config_contacts=config_contacts,
        fallback_email="",
        rule_nr=1,
        timeperiods_active={},
    )

    assert len(notifications) == 1
    assert notifications[0].contacts == {ContactName("userX")}


def test_cancellation_removes_contact_from_all_matching_entries() -> None:
    """A cancel rule removes a contact from ALL entries for the same plugin,
    even if they have different parameters."""
    config_contacts = {
        ContactName("userX"): Contact({"email": "x@example.com"}),
    }
    enriched_context = EnrichedEventContext({"HOSTNAME": HostName("testhost"), "WHAT": "HOST"})
    param_alpha = NotificationParameterID("alpha")
    param_beta = NotificationParameterID("beta")
    parameters: NotificationParameterSpecs = {
        _TEST_PLUGIN: {
            param_alpha: {
                "general": _TEST_GENERAL,
                "parameter_properties": {"mode": "alpha"},
            },
            param_beta: {
                "general": _TEST_GENERAL,
                "parameter_properties": {"mode": "beta"},
            },
        }
    }

    notifications, rule_info = notify._create_notifications(  # noqa: SLF001
        enriched_context=enriched_context,
        rule=_make_add_rule(contact_users=["userX"], param_id=param_alpha),
        parameters=parameters,
        notifications=[],
        rule_info=[],
        host_parameters_cb=lambda _host, _plugin: {},
        config_contacts=config_contacts,
        fallback_email="",
        rule_nr=0,
        timeperiods_active={},
    )
    notifications, rule_info = notify._create_notifications(  # noqa: SLF001
        enriched_context=enriched_context,
        rule=_make_add_rule(contact_users=["userX"], param_id=param_beta),
        parameters=parameters,
        notifications=notifications,
        rule_info=rule_info,
        host_parameters_cb=lambda _host, _plugin: {},
        config_contacts=config_contacts,
        fallback_email="",
        rule_nr=1,
        timeperiods_active={},
    )
    assert len(notifications) == 2

    notifications, rule_info = notify._create_notifications(  # noqa: SLF001
        enriched_context=enriched_context,
        rule=_make_cancel_rule(contact_users=["userX"]),
        parameters=parameters,
        notifications=notifications,
        rule_info=rule_info,
        host_parameters_cb=lambda _host, _plugin: {},
        config_contacts=config_contacts,
        fallback_email="",
        rule_nr=2,
        timeperiods_active={},
    )

    assert len(notifications) == 0


def test_user_rule_creates_separate_entry_when_locked_entry_exists() -> None:
    """A user rule cannot merge into a locked notification, but should
    create a separate entry so the user still gets notified."""
    config_contacts = {
        ContactName("userX"): Contact({"email": "x@example.com"}),
        ContactName("userY"): Contact({"email": "y@example.com"}),
    }
    enriched_context = EnrichedEventContext({"HOSTNAME": HostName("testhost"), "WHAT": "HOST"})

    notifications, rule_info = notify._create_notifications(  # noqa: SLF001
        enriched_context=enriched_context,
        rule=_make_add_rule(allow_disable=False, contact_users=["userX"]),
        parameters=_TEST_PARAMETERS,
        notifications=[],
        rule_info=[],
        host_parameters_cb=lambda _host, _plugin: {},
        config_contacts=config_contacts,
        fallback_email="",
        rule_nr=0,
        timeperiods_active={},
    )
    assert len(notifications) == 1

    notifications, rule_info = notify._create_notifications(  # noqa: SLF001
        enriched_context=enriched_context,
        # User rule (allow_disable=True → locked=False) targets userY
        rule=_make_add_rule(allow_disable=True, contact="userY", contact_users=["userY"]),
        parameters=_TEST_PARAMETERS,
        notifications=notifications,
        rule_info=rule_info,
        host_parameters_cb=lambda _host, _plugin: {},
        config_contacts=config_contacts,
        fallback_email="",
        rule_nr=1,
        timeperiods_active={},
    )

    # Locked entry stays untouched, user gets a separate entry
    assert len(notifications) == 2
    assert notifications[0].contacts == {ContactName("userX")}
    assert notifications[1].contacts == {ContactName("userY")}


def test_user_rule_for_same_contact_as_locked_entry_is_suppressed() -> None:
    """A user rule targeting the same contact as a locked entry should not
    create a duplicate — the contact is already covered by the locked entry."""
    config_contacts = {
        ContactName("userX"): Contact({"email": "x@example.com"}),
    }
    enriched_context = EnrichedEventContext({"HOSTNAME": HostName("testhost"), "WHAT": "HOST"})

    notifications, rule_info = notify._create_notifications(  # noqa: SLF001
        enriched_context=enriched_context,
        rule=_make_add_rule(allow_disable=False, contact_users=["userX"]),
        parameters=_TEST_PARAMETERS,
        notifications=[],
        rule_info=[],
        host_parameters_cb=lambda _host, _plugin: {},
        config_contacts=config_contacts,
        fallback_email="",
        rule_nr=0,
        timeperiods_active={},
    )

    # User rule (allow_disable=True → locked=False) targets same contact
    notifications, rule_info = notify._create_notifications(  # noqa: SLF001
        enriched_context=enriched_context,
        rule=_make_add_rule(allow_disable=True, contact="userX", contact_users=["userX"]),
        parameters=_TEST_PARAMETERS,
        notifications=notifications,
        rule_info=rule_info,
        host_parameters_cb=lambda _host, _plugin: {},
        config_contacts=config_contacts,
        fallback_email="",
        rule_nr=1,
        timeperiods_active={},
    )

    # userX is already covered by the locked entry — no duplicate
    assert len(notifications) == 1
    assert notifications[0].contacts == {ContactName("userX")}


def test_user_rule_partial_overlap_with_locked_entry() -> None:
    """A user rule targeting contacts partially overlapping with a locked entry
    should only create a new entry for the non-overlapping contacts."""
    config_contacts = {
        ContactName("userX"): Contact({"email": "x@example.com"}),
        ContactName("userY"): Contact({"email": "y@example.com"}),
    }
    enriched_context = EnrichedEventContext({"HOSTNAME": HostName("testhost"), "WHAT": "HOST"})

    notifications, rule_info = notify._create_notifications(  # noqa: SLF001
        enriched_context=enriched_context,
        rule=_make_add_rule(allow_disable=False, contact_users=["userX"]),
        parameters=_TEST_PARAMETERS,
        notifications=[],
        rule_info=[],
        host_parameters_cb=lambda _host, _plugin: {},
        config_contacts=config_contacts,
        fallback_email="",
        rule_nr=0,
        timeperiods_active={},
    )

    notifications, rule_info = notify._create_notifications(  # noqa: SLF001
        enriched_context=enriched_context,
        # User rule (allow_disable=True → locked=False) targets both userX and userY
        rule=_make_add_rule(allow_disable=True, contact="userY", contact_users=["userX", "userY"]),
        parameters=_TEST_PARAMETERS,
        notifications=notifications,
        rule_info=rule_info,
        host_parameters_cb=lambda _host, _plugin: {},
        config_contacts=config_contacts,
        fallback_email="",
        rule_nr=1,
        timeperiods_active={},
    )

    assert len(notifications) == 2
    assert notifications[0].contacts == {ContactName("userX")}
    assert notifications[1].contacts == {ContactName("userY")}


def test__rbn_match_rule_escalation_blocked() -> None:
    assert (
        notify._rbn_match_rule(  # noqa: SLF001
            _make_rule() | {"match_escalation": (1, 5)},
            EnrichedEventContext(
                {"WHAT": "HOST", "HOSTNAME": HostName("testhost"), "HOSTNOTIFICATIONNUMBER": "10"}
            ),
            {},
            define_servicegroups={},
            analyse=False,
            timeperiods_active={},
        )
        == "The notification number 10 does not lie in range 1 ... 5"
    )


_BULK_BY_EVERYTHING = AlwaysBulkParameters(
    interval=60,
    count=10,
    groupby=["host", "folder", "service", "sl", "check_type", "state", "ec_contact", "ec_comment"],
    groupby_custom=["_CUSTOM"],
)


def _bulk_context(value: str) -> NotificationContext:
    return NotificationContext(
        {
            "WHAT": "SERVICE",
            "CONTACTNAME": "harry",
            "HOSTNAME": value,
            "HOSTTAGS": f"/wato/{value}/",
            "SERVICEDESC": value,
            "SERVICE_SL": value,
            "SERVICECHECKCOMMAND": value,
            "SERVICESTATE": value,
            "EC_CONTACT": value,
            "EC_COMMENT": value,
            "SERVICE_CUSTOM": value,
        }
    )


def _store_for_bulk(bulk_root: Path, context: NotificationContext) -> None:
    notify.do_bulk_notify("mail", {}, context, _BULK_BY_EVERYTHING, bulk_root=bulk_root)


def _bulk_dirs(bulk_root: Path) -> list[Path]:
    return sorted((bulk_root / "harry" / "mail").iterdir())


def test_bulk_with_long_grouping_values_is_stored(tmp_path: Path) -> None:
    _store_for_bulk(tmp_path, _bulk_context("x" * 300))

    (bulk_dir,) = _bulk_dirs(tmp_path)
    assert len(bulk_dir.name.encode()) <= 255
    assert len(list(bulk_dir.glob("[!.]*"))) == 1


def test_bulk_with_short_grouping_values_keeps_readable_directory_name(tmp_path: Path) -> None:
    _store_for_bulk(tmp_path, _bulk_context("a/b"))

    assert [d.name for d in _bulk_dirs(tmp_path)] == [
        (
            "60,10,host,a\\b,service,a\\b,sl,a\\b,check_type,a\\b,state,a\\b,"
            "ec_contact,a\\b,ec_comment,a\\b,custom,a\\b"
        )
    ]


def test_identical_long_grouping_values_share_one_bulk(tmp_path: Path) -> None:
    _store_for_bulk(tmp_path, _bulk_context("x" * 300))
    _store_for_bulk(tmp_path, _bulk_context("x" * 300))

    (bulk_dir,) = _bulk_dirs(tmp_path)
    assert len(list(bulk_dir.glob("[!.]*"))) == 2


def test_differing_long_grouping_values_get_separate_bulks(tmp_path: Path) -> None:
    _store_for_bulk(tmp_path, _bulk_context("x" * 300))
    _store_for_bulk(tmp_path, _bulk_context("y" * 300))

    assert len(_bulk_dirs(tmp_path)) == 2


@pytest.mark.parametrize(
    "value",
    [
        pytest.param("x", id="readable directory name"),
        pytest.param("x" * 300, id="hashed directory name"),
    ],
)
def test_open_bulks_report_their_readable_id(tmp_path: Path, value: str) -> None:
    _store_for_bulk(tmp_path, _bulk_context(value))

    bulks = notify.find_bulks(False, bulk_root=tmp_path, bulk_interval=10, timeperiods_active={})

    assert [bulk_id for *_, bulk_id in bulks] == [
        (
            f"60,10,host,{value},service,{value},sl,{value},check_type,{value},state,{value},"
            f"ec_contact,{value},ec_comment,{value},custom,{value}"
        )
    ]


def test_orphaned_hashed_bulk_directory_is_removed(tmp_path: Path) -> None:
    _store_for_bulk(tmp_path, _bulk_context("x" * 300))
    (bulk_dir,) = _bulk_dirs(tmp_path)
    for notification in bulk_dir.glob("[!.]*"):
        notification.unlink()
    an_hour_ago = time.time() - 3600
    os.utime(bulk_dir, (an_hour_ago, an_hour_ago))

    notify.find_bulks(False, bulk_root=tmp_path, bulk_interval=10, timeperiods_active={})

    assert not _bulk_dirs(tmp_path)


@pytest.mark.parametrize(
    "configured, expected",
    [
        pytest.param(0, 20, id="deprecated 0 → info"),
        pytest.param(1, 20, id="legacy 1 → info"),
        pytest.param(2, 10, id="legacy 2 → debug"),
        pytest.param(30, 30, id="logging level is kept"),
    ],
)
def test_legacy_logging_levels_are_mapped(configured: int, expected: int) -> None:
    assert notify.resolve_logging_level(configured) == expected


# fmt: off
@pytest.mark.parametrize(
    "edition, spooling, spool_to, expected",
    [
        pytest.param(Edition.COMMUNITY, None, None, "off", id="community default is off"),
        pytest.param(Edition.PRO, None, None, "local", id="commercial default is local"),
        pytest.param(Edition.COMMUNITY, "both", None, "both", id="explicit setting wins over default"),
        pytest.param(Edition.PRO, "local", ("host", 6555), "remote", id="legacy spool_to wins over setting"),
        pytest.param(Edition.PRO, None, ("host", 6555, True), "both", id="legacy spool_to also local"),
        pytest.param(Edition.PRO, None, ("host", 6555, False), "remote", id="legacy spool_to only remote"),
    ],
)
# fmt: on
def test_spooling_mode_is_resolved(
    edition: Edition,
    spooling: Literal["local", "remote", "both", "off"] | None,
    spool_to: object,
    expected: str,
) -> None:
    assert notify.resolve_spooling(edition, spooling, spool_to) == expected


def _host_parameters_callback(
    merged_values: list[Mapping[str, object]],
) -> Callable[[HostAddress, str], Mapping[str, object]]:
    matcher = Mock(spec=RulesetMatcher)
    matcher.get_host_values_merged.side_effect = merged_values
    return notify.make_notification_parameters_config(
        {"mail": []}, matcher, Mock(spec=LabelManager)
    )


def test_notification_parameters_are_the_merged_host_values() -> None:
    get_parameters = _host_parameters_callback([{"from": "a@example.com"}])

    assert get_parameters(HostAddress("h"), "mail") == {"from": "a@example.com"}


def test_notification_parameters_are_computed_once_per_host_and_plugin() -> None:
    get_parameters = _host_parameters_callback([{"from": "first"}, {"from": "second"}])
    get_parameters(HostAddress("h"), "mail")

    assert get_parameters(HostAddress("h"), "mail") == {"from": "first"}


def test_ensure_nagios_accepts_nagios_core() -> None:
    assert notify.make_ensure_nagios("nagios")("only with nagios") is None


def test_ensure_nagios_rejects_other_cores() -> None:
    with pytest.raises(RuntimeError, match="only with nagios"):
        notify.make_ensure_nagios("cmc")("only with nagios")


def test_user_notification_rules_are_owned_by_their_contact_and_can_be_disabled() -> None:
    contacts = {"bob": Contact({"notification_rules": [_make_rule()]})}

    (rule,) = notify.user_notification_rules(contacts)

    assert (rule.get("contact"), rule["allow_disable"]) == ("bob", True)


def test_user_notification_rules_are_ordered_by_contact_name() -> None:
    contacts = {
        "zed": Contact({"notification_rules": [_make_rule() | {"description": "zed's"}]}),
        "amy": Contact({"notification_rules": [_make_rule() | {"description": "amy's"}]}),
    }

    rules = notify.user_notification_rules(contacts)

    assert [r["description"] for r in rules] == ["amy's", "zed's"]


# fmt: off
@pytest.mark.parametrize(
    "rule, expected_sites",
    [
        pytest.param(_make_rule(), ["site_a"], id="authorized sites become the site condition"),
        pytest.param(_make_rule() | {"match_site": ["site_b"]}, ["site_b"], id="explicit site condition is kept"),
    ],
)
# fmt: on
def test_user_notification_rules_respect_authorized_sites(
    rule: EventRule, expected_sites: list[str]
) -> None:
    contacts = {
        "bob": Contact({"notification_rules": [rule], "authorized_sites": ["site_a"]}),
    }

    (user_rule,) = notify.user_notification_rules(contacts)

    assert user_rule.get("match_site") == expected_sites


def test_fallback_contacts_are_fallback_email_and_flagged_contacts_with_email() -> None:
    config_contacts = {
        "alice": cast(Contact, {"email": "alice@example.com", "fallback_contact": True}),
        "bob": cast(Contact, {"fallback_contact": True}),
        "carl": Contact({"email": "carl@example.com"}),
    }

    contacts = notify.rbn_fallback_contacts(
        config_contacts=config_contacts, fallback_email="fb@example.com"
    )

    assert [c.get("name") for c in contacts] == ["mailto:fb@example.com", "alice"]


@pytest.mark.parametrize(
    "contacts_value, expected",
    [
        pytest.param("?", ["mailto:fb@example.com", "alice"], id="unknown contacts → fallback"),
        pytest.param("alice,bob", ["alice", "bob"], id="comma separated contacts"),
        pytest.param("", [], id="no contacts"),
    ],
)
def test_object_contact_names(contacts_value: str, expected: list[str]) -> None:
    config_contacts = {
        "alice": cast(Contact, {"email": "alice@example.com", "fallback_contact": True}),
    }

    assert (
        notify.rbn_object_contact_names(
            EventContext({"CONTACTS": contacts_value, "HOSTNAME": HostName("h")}),
            config_contacts=config_contacts,
            fallback_email="fb@example.com",
        )
        == expected
    )


_RULE_CONTACTS: Final[Mapping[ContactName, Contact]] = {
    "alice": Contact({"email": "alice@example.com", "contactgroups": ["ops"]}),
    "bob": Contact({"contactgroups": ["dev"]}),
}


# fmt: off
@pytest.mark.parametrize(
    "rule, expected",
    [
        pytest.param(_make_rule() | {"contact_object": True}, {"bob"}, id="contacts of the object"),
        pytest.param(_make_rule() | {"contact_all": True}, {"alice", "bob"}, id="all contacts"),
        pytest.param(_make_rule() | {"contact_all_with_email": True}, {"alice"}, id="all contacts with email"),
        pytest.param(_make_rule() | {"contact_groups": ["ops"]}, {"alice"}, id="members of contact groups"),
        pytest.param(_make_rule() | {"contact_emails": ["x@example.com"]}, {"mailto:x@example.com"}, id="explicit email addresses"),
        pytest.param(_make_rule() | {"contact_users": ["unknown"]}, {"unknown"}, id="unknown user without restrictions"),
        pytest.param(_make_rule() | {"contact_users": ["fb@example.com"]}, {"fb@example.com"}, id="fallback address as user"),
        pytest.param(_make_rule() | {"contact_all": True, "contact_match_groups": ["ops"]}, {"alice"}, id="restricted to group members"),
    ],
)
# fmt: on
def test_rule_contacts(rule: EventRule, expected: set[str]) -> None:
    assert notify.rbn_rule_contacts(
        rule,
        EventContext({"CONTACTS": "bob", "HOSTNAME": HostName("h")}),
        fallback_email="fb@example.com",
        config_contacts=_RULE_CONTACTS,
    ) == frozenset(expected)


_NOW: Final = time.time()


# fmt: off
@pytest.mark.parametrize(
    "disable_notifications, expected",
    [
        pytest.param({"disable": True}, frozenset(), id="disabled forever"),
        pytest.param({"disable": True, "timerange": (_NOW - 3600, _NOW + 3600)}, frozenset(), id="disabled right now"),
        pytest.param({"disable": True, "timerange": (_NOW - 7200, _NOW - 3600)}, frozenset({"alice"}), id="disabled in the past"),
        pytest.param({"disable": False}, frozenset({"alice"}), id="not disabled"),
    ],
)
# fmt: on
def test_rule_contacts_skip_contacts_with_disabled_notifications(
    disable_notifications: Mapping[str, object], expected: frozenset[str]
) -> None:
    # The GUI stores the key "disable", the Contact type wrongly declares "disabled"
    contacts = {"alice": cast(Contact, {"disable_notifications": disable_notifications})}

    assert (
        notify.rbn_rule_contacts(
            _make_rule() | {"contact_users": ["alice"]},
            EventContext({"HOSTNAME": HostName("h")}),
            fallback_email="",
            config_contacts=contacts,
        )
        == expected
    )


def test_contact_information_of_contact_dicts_includes_custom_macros() -> None:
    plugin_context = NotificationContext({})

    notify.rbn_add_contact_information(
        plugin_context,
        [
            cast(Contact, {"name": "alice", "email": "a@example.com", "_tel": "123"}),
            Contact({"name": "bob", "alias": "Bob", "pager": "0815"}),
        ],
        {},
    )

    assert plugin_context == {
        "CONTACTNAME": "alice,bob",
        "CONTACTALIAS": ",Bob",
        "CONTACTEMAIL": "a@example.com,",
        "CONTACTPAGER": ",0815",
        "CONTACT_TEL": "123,",
    }


def _contact_information_of(contact: str) -> NotificationContext:
    plugin_context = NotificationContext({})
    notify.rbn_add_contact_information(
        plugin_context,
        frozenset({contact}),
        {"alice": Contact({"email": "alice@example.com"})},
    )
    return plugin_context


def test_contact_information_of_an_explicit_email_address() -> None:
    assert _contact_information_of("mailto:x@example.com") == {
        "CONTACTNAME": "x@example.com",
        "CONTACTALIAS": "Email address mailto:x@example.com",
        "CONTACTEMAIL": "x@example.com",
        "CONTACTPAGER": "",
    }


def test_contact_information_of_a_configured_contact() -> None:
    assert _contact_information_of("alice") == {
        "CONTACTNAME": "alice",
        "CONTACTALIAS": "",
        "CONTACTEMAIL": "alice@example.com",
        "CONTACTPAGER": "",
    }


def test_contact_information_of_an_unknown_contact() -> None:
    assert _contact_information_of("unknown") == {
        "CONTACTNAME": "unknown",
        "CONTACTALIAS": "unknown",
        "CONTACTEMAIL": "",
        "CONTACTPAGER": "",
    }


def test_plugin_context_of_a_single_contact_is_not_split() -> None:
    plugin_context = NotificationContext({"CONTACTNAME": "alice", "HOSTNAME": "h"})

    assert notify.rbn_split_plugin_context(plugin_context) == [plugin_context]


def test_plugin_context_is_split_per_contact() -> None:
    plugin_context = NotificationContext(
        {
            "CONTACTNAME": "alice,bob",
            "CONTACTALIAS": "Alice,Bob",
            "CONTACTEMAIL": "a@example.com,b@example.com",
            "CONTACTPAGER": ",",
            "CONTACT_TEL": "1,2",
            "HOSTNAME": "h",
        }
    )

    assert notify.rbn_split_plugin_context(plugin_context) == [
        {
            "CONTACTNAME": "alice",
            "CONTACTALIAS": "Alice",
            "CONTACTEMAIL": "a@example.com",
            "CONTACTPAGER": "",
            "CONTACT_TEL": "1",
            "HOSTNAME": "h",
        },
        {
            "CONTACTNAME": "bob",
            "CONTACTALIAS": "Bob",
            "CONTACTEMAIL": "b@example.com",
            "CONTACTPAGER": "",
            "CONTACT_TEL": "2",
            "HOSTNAME": "h",
        },
    ]


_ALWAYS_BULK: Final = AlwaysBulkParameters(interval=60, count=10, groupby=[])
_NIGHT_BULK: Final = TimeperiodBulkParameters(timeperiod="night", count=10, groupby=[])
_NIGHT_BULK_WITH_OUTSIDE: Final = TimeperiodBulkParameters(
    timeperiod="night", count=10, groupby=[], bulk_outside=_ALWAYS_BULK
)


class _UnreachableCore(Mapping[str, bool]):
    @override
    def __getitem__(self, key: str) -> bool:
        raise MKLivestatusException(f"core not reachable to look up {key}")

    @override
    def __iter__(self) -> Iterator[str]:
        return iter(())

    @override
    def __len__(self) -> int:
        return 0


@pytest.mark.parametrize(
    "notification_type, event",
    [
        pytest.param("FLAPPINGSTART", "f", id="flapping"),
        pytest.param("DOWNTIMESTART", "s", id="downtime"),
        pytest.param("ACKNOWLEDGEMENT", "x", id="acknowledgement"),
        pytest.param("ALERTHANDLER (OK)", "as", id="alert handler succeeded"),
        pytest.param("ALERTHANDLER (CRITICAL)", "af", id="alert handler failed"),
    ],
)
def test_event_type_of_non_state_change_service_notification(
    notification_type: str, event: str
) -> None:
    # Alert handler notification types are outside the NotificationType literal.
    context = cast(
        EventContext,
        {
            "WHAT": "SERVICE",
            "NOTIFICATIONTYPE": notification_type,
            "SERVICESTATE": "OK",
            "PREVIOUSSERVICEHARDSTATE": "OK",
        }
    )

    assert (
        notify.rbn_match_service_event(
            _make_rule() | {"match_service_event": ["rr"]}, context, False, {}
        )
        == f"Event type '{event}' not handled by this rule. Allowed are: rr"
    )


@pytest.mark.parametrize(
    "priority_range, priority, matches",
    [
        pytest.param((0, 3), "2", True, id="within an ascending range"),
        pytest.param((0, 3), "7", False, id="outside an ascending range"),
        pytest.param((2, 2), "2", True, id="the single priority of a range"),
        pytest.param((2, 2), "5", False, id="another than the single priority of a range"),
    ],
)
def test_ec_alerts_are_filtered_by_ascending_and_single_priority_ranges(
    priority_range: tuple[SyslogPriorityIntType, SyslogPriorityIntType],
    priority: str,
    matches: bool,
) -> None:
    rule = _make_rule() | {"match_ec": {"match_priority": priority_range}}
    context = EventContext({"EC_ID": "1", "EC_PRIORITY": priority})

    assert (notify.rbn_match_event_console(rule, context, False, {}) is None) is matches


def test_bulk_parameter_context_escapes_line_breaks() -> None:
    assert notify.create_bulk_parameter_context(
        {"subject": "first\r\nsecond"},
        _environment_proxy,
    ) == ["PARAMETER_SUBJECT=first\x01second\n"]


def _install_plugin(name: str, out_dir: Path, *, exit_code: int = 0) -> Path:
    """Install a notification plug-in that records what it was called with"""
    script = cmk.utils.paths.local_notifications_dir / name
    script.parent.mkdir(parents=True, exist_ok=True)
    bulk_calls, sent = shlex.quote(str(out_dir / "bulk_calls")), shlex.quote(str(out_dir / "sent"))
    script.write_text(
        "#!/bin/sh\n"
        'if [ "$1" = "--bulk" ]; then\n'
        f"  cat >> {bulk_calls}; echo ===== >> {bulk_calls}\n"
        "else\n"
        f'  echo "$NOTIFY_CONTACTEMAIL" >> {sent}\n'
        "fi\n"
        "echo some output\n"
        f"exit {exit_code}\n"
    )
    script.chmod(0o755)
    return script


def _sent_to(out_dir: Path) -> list[str]:
    return (out_dir / "sent").read_text().splitlines()


@pytest.fixture(name="no_monitoring_core")
def fixture_no_monitoring_core(monkeypatch: MonkeyPatch) -> None:
    # Without OMD_ROOT, logging to the monitoring history fails right away instead of
    # waiting for the core's socket to time out
    monkeypatch.delenv("OMD_ROOT", raising=False)


def test_notification_script_path_rejects_slashes() -> None:
    with pytest.raises(MKGeneralException):
        notify.path_to_notification_script(CustomPluginName("../evil"))


def test_notification_script_path_of_unknown_plugin_is_none() -> None:
    assert notify.path_to_notification_script(CustomPluginName("no_such_plugin")) is None


def test_notification_script_path_prefers_local_plugin(tmp_path: Path) -> None:
    local_script = _install_plugin("mail", tmp_path)

    assert notify.path_to_notification_script("mail") == str(local_script)


def test_notification_script_env_truncates_too_long_values() -> None:
    env = notify.notification_script_env(NotificationContext({"LONGSERVICEOUTPUT": "x" * 2**20}))

    assert env["NOTIFY_LONGSERVICEOUTPUT"].endswith(
        "x...\nAttention: Removed remaining content because it was too long."
    )


_PLUGIN_CONTEXT: Final = NotificationContext(
    {"CONTACTNAME": "harry", "CONTACTEMAIL": "harry@example.com", "HOSTNAME": "h"}
)


@pytest.mark.usefixtures("no_monitoring_core")
def test_calling_an_unknown_notification_script_fails_permanently() -> None:
    assert (
        notify.call_notification_script(
            CustomPluginName("no_such_plugin"), _PLUGIN_CONTEXT, plugin_timeout=10
        )
        == 2
    )


@pytest.mark.usefixtures("no_monitoring_core")
def test_notification_script_gets_context_as_environment(tmp_path: Path) -> None:
    _install_plugin("my_script", tmp_path)

    notify.call_notification_script(
        CustomPluginName("my_script"), _PLUGIN_CONTEXT, plugin_timeout=10
    )

    assert _sent_to(tmp_path) == ["harry@example.com"]


@pytest.mark.usefixtures("no_monitoring_core")
def test_notification_script_exit_code_is_returned(tmp_path: Path) -> None:
    _install_plugin("my_script", tmp_path, exit_code=1)

    assert (
        notify.call_notification_script(
            CustomPluginName("my_script"), _PLUGIN_CONTEXT, plugin_timeout=10
        )
        == 1
    )


# With OMD_SITE set, the notification counts as enriched already and needs no core
_HARRY_NOTIFICATION: Final = {
    "OMD_SITE": "mysite",
    "WHAT": "HOST",
    "HOSTNAME": "testhost",
    "HOSTSTATE": "DOWN",
    "NOTIFICATIONTYPE": "PROBLEM",
}


_HARRY: Final = {ContactName("harry"): Contact({"email": "harry@example.com"})}


def _notification_config(
    rules: list[EventRule],
    *,
    spooling: Literal["local", "remote", "both", "off"] = "off",
    fallback_email: str = "",
) -> notify.NotificationConfig:
    return notify.NotificationConfig(
        rules=rules,
        parameters=_TEST_PARAMETERS,
        backlog_size=10,
        bulk_interval=10,
        fallback_email=fallback_email,
        fallback_format=(_TEST_PLUGIN, {}),
        plugin_timeout=10,
        spooling=spooling,
        logging_level=20,
        host_parameters_cb=lambda _host, _plugin: {},
    )


def _do_notify(
    args: list[str],
    notification_config: notify.NotificationConfig,
    timeperiods_active: Mapping[str, bool] | None = None,
) -> int | None:
    return notify.do_notify(
        {},
        args,
        notification_config=notification_config,
        define_servicegroups={},
        get_http_proxy=_environment_proxy,
        ensure_nagios=lambda _site: None,
        config_contacts=_HARRY,
        keepalive=False,
        all_timeperiods={},
        timeperiods_active={} if timeperiods_active is None else timeperiods_active,
    )


def _notification_test(
    notification_config: notify.NotificationConfig, *, dispatch: str = ""
) -> NotifyAnalysisInfo | None:
    return notify.notification_test(
        NotificationContext({**_HARRY_NOTIFICATION, "CONTACTS": ""}),
        _environment_proxy,
        lambda _site: None,
        notification_config=notification_config,
        define_servicegroups={},
        config_contacts=_HARRY,
        all_timeperiods={},
        dispatch=dispatch,
        timeperiods_active={},
    )


@pytest.fixture(name="release_locks")
def fixture_release_locks() -> Iterator[None]:
    yield
    # Storing the backlog keeps it locked, like the long running notification helper does
    store.release_all_locks()


@pytest.fixture(name="isolated_logging")
def fixture_isolated_logging() -> Iterator[None]:
    # do_notify points the global "cmk" logger at notify.log
    notify.notification_log.parent.mkdir(parents=True, exist_ok=True)
    level, handlers = log.logger.level, list(log.logger.handlers)
    yield
    for handler in log.logger.handlers:
        if handler not in handlers:
            handler.close()
    log.logger.handlers = handlers
    log.logger.setLevel(level)


@pytest.fixture(name="core_notification")
def fixture_core_notification(monkeypatch: MonkeyPatch) -> None:
    for key, value in _HARRY_NOTIFICATION.items():
        monkeypatch.setenv(f"NOTIFY_{key}", value)


@pytest.mark.usefixtures("isolated_logging")
def test_analysis_reports_notifications_without_sending_them(tmp_path: Path) -> None:
    _install_plugin("my_script", tmp_path)

    analysis = _notification_test(_notification_config([_make_add_rule(contact_users=["harry"])]))

    assert analysis is not None
    assert (analysis[1], (tmp_path / "sent").exists()) == (
        [("harry", "my_script", {}, None)],
        False,
    )


@pytest.mark.usefixtures("isolated_logging")
def test_analysis_reports_why_a_rule_does_not_match() -> None:
    rule = _make_add_rule(contact_users=["harry"]) | {"disabled": True}

    analysis = _notification_test(_notification_config([rule]))

    assert analysis is not None
    assert analysis[0] == [("miss", rule, "This rule is disabled")]


@pytest.mark.usefixtures("no_monitoring_core", "isolated_logging")
def test_test_notification_is_sent_via_the_dispatched_plugin(tmp_path: Path) -> None:
    _install_plugin("my_script", tmp_path)

    _notification_test(
        _notification_config([_make_add_rule(contact_users=["harry"])]), dispatch="my_script"
    )

    assert _sent_to(tmp_path) == ["harry@example.com"]


@pytest.mark.usefixtures("core_notification", "release_locks", "no_monitoring_core", "isolated_logging")
def test_notification_is_sent_directly_without_spooling(tmp_path: Path) -> None:
    _install_plugin("my_script", tmp_path)

    _do_notify([], _notification_config([_make_add_rule(contact_users=["harry"])]))

    assert _sent_to(tmp_path) == ["harry@example.com"]


@pytest.mark.usefixtures("core_notification", "release_locks", "isolated_logging")
def test_notification_is_spooled_for_local_delivery() -> None:
    _do_notify(
        [], _notification_config([_make_add_rule(contact_users=["harry"])], spooling="local")
    )

    (spool_file,) = notify.notification_spooldir.iterdir()
    spooled = store.load_object_from_file(spool_file, default={})
    assert (spooled["plugin"], spooled["context"]["CONTACTNAME"]) == ("my_script", "harry")


# fmt: off
@pytest.mark.parametrize(
    "bulk, timeperiods_active, expected_bulk",
    [
        pytest.param(("always", _ALWAYS_BULK), {}, "60,10", id="always bulk"),
        pytest.param(("timeperiod", _NIGHT_BULK), {"night": True}, "timeperiod:night,10", id="inside time period"),
        pytest.param(("timeperiod", _NIGHT_BULK_WITH_OUTSIDE), {"night": False}, "60,10", id="outside time period with bulking outside"),
        pytest.param(("timeperiod", _NIGHT_BULK), _UnreachableCore(), "timeperiod:night,10", id="unknown time period state is assumed active"),
    ],
)
# fmt: on
@pytest.mark.usefixtures("core_notification", "release_locks", "disable_debug", "isolated_logging")
def test_notification_of_bulk_rule_is_stored_for_bulk_delivery(
    bulk: NotifyBulkType,
    timeperiods_active: Mapping[str, bool],
    expected_bulk: str,
) -> None:
    rule = _make_add_rule(contact_users=["harry"]) | {"bulk": bulk}

    _do_notify([], _notification_config([rule]), timeperiods_active)

    bulk_dirs = (Path(notify.notification_bulkdir) / "harry" / "my_script").iterdir()
    assert [d.name for d in bulk_dirs] == [expected_bulk]


@pytest.mark.usefixtures("core_notification", "release_locks", "no_monitoring_core", "isolated_logging")
def test_notification_outside_bulk_time_period_is_sent_directly(tmp_path: Path) -> None:
    _install_plugin("my_script", tmp_path)
    rule = _make_add_rule(contact_users=["harry"]) | {"bulk": ("timeperiod", _NIGHT_BULK)}

    _do_notify([], _notification_config([rule]), {"night": False})

    assert _sent_to(tmp_path) == ["harry@example.com"]


@pytest.mark.usefixtures("core_notification", "release_locks", "no_monitoring_core", "isolated_logging")
def test_fallback_address_is_notified_when_no_rule_matches(tmp_path: Path) -> None:
    _install_plugin("my_script", tmp_path)

    _do_notify([], _notification_config([], fallback_email="fb@example.com"))

    assert _sent_to(tmp_path) == ["fb@example.com"]


@pytest.mark.usefixtures("isolated_logging")
def test_missing_spool_file_fails_permanently(tmp_path: Path) -> None:
    assert _do_notify(["spoolfile", str(tmp_path / "spoolfile")], _notification_config([])) == 2


@pytest.mark.parametrize(
    "content",
    [
        pytest.param("", id="empty spool file"),
        pytest.param("{'plugin': 'my_script'}", id="spool file without context"),
    ],
)
@pytest.mark.usefixtures("isolated_logging")
def test_invalid_spool_file_fails_permanently(tmp_path: Path, content: str) -> None:
    spoolfile = tmp_path / "spoolfile"
    spoolfile.write_text(content)

    assert _do_notify(["spoolfile", str(spoolfile)], _notification_config([])) == 2


@pytest.mark.usefixtures("no_monitoring_core", "isolated_logging")
def test_spool_file_for_plugin_returns_plugin_exit_code(tmp_path: Path) -> None:
    _install_plugin("my_script", tmp_path, exit_code=1)
    spoolfile = tmp_path / "spoolfile"
    spoolfile.write_text(repr({"plugin": "my_script", "context": dict(_PLUGIN_CONTEXT)}))

    assert _do_notify(["spoolfile", str(spoolfile)], _notification_config([])) == 1


@pytest.mark.usefixtures("release_locks", "isolated_logging")
def test_forwarded_spool_file_is_processed_by_local_rules(tmp_path: Path) -> None:
    spoolfile = tmp_path / "spoolfile"
    spoolfile.write_text(repr({"context": _HARRY_NOTIFICATION}))

    _do_notify(
        ["spoolfile", str(spoolfile)],
        _notification_config([_make_add_rule(contact_users=["harry"])], spooling="local"),
    )

    (spool_file,) = notify.notification_spooldir.iterdir()
    assert store.load_object_from_file(spool_file, default={})["plugin"] == "my_script"


def _stored_bulk_notification(
    bulk_dir: Path,
) -> tuple[NotifyPluginParamsDict, NotificationContext]:
    (notification,) = bulk_dir.glob("[!.]*")
    params, context = ast.literal_eval(notification.read_text())
    return params, context


# fmt: off
@pytest.mark.parametrize(
    "bulk, expected_name",
    [
        pytest.param(TimeperiodBulkParameters(timeperiod="night", count=5, groupby=["host"]), "timeperiod:night,5,host,h", id="time period"),
        pytest.param(AlwaysBulkParameters(interval=60, count=5, groupby=["folder"]), "60,5,folder,linux", id="folder"),
    ],
)
# fmt: on
def test_bulk_directory_is_named_after_its_grouping(
    tmp_path: Path, bulk: NotifyBulkParameters, expected_name: str
) -> None:
    notify.do_bulk_notify(
        "mail",
        {},
        NotificationContext(
            {"WHAT": "HOST", "CONTACTNAME": "harry", "HOSTNAME": "h", "HOSTTAGS": "/wato/linux/"}
        ),
        bulk,
        bulk_root=tmp_path,
    )

    assert [d.name for d in (tmp_path / "harry" / "mail").iterdir()] == [expected_name]


def test_bulk_subject_is_stored_with_the_notification(tmp_path: Path) -> None:
    notify.do_bulk_notify(
        "mail",
        {},
        NotificationContext({"WHAT": "HOST", "CONTACTNAME": "harry", "HOSTNAME": "h"}),
        AlwaysBulkParameters(interval=60, count=5, groupby=[], bulk_subject="Bulk!"),
        bulk_root=tmp_path,
    )

    _params, context = _stored_bulk_notification(tmp_path / "harry" / "mail" / "60,5")
    assert context["PARAMETER_BULK_SUBJECT"] == "Bulk!"


def test_bulk_with_slash_in_contact_name_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(MKGeneralException):
        notify.do_bulk_notify(
            "mail",
            {},
            NotificationContext({"WHAT": "HOST", "CONTACTNAME": "../harry", "HOSTNAME": "h"}),
            _ALWAYS_BULK,
            bulk_root=tmp_path,
        )


@pytest.mark.parametrize(
    "dirname, expected",
    [
        pytest.param("60,10,host,h", (60, None, 10), id="interval bulk"),
        pytest.param("timeperiod:night,5", (None, "night", 5), id="time period bulk"),
        pytest.param("bogus,5", None, id="invalid interval"),
        pytest.param("60,many", None, id="invalid count"),
    ],
)
def test_bulk_parts(dirname: str, expected: tuple[int | None, str | None, int] | None) -> None:
    assert notify.bulk_parts("method_dir", dirname) == expected


def test_bulk_uuids_skips_temporary_hidden_and_foreign_files(tmp_path: Path) -> None:
    older, newer = str(uuid.uuid4()), str(uuid.uuid4())
    for name, mtime in [
        (newer, 2000.0),
        (older, 1000.0),
        ("x.new", 1.0),
        (".bulk_id", 1.0),
        ("foreign", 1.0),
    ]:
        (tmp_path / name).write_text("")
        os.utime(tmp_path / name, (mtime, mtime))

    assert notify.bulk_uuids(str(tmp_path)) == ([(1000.0, older), (2000.0, newer)], 1000.0)


def test_recently_changed_empty_bulk_directory_is_kept(tmp_path: Path) -> None:
    notify.remove_if_orphaned(str(tmp_path), max_age=60, ref_time=tmp_path.stat().st_mtime + 10)

    assert tmp_path.exists()


def test_old_bulk_directory_with_notifications_is_kept(tmp_path: Path) -> None:
    (tmp_path / str(uuid.uuid4())).write_text("")

    notify.remove_if_orphaned(str(tmp_path), max_age=60, ref_time=tmp_path.stat().st_mtime + 3600)

    assert tmp_path.exists()


def test_no_bulks_without_bulk_directory(tmp_path: Path) -> None:
    assert (
        notify.find_bulks(
            False, bulk_root=tmp_path / "missing", bulk_interval=10, timeperiods_active={}
        )
        == []
    )


def _make_bulk(bulk_root: Path, dirname: str, *, notifications: int, age: float) -> None:
    bulk_dir = bulk_root / "harry" / "mail" / dirname
    bulk_dir.mkdir(parents=True)
    mtime = time.time() - age
    for _ in range(notifications):
        notification = bulk_dir / str(uuid.uuid4())
        notification.write_text("")
        os.utime(notification, (mtime, mtime))


# fmt: off
@pytest.mark.parametrize(
    "dirname, notifications, age, timeperiods_active, ripe",
    [
        pytest.param("60,10", 1, 120, {}, True, id="interval elapsed"),
        pytest.param("60,2", 2, 0, {}, True, id="interval bulk is full"),
        pytest.param("60,10", 1, 0, {}, False, id="interval bulk is young and not full"),
        pytest.param("timeperiod:night,10", 1, 0, {"night": True}, False, id="time period active"),
        pytest.param("timeperiod:night,10", 1, 0, {"night": False}, True, id="time period ended"),
        pytest.param("timeperiod:night,1", 1, 0, {"night": True}, True, id="time period bulk is full"),
        pytest.param("timeperiod:night,10", 1, 0, {}, True, id="time period unknown"),
        pytest.param("timeperiod:night,10", 1, 0, _UnreachableCore(), False, id="time period state unknown"),
        pytest.param("bogus,10", 1, 120, {}, False, id="invalid bulk directory"),
    ],
)
# fmt: on
def test_ripe_bulks(
    tmp_path: Path,
    dirname: str,
    notifications: int,
    age: float,
    timeperiods_active: Mapping[str, bool],
    ripe: bool,
) -> None:
    _make_bulk(tmp_path, dirname, notifications=notifications, age=age)

    bulks = notify.find_bulks(
        True, bulk_root=tmp_path, bulk_interval=10, timeperiods_active=timeperiods_active
    )

    assert bool(bulks) is ripe


def _store_bulk_notification(
    bulk_root: Path, hostname: str, params: NotifyPluginParamsDict, *, mtime: float = 1000.0
) -> None:
    notify.do_bulk_notify(
        _TEST_PLUGIN,
        params,
        NotificationContext({"WHAT": "HOST", "CONTACTNAME": "harry", "HOSTNAME": hostname}),
        _ALWAYS_BULK,
        bulk_root=bulk_root,
    )
    for notification in (bulk_root / "harry" / _TEST_PLUGIN / "60,10").glob("[!.]*"):
        if f"'HOSTNAME': '{hostname}'" in notification.read_text():
            os.utime(notification, (mtime, mtime))


def _send_bulk(bulk_root: Path) -> None:
    ((bulk_dir, *_rest, uuids, _bulk_id),) = notify.find_bulks(
        False, bulk_root=bulk_root, bulk_interval=10, timeperiods_active={}
    )
    notify.notify_bulk(
        bulk_dir,
        uuids,
        _environment_proxy,
        plugin_timeout=10,
    )


def _bulk_calls(out_dir: Path) -> list[list[str]]:
    """Lines piped into the bulk plug-in, one list per call"""
    return [
        call.strip().splitlines() for call in (out_dir / "bulk_calls").read_text().split("=====")[:-1]
    ]


@pytest.mark.usefixtures("no_monitoring_core")
def test_bulk_is_sent_with_parameters_and_all_notifications(tmp_path: Path) -> None:
    _install_plugin(_TEST_PLUGIN, tmp_path)
    _store_bulk_notification(tmp_path / "bulk", "h1", {"subject": "S"}, mtime=1000.0)
    _store_bulk_notification(tmp_path / "bulk", "h2", {"subject": "S"}, mtime=2000.0)

    _send_bulk(tmp_path / "bulk")

    assert [
        [line for line in call if line.startswith(("PARAMETER_", "HOSTNAME="))]
        for call in _bulk_calls(tmp_path)
    ] == [["PARAMETER_SUBJECT=S", "HOSTNAME=h1", "HOSTNAME=h2"]]


@pytest.mark.usefixtures("no_monitoring_core")
def test_sent_bulk_is_removed(tmp_path: Path) -> None:
    _install_plugin(_TEST_PLUGIN, tmp_path)
    _store_bulk_notification(tmp_path / "bulk", "h1", {})

    _send_bulk(tmp_path / "bulk")

    assert not list((tmp_path / "bulk" / "harry" / _TEST_PLUGIN).iterdir())


@pytest.mark.usefixtures("no_monitoring_core")
def test_bulk_notifications_with_different_parameters_are_sent_separately(
    tmp_path: Path,
) -> None:
    _install_plugin(_TEST_PLUGIN, tmp_path)
    _store_bulk_notification(tmp_path / "bulk", "h1", {"subject": "A"}, mtime=1000.0)
    _store_bulk_notification(tmp_path / "bulk", "h2", {"subject": "B"}, mtime=2000.0)

    _send_bulk(tmp_path / "bulk")

    assert len(_bulk_calls(tmp_path)) == 2


@pytest.mark.usefixtures("no_monitoring_core")
def test_bulk_can_be_sent_newest_first(tmp_path: Path) -> None:
    _install_plugin(_TEST_PLUGIN, tmp_path)
    params: NotifyPluginParamsDict = {"bulk_sort_order": "newest_first"}
    _store_bulk_notification(tmp_path / "bulk", "h1", params, mtime=1000.0)
    _store_bulk_notification(tmp_path / "bulk", "h2", params, mtime=2000.0)

    _send_bulk(tmp_path / "bulk")

    (call,) = _bulk_calls(tmp_path)
    assert [line for line in call if line.startswith("HOSTNAME=")] == [
        "HOSTNAME=h2",
        "HOSTNAME=h1",
    ]


@pytest.mark.usefixtures("no_monitoring_core", "disable_debug")
def test_corrupted_bulk_notification_is_dropped(tmp_path: Path) -> None:
    _install_plugin(_TEST_PLUGIN, tmp_path)
    _store_bulk_notification(tmp_path / "bulk", "h1", {})
    (tmp_path / "bulk" / "harry" / _TEST_PLUGIN / "60,10" / str(uuid.uuid4())).write_text("{{")

    _send_bulk(tmp_path / "bulk")

    (call,) = _bulk_calls(tmp_path)
    assert [line for line in call if line.startswith("HOSTNAME=")] == ["HOSTNAME=h1"]


def test_bulk_for_unknown_plugin_cannot_be_sent() -> None:
    with pytest.raises(MKGeneralException):
        notify.call_bulk_notification_script(
            CustomPluginName("no_such_plugin"), [], plugin_timeout=10
        )


def test_bulk_script_result_is_returned(tmp_path: Path) -> None:
    _install_plugin(_TEST_PLUGIN, tmp_path, exit_code=1)

    assert notify.call_bulk_notification_script(_TEST_PLUGIN, ["A=1\n"], plugin_timeout=10) == (
        1,
        ["some output"],
    )


@pytest.mark.usefixtures("release_locks")
def test_backlog_is_replayed_newest_first() -> None:
    for nr in range(3):
        notify.store_notification_backlog(
            EventContext({"HOSTNAME": HostName(f"h{nr}")}), backlog_size=2
        )

    assert [notify.raw_context_from_backlog(nr).get("HOSTNAME") for nr in range(2)] == [
        "h2",
        "h1",
    ]


@pytest.mark.usefixtures("release_locks")
def test_backlog_is_limited_to_its_size() -> None:
    for nr in range(3):
        notify.store_notification_backlog(
            EventContext({"HOSTNAME": HostName(f"h{nr}")}), backlog_size=2
        )

    with pytest.raises(SystemExit) as exc:
        notify.raw_context_from_backlog(2)

    assert exc.value.code == 2


@pytest.mark.usefixtures("release_locks")
def test_disabled_backlog_is_removed() -> None:
    notify.store_notification_backlog(EventContext({"HOSTNAME": HostName("h")}), backlog_size=2)

    notify.store_notification_backlog(EventContext({"HOSTNAME": HostName("h")}), backlog_size=0)

    assert not (notify.notification_logdir / "backlog.mk").exists()
