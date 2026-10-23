#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Literal

import pytest
from pytest_mock import MockerFixture

from cmk.events.notify_types import (
    AlwaysBulkParameters,
    EventRule,
    NotificationParameterID,
    NotificationRuleID,
    NotifyBulkType,
    TimeperiodBulkParameters,
)
from cmk.gui.wato.pages.notifications.migrate import (
    migrate_to_event_rule,
    migrate_to_notification_quick_setup_spec,
)
from cmk.gui.wato.pages.notifications.quick_setup import validate_at_least_one_event
from cmk.gui.wato.pages.notifications.quick_setup_types import (
    Method,
    NotificationQuickSetupSpec,
    SpecificEvents,
    TriggeringEvents,
)
from cmk.ruleset_matcher.tags import TagGroupID, TagID
from cmk.utils.timeperiod import TimeperiodName
from tests.unit.cmk.gui.helpers.notification_rule_test_helper import mail_rule


def set_specific_triggering_events(
    trigger_events: set[Literal["host", "service", "ec"]],
) -> TriggeringEvents:
    specific_events = SpecificEvents()
    if "host" in trigger_events:
        specific_events["host_events"] = [
            ("state_change", (-1, 0)),
            ("state_change", (1, 2)),
            ("flapping_state", None),
            ("acknowledgement", None),
            ("alert_handler", "failure"),
        ]
    if "service" in trigger_events:
        specific_events["service_events"] = [
            ("state_change", (-1, 0)),
            ("state_change", (1, 2)),
            ("state_change", (3, 0)),
            ("downtime", None),
            ("alert_handler", "success"),
        ]
    if "ec" in trigger_events:
        specific_events["ec_alerts"] = True

    return ("specific_events", specific_events)


def set_quick_setup_params(triggering_events: TriggeringEvents) -> NotificationQuickSetupSpec:
    quick_setup_params: NotificationQuickSetupSpec = {
        "triggering_events": triggering_events,
        "host_filters": {
            "match_host_groups": ["group1", "group2", "group3"],
        },
        "service_filters": {
            "service_labels": {"label1": "value1", "label2": "value2"},
            "match_service_groups": ["group1", "group2", "group3"],
            "match_service_groups_regex": ("match_alias", [".*"]),
            "exclude_service_groups": ["group4", "group5", "group6"],
            "exclude_service_groups_regex": ("match_id", ["my_id_regex$"]),
            "match_services": ["service1", "service2", "service3"],
            "exclude_services": ["service4", "service5", "service6"],
            "check_type_plugin": ["check_mk", "local"],
        },
        "assignee_filters": {
            "contact_groups": ["cg1", "cg2", "cg3"],
            "users": ["admin_user", "guest_user", "monitoring_user"],
        },
        "general_filters": {
            "service_level": ("range", (0, 100)),
            "folder": "test",
            "sites": ["heute"],
        },
        "ec_alert_filters": {
            "rule_ids": ["foo", "bar"],
            "syslog_priority": (1, 2),
            "syslog_facility": 3,
            "event_comment": "foobar",
        },
        "notification_method": {
            "notification_effect": (
                "send",
                (
                    "mail",
                    Method(
                        parameter_id=NotificationParameterID("61736d07-326a-4fb9-affd-201e3bd2a637")
                    ),
                ),
            ),
        },
        "recipient": {
            "receive": [
                ("all_contacts_affected", None),
                ("all_email_users", None),
                ("all_users", None),
                ("contact_group", ["cg1", "cg2", "cg3"]),
                ("explicit_email_addresses", ["email1@checkmk.com", "email2@checkmk.com"]),
                ("specific_users", ["admin_user", "guest_user", "monitoring_user"]),
            ],
            "restrict_previous": [
                ("contact_group", ["cg1"]),
                ("custom_macro", [("m1", "regex1"), ("m2", "regex2")]),
            ],
        },
        "sending_conditions": {
            "frequency_and_timing": {
                "restrict_timeperiod": TimeperiodName("24X7"),
                "limit_by_count": (2, 4),
                "throttle_periodic": (3, 5),
            },
            "content_based_filtering": {
                "by_plugin_output": "some_plugin_output",
                "custom_by_comment": "some_comment",
            },
        },
        "general_properties": {
            "description": "foo",
            "settings": {
                "disable_rule": None,
                "allow_users_to_disable": None,
            },
            "comment": "foo.comment",
            "documentation_url": "foo.com",
        },
    }
    return quick_setup_params


