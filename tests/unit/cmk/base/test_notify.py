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
from cmk.events.event_context import EnrichedEventContext, EventContext, HostName
from cmk.utils.http_proxy_config import EnvironmentProxyConfig
from cmk.utils.notify_types import (
    Contact,
    ContactName,
    CustomPluginName,
    EventRule,
    NotificationContext,
    NotificationParameterGeneralInfos,
    NotificationParameterID,
    NotificationParameterSpecs,
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
    monkeypatch.setattr(notify, "is_timeperiod_active", lambda **kwargs: is_active)
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
    assert notify._rbn_match_contact_macros(rule, contactname, contact) == expected


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
    assert notify._rbn_match_contact_groups(rule, contactname, contact) == expected


def test__rbn_match_rule_disabled_rule() -> None:
    assert (
        notify._rbn_match_rule(
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
        notify._rbn_match_rule(
            _make_rule(),
            EnrichedEventContext({"WHAT": "HOST", "HOSTNAME": HostName("testhost")}),
            {},
            define_servicegroups={},
            analyse=False,
            timeperiods_active={},
        )
        is None
    )


def test_create_notifications_custom_script_with_call_parameters() -> None:
    """Regression test custom notification scripts with
    'Call with the following parameters'"""
    rule: EventRule = {
        "rule_id": NotificationRuleID("test_custom"),
        "allow_disable": False,
        "contact_all": False,
        "contact_all_with_email": False,
        "contact_object": False,
        "description": "Custom script rule",
        "disabled": False,
        # In user notification rules with custom scripts and "Call with the following
        # parameters", the plugin_parameter_id is a list of strings, not a
        # NotificationParameterID string.
        "notify_plugin": ("my_custom_script", ["param1", "param2"]),  # type: ignore[typeddict-item]
        "contact_users": ["testuser"],
    }
    config_contacts = {
        ContactName("testuser"): Contact({"email": "test@example.com"}),
    }
    notifications, _rule_info = notify._create_notifications(
        enriched_context=EnrichedEventContext({"HOSTNAME": HostName("testhost"), "WHAT": "HOST"}),
        rule=rule,
        parameters={},
        notifications={},
        rule_info=[],
        host_parameters_cb=lambda _host, _plugin: {},
        config_contacts=config_contacts,
        fallback_email="",
        rule_nr=0,
        timeperiods_active={},
    )
    # Should create exactly one notification without raising ValueError
    assert len(notifications) == 1
    _locked, final_params, _bulk = next(iter(notifications.values()))
    assert final_params["params"] == ["param1", "param2"]  # type: ignore[typeddict-item]


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


def _count_contact_occurrences(notifications: notify.Notifications, contact: ContactName) -> int:
    """Count how many notification entries contain a given contact."""
    count = 0
    for contacts_set, _plugin in notifications:
        if contact in contacts_set:
            count += 1
    return count


def test_cancellation_removes_contacts() -> None:
    """A cancel rule removes contacts from an existing notification entry."""
    config_contacts = {
        ContactName("userX"): Contact({"email": "x@example.com"}),
        ContactName("userY"): Contact({"email": "y@example.com"}),
    }
    enriched_context = EnrichedEventContext({"HOSTNAME": HostName("testhost"), "WHAT": "HOST"})

    notifications, rule_info = notify._create_notifications(
        enriched_context=enriched_context,
        rule=_make_add_rule(contact_users=["userX", "userY"]),
        parameters=_TEST_PARAMETERS,
        notifications={},
        rule_info=[],
        host_parameters_cb=lambda _host, _plugin: {},
        config_contacts=config_contacts,
        fallback_email="",
        rule_nr=0,
        timeperiods_active={},
    )
    assert len(notifications) == 1

    notifications, rule_info = notify._create_notifications(
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

    notifications, rule_info = notify._create_notifications(
        enriched_context=enriched_context,
        rule=_make_add_rule(contact_users=["userX"]),
        parameters=_TEST_PARAMETERS,
        notifications={},
        rule_info=[],
        host_parameters_cb=lambda _host, _plugin: {},
        config_contacts=config_contacts,
        fallback_email="",
        rule_nr=0,
        timeperiods_active={},
    )
    assert len(notifications) == 1

    notifications, rule_info = notify._create_notifications(
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

    notifications, rule_info = notify._create_notifications(
        enriched_context=enriched_context,
        rule=_make_add_rule(allow_disable=False, contact_users=["userX"]),
        parameters=_TEST_PARAMETERS,
        notifications={},
        rule_info=[],
        host_parameters_cb=lambda _host, _plugin: {},
        config_contacts=config_contacts,
        fallback_email="",
        rule_nr=0,
        timeperiods_active={},
    )
    assert len(notifications) == 1

    notifications, rule_info = notify._create_notifications(
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

    notifications, rule_info = notify._create_notifications(
        enriched_context=enriched_context,
        rule=_make_add_rule(contact_users=["userX"], plugin=plugin_a),
        parameters=parameters,
        notifications={},
        rule_info=[],
        host_parameters_cb=lambda _host, _plugin: {},
        config_contacts=config_contacts,
        fallback_email="",
        rule_nr=0,
        timeperiods_active={},
    )
    notifications, rule_info = notify._create_notifications(
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


def test__rbn_match_rule_escalation_blocked() -> None:
    assert (
        notify._rbn_match_rule(
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
