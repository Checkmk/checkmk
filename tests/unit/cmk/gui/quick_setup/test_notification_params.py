#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pytest_mock import MockerFixture

from cmk.utils.notify_types import EventRule, NotificationParameterID, NotificationRuleID

from cmk.gui.wato.pages.notifications.migrate import (
    migrate_to_event_rule,
    migrate_to_notification_quick_setup_spec,
)
from cmk.gui.wato.pages.notifications.quick_setup_types import (
    Method,
    NotificationQuickSetupSpec,
    SpecificEvents,
)

QUICK_SETUP_PARAMS: NotificationQuickSetupSpec = {
    "triggering_events": (
        "specific_events",
        SpecificEvents(
            host_events=[
                ("status_change", (-1, 0)),
                ("status_change", (1, 2)),
                ("flapping_state", None),
                ("acknowledgement", None),
                ("alert_handler", "failure"),
            ],
            service_events=[
                ("status_change", (-1, 0)),
                ("status_change", (1, 2)),
                ("status_change", (3, 0)),
                ("downtime", None),
                ("alert_handler", "success"),
            ],
            ec_alerts=True,
        ),
    ),
    "host_filters": {
        "match_host_groups": ["group1", "group2", "group3"],
    },
    "service_filters": {
        "match_service_groups": ["group1", "group2", "group3"],
        "exclude_service_groups": ["group4", "group5", "group6"],
        "match_services": ["service1", "service2", "service3"],
        "exclude_services": ["service4", "service5", "service6"],
    },
    "assignee_filters": {
        "contact_groups": ["cg1", "cg2", "cg3"],
        "users": ["admin_user", "guest_user", "monitoring_user"],
    },
    "general_filters": {
        "service_level": ("range", (0, 100)),
        "folder": "test",
        "sites": ["heute"],
        "check_type_plugin": ["check_mk", "local"],
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
            "restrict_timeperiod": "24X7",
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

EVENT_RULE_PARAMS: EventRule = EventRule(
    rule_id=NotificationRuleID("uuid4_rule_id"),
    match_host_event=["?r", "du", "f", "x", "af"],
    match_service_event=["?r", "wc", "ur", "s", "as"],
    notify_plugin=("mail", NotificationParameterID("61736d07-326a-4fb9-affd-201e3bd2a637")),
    match_escalation=(2, 4),
    match_escalation_throttle=(3, 5),
    match_timeperiod="24X7",
    match_plugin_output="some_plugin_output",
    match_notification_comment="some_comment",
    match_checktype=["check_mk", "local"],
    match_contactgroups=["cg1", "cg2", "cg3"],
    match_contacts=["admin_user", "guest_user", "monitoring_user"],
    match_exclude_servicegroups=["group4", "group5", "group6"],
    match_exclude_services=["service4", "service5", "service6"],
    match_folder="test",
    match_hostgroups=["group1", "group2", "group3"],
    match_servicegroups=["group1", "group2", "group3"],
    match_services=["service1", "service2", "service3"],
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
    match_ec={
        "match_rule_id": ["foo", "bar"],
        "match_priority": (1, 2),
        "match_facility": 3,
        "match_comment": "foobar",
    },
    disabled=True,
    allow_disable=True,
    description="foo",
    docu_url="foo.com",
    comment="foo.comment",
)


def test_quick_setup_notifications_transform_to_disk(mocker: MockerFixture) -> None:
    mocker.patch("cmk.gui.wato.pages.notifications.migrate.uuid4", return_value="uuid4_rule_id")
    assert migrate_to_event_rule(QUICK_SETUP_PARAMS) == EVENT_RULE_PARAMS


def test_quick_setup_notifications_transform_to_frontend() -> None:
    assert migrate_to_notification_quick_setup_spec(EVENT_RULE_PARAMS) == QUICK_SETUP_PARAMS