def get_expected_event_rule(
    trigger_events: set[Literal["host", "service", "ec"]],
) -> EventRule:
    event_rule: EventRule = EventRule(
        rule_id=NotificationRuleID("uuid4_rule_id"),
        notify_plugin=("mail", NotificationParameterID("61736d07-326a-4fb9-affd-201e3bd2a637")),
        match_escalation=(2, 4),
        match_escalation_throttle=(3, 5),
        match_timeperiod=TimeperiodName("24X7"),
        match_plugin_output="some_plugin_output",
        match_notification_comment="some_comment",
        match_contactgroups=["cg1", "cg2", "cg3"],
        match_contacts=["admin_user", "guest_user", "monitoring_user"],
        match_folder="test",
        match_hostgroups=["group1", "group2", "group3"],
        match_site=["heute"],
        match_sl=(0, 100),
        contact_all=True,
        contact_all_with_email=True,
        contact_object=True,
        contact_groups=["cg1", "cg2", "cg3"],
        contact_emails=["email1@checkmk.com", "email2@checkmk.com"],
        contact_match_groups=["cg1"],
        contact_match_macros=[("m1", "regex1"), ("m2", "regex2")],
        contact_users=["admin_user", "guest_user", "monitoring_user"],
        disabled=True,
        allow_disable=True,
        description="foo",
        docu_url="foo.com",
        comment="foo.comment",
    )

    if "ec" in trigger_events:
        event_rule["match_ec"] = {
            "match_rule_id": ["foo", "bar"],
            "match_priority": (1, 2),
            "match_facility": 3,
            "match_comment": "foobar",
        }

    if "service" in trigger_events:
        event_rule["match_servicelabels"] = {"label1": "value1", "label2": "value2"}
        event_rule["match_servicegroups"] = ["group1", "group2", "group3"]
        event_rule["match_servicegroups_regex"] = ("match_alias", [".*"])
        event_rule["match_exclude_servicegroups"] = ["group4", "group5", "group6"]
        event_rule["match_exclude_servicegroups_regex"] = ("match_id", ["my_id_regex$"])
        event_rule["match_services"] = ["service1", "service2", "service3"]
        event_rule["match_exclude_services"] = ["service4", "service5", "service6"]
        event_rule["match_service_event"] = ["?r", "wc", "ur", "s", "as"]
        event_rule["match_checktype"] = ["check_mk", "local"]

    if "host" in trigger_events:
        event_rule["match_host_event"] = ["?r", "du", "f", "x", "af"]

    return event_rule


def _prepare_triggering_events(
    trigger_events: set[Literal["host", "service", "ec"]],
) -> tuple[NotificationQuickSetupSpec, EventRule]:
    quick_setup_params = set_quick_setup_params(
        set_specific_triggering_events(trigger_events=trigger_events)
    )
    expected_event_rule = get_expected_event_rule(trigger_events=trigger_events)
    return quick_setup_params, expected_event_rule


@pytest.mark.parametrize(
    "trigger_events",
    [
        {"host", "service", "ec"},
        {"host", "service"},
        {"host", "ec"},
        {"service", "ec"},
        {"host"},
        {"service"},
        {"ec"},
    ],
)
def test_triggering_events(
    mocker: MockerFixture,
    trigger_events: set[Literal["host", "service", "ec"]],
) -> None:
    mocker.patch("cmk.gui.wato.pages.notifications.migrate.uuid4", return_value="uuid4_rule_id")
    quick_setup_params, event_rule = _prepare_triggering_events(trigger_events=trigger_events)
    assert migrate_to_event_rule(quick_setup_params) == event_rule


def test_quick_setup_notifications_transform_to_frontend() -> None:
    quick_setup_params, event_rule = _prepare_triggering_events(
        trigger_events={"host", "service", "ec"}
    )
    assert migrate_to_notification_quick_setup_spec(event_rule) == quick_setup_params


def _do_not_match_ec_alerts_event_rule() -> EventRule:
    return EventRule(
        rule_id=NotificationRuleID("uuid4_rule_id"),
        allow_disable=False,
        contact_all=False,
        contact_all_with_email=False,
        contact_object=False,
        description="foo",
        disabled=False,
        notify_plugin=("mail", NotificationParameterID("parameter_id")),
        match_ec=False,
    )


