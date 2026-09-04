#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.monitor.hosts._api._filters import (
    AndNode,
    BooleanCondition,
    NotNode,
    NumericCondition,
    NumericOp,
    OrNode,
    parse_as_livestatus_filter,
    StateChoiceCondition,
    StringCondition,
    StringOp,
)


def test_query_builder_nested_conditions_and_nodes() -> None:
    nodes = AndNode(
        type="and",
        children=[
            StringCondition(type="condition", field="name", op="contains", value="heute"),
            OrNode(
                type="or",
                children=[
                    StringCondition(type="condition", field="name", op="matches", value="gestern"),
                    NumericCondition(type="condition", field="num_services", op="eq", value=42),
                ],
            ),
            NotNode(
                type="not",
                child=OrNode(
                    type="or",
                    children=[
                        BooleanCondition(
                            type="condition", field="acknowledged", op="eq", value=True
                        ),
                        StringCondition(
                            type="condition", field="alias", op="matches", value="Zukunft"
                        ),
                    ],
                ),
            ),
        ],
    )

    value = parse_as_livestatus_filter(nodes)
    expected = (
        "Filter: name ~~ heute\n"
        "Filter: name ~ gestern\n"
        "Filter: num_services = 42\n"
        "Or: 2\n"
        "Filter: acknowledged = 1\n"
        "Filter: alias ~ Zukunft\n"
        "Or: 2\n"
        "Negate:\n"
        "And: 3"
    )

    assert value == expected


@pytest.mark.parametrize(
    "op, ls_op",
    [
        ("contains", "~~"),
        ("matches", "~"),
    ],
)
def test_query_builder_string_condition(op: StringOp, ls_op: str) -> None:
    condition = StringCondition(type="condition", field="name", op=op, value="heute")
    assert parse_as_livestatus_filter(condition) == f"Filter: name {ls_op} heute"


@pytest.mark.parametrize(
    "op, ls_op",
    [
        ("eq", "="),
        ("lt", "<"),
        ("lte", "<="),
        ("gt", ">"),
        ("gte", ">="),
    ],
)
def test_query_builder_numeric_condition(op: NumericOp, ls_op: str) -> None:
    condition = NumericCondition(type="condition", field="num_services", op=op, value=42)
    assert parse_as_livestatus_filter(condition) == f"Filter: num_services {ls_op} 42"


@pytest.mark.parametrize(
    "value, ls_value",
    [
        (True, 1),
        (False, 0),
    ],
)
def test_query_builder_boolean_condition(value: bool, ls_value: int) -> None:
    condition = BooleanCondition(type="condition", field="acknowledged", op="eq", value=value)
    assert parse_as_livestatus_filter(condition) == f"Filter: acknowledged = {ls_value}"


@pytest.mark.parametrize(
    "value, expected",
    [
        (True, "Filter: scheduled_downtime_depth > 0"),
        (False, "Filter: scheduled_downtime_depth = 0"),
    ],
)
def test_query_builder_downtime_condition(value: bool, expected: str) -> None:
    condition = BooleanCondition(type="condition", field="in_downtime", op="eq", value=value)
    assert parse_as_livestatus_filter(condition) == expected


def test_query_builder_state_choice_single_no_or() -> None:
    condition = StateChoiceCondition(type="condition", field="state", op="one_of", value=["DOWN"])
    value = parse_as_livestatus_filter(condition)
    expected = "\n".join(
        [
            "Filter: state = 1",
            "Filter: has_been_checked = 1",
            "And: 2",
        ]
    )

    assert value == expected


def test_query_builder_state_choice_multiple_with_or() -> None:
    condition = StateChoiceCondition(
        type="condition",
        field="state",
        op="one_of",
        value=["DOWN", "UNREACHABLE"],
    )

    value = parse_as_livestatus_filter(condition)
    expected = "\n".join(
        [
            "Filter: state = 1",
            "Filter: has_been_checked = 1",
            "And: 2",
            "Filter: state = 2",
            "Filter: has_been_checked = 1",
            "And: 2",
            "Or: 2",
        ]
    )

    assert value == expected


def test_query_builder_state_choice_pending_matches_has_been_checked_only() -> None:
    """A pending host's raw ``state`` column is meaningless, so 'PENDING' is not translated into a
    ``state = X`` filter at all - only into ``has_been_checked``."""
    condition = StateChoiceCondition(
        type="condition", field="state", op="one_of", value=["PENDING"]
    )

    assert parse_as_livestatus_filter(condition) == "Filter: has_been_checked = 0"


def test_query_builder_state_choice_mixes_pending_and_real_states() -> None:
    condition = StateChoiceCondition(
        type="condition", field="state", op="one_of", value=["UP", "PENDING"]
    )

    value = parse_as_livestatus_filter(condition)
    expected = "\n".join(
        [
            "Filter: state = 0",
            "Filter: has_been_checked = 1",
            "And: 2",
            "Filter: has_been_checked = 0",
            "Or: 2",
        ]
    )

    assert value == expected
