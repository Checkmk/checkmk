#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Literal

import pytest

from cmk.gui.monitor.services._api._filters import (
    parse_as_livestatus_filter,
    ServiceAndNode,
    ServiceBooleanCondition,
    ServiceNotNode,
    ServiceOrNode,
    ServiceStateChoiceCondition,
    ServiceStringCondition,
    ServiceStringOp,
)


@pytest.mark.parametrize(
    "op, ls_op",
    [
        ("contains", "~~"),
        ("matches", "~"),
    ],
)
def test_query_builder_string_condition(op: ServiceStringOp, ls_op: str) -> None:
    condition = ServiceStringCondition(type="condition", field="name", op=op, value="CPU")
    assert parse_as_livestatus_filter(condition) == f"Filter: description {ls_op} CPU"


@pytest.mark.parametrize(
    "public, private",
    [
        ("name", "description"),
        ("summary", "plugin_output"),
    ],
)
def test_query_builder_string_fields_are_properly_overriden(
    public: Literal["name", "summary"],
    private: str,
) -> None:
    condition = ServiceStringCondition(type="condition", field=public, op="contains", value="CPU")
    assert parse_as_livestatus_filter(condition) == f"Filter: {private} ~~ CPU"


@pytest.mark.parametrize(
    "field",
    ["acknowledged", "notifications_enabled", "is_flapping"],
)
@pytest.mark.parametrize(
    "value, ls_value",
    [
        (True, 1),
        (False, 0),
    ],
)
def test_query_builder_boolean_condition_fields(
    field: Literal["acknowledged", "notifications_enabled", "is_flapping"],
    value: bool,
    ls_value: int,
) -> None:
    condition = ServiceBooleanCondition(type="condition", field=field, op="eq", value=value)
    assert parse_as_livestatus_filter(condition) == f"Filter: {field} = {ls_value}"


@pytest.mark.parametrize(
    "value, expected",
    [
        (True, "Filter: scheduled_downtime_depth > 0"),
        (False, "Filter: scheduled_downtime_depth = 0"),
    ],
)
def test_query_builder_downtime_condition(value: bool, expected: str) -> None:
    condition = ServiceBooleanCondition(type="condition", field="in_downtime", op="eq", value=value)
    assert parse_as_livestatus_filter(condition) == expected


def test_query_builder_state_choice_single_no_or() -> None:
    condition = ServiceStateChoiceCondition(
        type="condition", field="state", op="one_of", value=["WARN"]
    )
    assert parse_as_livestatus_filter(condition) == "Filter: state = 1"


def test_query_builder_state_choice_multiple_with_or() -> None:
    condition = ServiceStateChoiceCondition(
        type="condition",
        field="state",
        op="one_of",
        value=["WARN", "CRIT"],
    )

    value = parse_as_livestatus_filter(condition)
    expected = "\n".join(  # noqa: FLY002
        [
            "Filter: state = 1",
            "Filter: state = 2",
            "Or: 2",
        ]
    )

    assert value == expected


def test_query_builder_nested_conditions() -> None:
    nodes = ServiceAndNode(
        type="and",
        children=[
            ServiceStateChoiceCondition(
                type="condition", field="state", op="one_of", value=["WARN"]
            ),
            ServiceNotNode(
                type="not",
                child=ServiceOrNode(
                    type="or",
                    children=[
                        ServiceStateChoiceCondition(
                            type="condition", field="state", op="one_of", value=["OK"]
                        ),
                        ServiceStateChoiceCondition(
                            type="condition", field="state", op="one_of", value=["UNKNOWN"]
                        ),
                    ],
                ),
            ),
        ],
    )

    value = parse_as_livestatus_filter(nodes)
    expected = "Filter: state = 1\nFilter: state = 0\nFilter: state = 3\nOr: 2\nNegate:\nAnd: 2"

    assert value == expected


def test_query_builder_mixed_string_and_state_conditions() -> None:
    nodes = ServiceAndNode(
        type="and",
        children=[
            ServiceStringCondition(type="condition", field="name", op="contains", value="CPU"),
            ServiceStateChoiceCondition(
                type="condition", field="state", op="one_of", value=["WARN"]
            ),
        ],
    )

    value = parse_as_livestatus_filter(nodes)
    expected = "Filter: description ~~ CPU\nFilter: state = 1\nAnd: 2"

    assert value == expected


def test_query_builder_combines_multiple_boolean_conditions() -> None:
    nodes = ServiceAndNode(
        type="and",
        children=[
            ServiceBooleanCondition(type="condition", field="acknowledged", op="eq", value=False),
            ServiceBooleanCondition(type="condition", field="in_downtime", op="eq", value=False),
        ],
    )

    value = parse_as_livestatus_filter(nodes)
    expected = "Filter: acknowledged = 0\nFilter: scheduled_downtime_depth = 0\nAnd: 2"

    assert value == expected
