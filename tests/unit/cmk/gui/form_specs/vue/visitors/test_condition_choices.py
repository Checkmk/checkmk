#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from dataclasses import asdict

from cmk.gui.form_specs.private import ConditionChoices
from cmk.gui.form_specs.vue.shared_type_defs import (
    Condition,
    ConditionChoicesValue,
    ConditionGroup,
    Eq,
    Ne,
    Nor,
    Or,
)
from cmk.gui.form_specs.vue.visitors import DataOrigin, get_visitor
from cmk.gui.form_specs.vue.visitors._type_defs import VisitorOptions

from cmk.rulesets.v1 import Label

CONDITION_CHOICES_FS = ConditionChoices(
    add_condition_label=Label("add"),
    add_condition_group_label=Label("add"),
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
)


def test_tags_from_disk() -> None:
    disk_tags = {
        "address_family": {"$nor": ["ip-v6-only", "ip-v4-only"]},
        "agent": {"$or": ["all-agents"]},
        "ip-v4": {"$ne": "ip-v4"},
        "ip-v6": "ip-v6",
    }
    disk_visitor = get_visitor(CONDITION_CHOICES_FS, VisitorOptions(data_origin=DataOrigin.DISK))
    _, frontend_tags = disk_visitor.to_vue(disk_tags)

    assert frontend_tags == [
        ConditionChoicesValue(
            group_name="address_family", value=Nor(nor=["ip-v6-only", "ip-v4-only"])
        ),
        ConditionChoicesValue(group_name="agent", value=Or(or_=["all-agents"])),
        ConditionChoicesValue(group_name="ip-v4", value=Ne(ne="ip-v4")),
        ConditionChoicesValue(group_name="ip-v6", value=Eq(eq="ip-v6")),
    ]


def test_tags_from_frontend() -> None:
    frontend_tags = [
        asdict(
            ConditionChoicesValue(
                group_name="address_family", value=Nor(nor=["ip-v6-only", "ip-v4-only"])
            )
        ),
        asdict(ConditionChoicesValue(group_name="agent", value=Or(or_=["all-agents"]))),
        asdict(ConditionChoicesValue(group_name="ip-v4", value=Ne(ne="ip-v4"))),
        asdict(ConditionChoicesValue(group_name="ip-v6", value=Eq(eq="ip-v6"))),
    ]
    disk_visitor = get_visitor(
        CONDITION_CHOICES_FS, VisitorOptions(data_origin=DataOrigin.FRONTEND)
    )
    disk_tags = disk_visitor.to_disk(frontend_tags)

    assert disk_tags == {
        "address_family": {"$nor": ["ip-v6-only", "ip-v4-only"]},
        "agent": {"$or": ["all-agents"]},
        "ip-v4": {"$ne": "ip-v4"},
        "ip-v6": "ip-v6",
    }
