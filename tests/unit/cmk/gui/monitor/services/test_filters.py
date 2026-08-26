#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Literal

import pytest
from pydantic import TypeAdapter, ValidationError

from cmk.gui.monitor.services._api._filters import (
    parse_as_livestatus_filter,
    ServiceAndNode,
    ServiceBooleanCondition,
    ServiceFilterNode,
    ServiceLabelChoiceCondition,
    ServiceNameChoiceCondition,
    ServiceNotNode,
    ServiceOrNode,
    ServiceStateChoiceCondition,
    ServiceStringCondition,
    ServiceStringOp,
    ServiceTimestampCondition,
    ServiceTimestampOp,
)
from tests.testlib.gui.web_test_app import SetConfig


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


@pytest.mark.parametrize(
    "value, expected",
    [
        (True, "Filter: staleness >= 3.5"),
        (False, "Filter: staleness < 3.5"),
    ],
)
def test_query_builder_stale_condition(
    value: bool, expected: str, request_context: None, set_config: SetConfig
) -> None:
    condition = ServiceBooleanCondition(type="condition", field="stale", op="eq", value=value)
    with set_config(staleness_threshold=3.5):
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


def test_query_builder_label_choice_single_no_or() -> None:
    condition = ServiceLabelChoiceCondition(
        type="condition", field="labels", op="one_of", value=["cmk/os_family:linux"]
    )

    assert parse_as_livestatus_filter(condition) == "Filter: labels = 'cmk/os_family' 'linux'"


def test_query_builder_label_choice_multiple_with_or() -> None:
    condition = ServiceLabelChoiceCondition(
        type="condition",
        field="tags",
        op="one_of",
        value=["criticality:prod", "networking:core"],
    )

    expected = "\n".join(  # noqa: FLY002
        [
            "Filter: tags = 'criticality' 'prod'",
            "Filter: tags = 'networking' 'core'",
            "Or: 2",
        ]
    )

    assert parse_as_livestatus_filter(condition) == expected


def test_query_builder_label_choice_splits_on_the_first_colon_only() -> None:
    condition = ServiceLabelChoiceCondition(
        type="condition", field="labels", op="one_of", value=["url:https://example.com"]
    )

    assert parse_as_livestatus_filter(condition) == "Filter: labels = 'url' 'https://example.com'"


def test_query_builder_label_choice_value_prefix_matches_by_regex() -> None:
    condition = ServiceLabelChoiceCondition(
        type="condition", field="labels", op="one_of", value=["cmk/os_family:lin*"]
    )

    assert parse_as_livestatus_filter(condition) == "Filter: labels ~ 'cmk/os_family' '^lin'"


def test_query_builder_label_choice_key_prefix_matches_the_names_column() -> None:
    condition = ServiceLabelChoiceCondition(
        type="condition", field="labels", op="one_of", value=["cmk/os*"]
    )

    assert parse_as_livestatus_filter(condition) == "Filter: label_names ~ ^cmk/os"


def test_query_builder_tag_key_prefix_matches_its_own_names_column() -> None:
    condition = ServiceLabelChoiceCondition(
        type="condition", field="tags", op="one_of", value=["crit*"]
    )

    assert parse_as_livestatus_filter(condition) == "Filter: tag_names ~ ^crit"


def test_query_builder_label_choice_prefix_is_a_literal_not_a_pattern() -> None:
    condition = ServiceLabelChoiceCondition(
        type="condition", field="labels", op="one_of", value=["cmk/os_family:a.b*"]
    )

    assert parse_as_livestatus_filter(condition) == "Filter: labels ~ 'cmk/os_family' '^a\\.b'"


def test_query_builder_name_choice_single_no_or() -> None:
    condition = ServiceNameChoiceCondition(
        type="condition", field="contact_groups", op="one_of", value=["all"]
    )

    assert parse_as_livestatus_filter(condition) == "Filter: contact_groups >= all"


def test_query_builder_name_choice_multiple_with_or() -> None:
    condition = ServiceNameChoiceCondition(
        type="condition", field="contacts", op="one_of", value=["alice", "bob"]
    )

    expected = "\n".join(  # noqa: FLY002
        [
            "Filter: contacts >= alice",
            "Filter: contacts >= bob",
            "Or: 2",
        ]
    )

    assert parse_as_livestatus_filter(condition) == expected


def test_query_builder_name_choice_prefix_matches_by_regex() -> None:
    condition = ServiceNameChoiceCondition(
        type="condition", field="contact_groups", op="one_of", value=["ops*"]
    )

    assert parse_as_livestatus_filter(condition) == "Filter: contact_groups ~ ^ops"


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


@pytest.mark.parametrize(
    "op, ls_op",
    [
        ("lt", "<"),
        ("lte", "<="),
        ("gt", ">"),
        ("gte", ">="),
    ],
)
@pytest.mark.parametrize("field", ["last_check", "last_state_change"])
def test_query_builder_timestamp_condition(
    field: Literal["last_check", "last_state_change"],
    op: ServiceTimestampOp,
    ls_op: str,
) -> None:
    condition = ServiceTimestampCondition(type="condition", field=field, op=op, value=1752405510)
    assert parse_as_livestatus_filter(condition) == f"Filter: {field} {ls_op} 1752405510"


def test_query_builder_timestamp_range() -> None:
    nodes = ServiceAndNode(
        type="and",
        children=[
            ServiceTimestampCondition(
                type="condition", field="last_check", op="gte", value=1752405510
            ),
            ServiceTimestampCondition(
                type="condition", field="last_check", op="lte", value=1752491910
            ),
        ],
    )

    value = parse_as_livestatus_filter(nodes)
    expected = "Filter: last_check >= 1752405510\nFilter: last_check <= 1752491910\nAnd: 2"

    assert value == expected


@pytest.mark.parametrize(
    "value",
    [
        pytest.param("1752405510", id="numeric string"),
        pytest.param(1752405510.0, id="float"),
        pytest.param("2026-07-13T11:38:30Z", id="iso timestamp"),
        pytest.param(True, id="boolean"),
    ],
)
def test_timestamp_condition_only_accepts_unix_timestamps(value: object) -> None:
    payload = {"type": "condition", "field": "last_check", "op": "gte", "value": value}

    with pytest.raises(ValidationError):
        TypeAdapter(ServiceFilterNode).validate_python(  # astrein: disable=pydantic-type-adapter
            payload, strict=False
        )
