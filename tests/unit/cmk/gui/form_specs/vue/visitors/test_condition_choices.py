#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from dataclasses import asdict

from cmk.gui.form_specs.private import ConditionChoices, not_empty
from cmk.gui.form_specs.vue import get_visitor, RawDiskData, RawFrontendData

from cmk.rulesets.v1 import Label
from cmk.shared_typing.vue_formspec_components import (
    Condition,
    ConditionChoicesValue,
    ConditionGroup,
    Eq,
    Ne,
    Nor,
    Or,
    ValidationMessage,
)

CONDITION_CHOICES_FS = ConditionChoices(
    select_condition_group_to_add=Label("add"),
    add_condition_group_label=Label("add"),
    no_more_condition_groups_to_add=Label("no more"),
    get_conditions=lambda: {
        "address_family": ConditionGroup(
            title="foo",
            conditions=[
                Condition(name="ip-v4", title="ip-v4"),
                Condition(name="ip-v6", title="ip-v6"),
            ],
        ),
        "agent": ConditionGroup(
            title="bar",
            conditions=[Condition(name="all-agents", title="all-agents")],
        ),
        "ip-v4": ConditionGroup(
            title="baz",
            conditions=[Condition(name="ip-v4", title="ip-v4")],
        ),
        "ip-v6": ConditionGroup(
            title="qux",
            conditions=[Condition(name="ip-v6", title="ip-v6")],
        ),
    },
    custom_validate=[not_empty()],
)


def test_tags_from_disk() -> None:
    disk_tags = RawDiskData(
        {
            "address_family": {"$nor": ["ip-v6-only", "ip-v4-only"]},
            "agent": {"$or": ["all-agents"]},
            "ip-v4": {"$ne": "ip-v4"},
            "ip-v6": "ip-v6",
        }
    )
    disk_visitor = get_visitor(CONDITION_CHOICES_FS)
    _, frontend_tags = disk_visitor.to_vue(disk_tags)

    assert frontend_tags == [
        ConditionChoicesValue(
            group_name="address_family", value=Nor(oper_nor=["ip-v6-only", "ip-v4-only"])
        ),
        ConditionChoicesValue(group_name="agent", value=Or(oper_or=["all-agents"])),
        ConditionChoicesValue(group_name="ip-v4", value=Ne(oper_ne="ip-v4")),
        ConditionChoicesValue(group_name="ip-v6", value=Eq(oper_eq="ip-v6")),
    ]


def test_tags_from_frontend() -> None:
    frontend_tags = RawFrontendData(
        [
            asdict(
                ConditionChoicesValue(
                    group_name="address_family", value=Nor(oper_nor=["ip-v6-only", "ip-v4-only"])
                )
            ),
            asdict(ConditionChoicesValue(group_name="agent", value=Or(oper_or=["all-agents"]))),
            asdict(ConditionChoicesValue(group_name="ip-v4", value=Ne(oper_ne="ip-v4"))),
            asdict(ConditionChoicesValue(group_name="ip-v6", value=Eq(oper_eq="ip-v6"))),
        ]
    )
    disk_visitor = get_visitor(CONDITION_CHOICES_FS)
    disk_tags = disk_visitor.to_disk(frontend_tags)

    assert disk_tags == {
        "address_family": {"$nor": ["ip-v6-only", "ip-v4-only"]},
        "agent": {"$or": ["all-agents"]},
        "ip-v4": {"$ne": "ip-v4"},
        "ip-v6": "ip-v6",
    }


def test_non_empty_validation() -> None:
    visitor = get_visitor(CONDITION_CHOICES_FS)
    validation = visitor.validate(RawFrontendData([]))

    assert validation == [
        ValidationMessage(
            location=[],
            message="An empty value is not allowed here",
            replacement_value=[],
        ),
    ]