def test_do_not_match_ec_alerts_is_editable_in_quick_setup() -> None:
    triggering_events = migrate_to_notification_quick_setup_spec(
        _do_not_match_ec_alerts_event_rule()
    )["triggering_events"]

    assert triggering_events[0] == "specific_events"
    specific_events = triggering_events[1]
    assert specific_events == {
        "host_events": [
            ("state_change", (-1, 0)),
            ("state_change", (-1, 1)),
            ("state_change", (-1, 2)),
            ("flapping_state", None),
            ("downtime", None),
            ("acknowledgement", None),
            ("alert_handler", "success"),
            ("alert_handler", "failure"),
        ],
        "service_events": [
            ("state_change", (-1, 0)),
            ("state_change", (-1, 1)),
            ("state_change", (-1, 2)),
            ("state_change", (-1, 3)),
            ("flapping_state", None),
            ("downtime", None),
            ("acknowledgement", None),
            ("alert_handler", "success"),
            ("alert_handler", "failure"),
        ],
    }
    validate_at_least_one_event(specific_events)


def test_do_not_match_ec_alerts_keeps_excluding_ec_alerts_after_a_round_trip(
    mocker: MockerFixture,
) -> None:
    mocker.patch("cmk.gui.wato.pages.notifications.migrate.uuid4", return_value="uuid4_rule_id")
    quick_setup_params = set_quick_setup_params(
        migrate_to_notification_quick_setup_spec(_do_not_match_ec_alerts_event_rule())[
            "triggering_events"
        ]
    )

    event_rule = migrate_to_event_rule(quick_setup_params)

    assert "match_ec" not in event_rule
    assert event_rule["match_host_event"] == ["?r", "?d", "?u", "f", "s", "x", "as", "af"]
    assert event_rule["match_service_event"] == [
        "?r",
        "?w",
        "?c",
        "?u",
        "f",
        "s",
        "x",
        "as",
        "af",
    ]


_ALWAYS_BULK = AlwaysBulkParameters(
    interval=60,
    count=1000,
    groupby=["host", "state"],
    groupby_custom=["MY_MACRO"],
    bulk_subject="Bulk subject",
)


_TIMEPERIOD_BULK_WITH_OUTSIDE = TimeperiodBulkParameters(
    timeperiod=TimeperiodName("workhours"),
    count=10,
    groupby=["folder"],
    groupby_custom=["OTHER_MACRO"],
    bulk_subject="Period subject",
    bulk_outside=_ALWAYS_BULK,
)
_MINIMAL_TIMEPERIOD_BULK = TimeperiodBulkParameters(
    timeperiod=TimeperiodName("workhours"), count=10, groupby=[]
)


@pytest.mark.parametrize(
    "bulk",
    [
        pytest.param(("always", _ALWAYS_BULK), id="always"),
        pytest.param(("timeperiod", _TIMEPERIOD_BULK_WITH_OUTSIDE), id="timeperiod-with-outside"),
        pytest.param(("timeperiod", _MINIMAL_TIMEPERIOD_BULK), id="timeperiod-minimal"),
    ],
)
def test_bulk_settings_survive_a_round_trip(bulk: NotifyBulkType) -> None:
    rule = mail_rule("plain")
    rule["bulk"] = bulk

    assert migrate_to_event_rule(migrate_to_notification_quick_setup_spec(rule))["bulk"] == bulk


def test_bulk_settings_are_dropped_for_cancelling_rules() -> None:
    rule = mail_rule("plain")
    rule["notify_plugin"] = ("mail", None)
    rule["bulk"] = ("always", _ALWAYS_BULK)

    effect = migrate_to_notification_quick_setup_spec(rule)["notification_method"]

    assert effect == {"notification_effect": ("suppress", ("mail", None))}


def test_host_filters_survive_a_round_trip() -> None:
    rule = mail_rule("plain")
    rule["match_hosttags"] = {TagGroupID("criticality"): TagID("prod")}
    rule["match_hostlabels"] = {"os": "linux"}
    rule["match_hosts"] = ["host1"]
    rule["match_exclude_hosts"] = ["host2"]

    round_tripped = migrate_to_event_rule(migrate_to_notification_quick_setup_spec(rule))

    assert round_tripped.get("match_hosttags") == {TagGroupID("criticality"): TagID("prod")}
    assert round_tripped.get("match_hostlabels") == {"os": "linux"}
    assert round_tripped.get("match_hosts") == ["host1"]
    assert round_tripped.get("match_exclude_hosts") == ["host2"]


def test_explicit_service_level_survives_a_round_trip() -> None:
    rule = mail_rule("plain")
    rule["match_sl"] = (10, 10)

    spec = migrate_to_notification_quick_setup_spec(rule)

    assert spec["general_filters"].get("service_level") == ("explicit", 10)
    assert migrate_to_event_rule(spec).get("match_sl") == (10, 10)


def test_rule_for_all_events_sets_no_event_conditions() -> None:
    event_rule = migrate_to_event_rule(set_quick_setup_params(("all_events", None)))

    assert "match_host_event" not in event_rule
    assert "match_service_event" not in event_rule
