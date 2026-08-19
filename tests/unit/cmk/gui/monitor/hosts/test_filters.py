#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Literal

import pytest
from pydantic import TypeAdapter, ValidationError

from cmk.ccc.site import SiteId
from cmk.gui.monitor.hosts._api._filters import (
    AndNode,
    BooleanCondition,
    extract_site_scope,
    FilterNode,
    FolderCondition,
    NotNode,
    NumericCondition,
    NumericOp,
    OrNode,
    parse_as_livestatus_filter,
    SiteChoiceCondition,
    StateChoiceCondition,
    StringCondition,
    StringOp,
    TimestampCondition,
    TimestampOp,
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


def test_query_builder_folder_condition() -> None:
    condition = FolderCondition(type="condition", field="folder", op="contains", value="network")
    assert (
        parse_as_livestatus_filter(condition)
        == r"Filter: filename ~~ ^/wato/.*network.*/hosts\.mk$"
    )


def test_query_builder_folder_condition_counts_as_a_single_child() -> None:
    """A folder condition may need several filters, which must not skew the and/or counts."""
    nodes = AndNode(
        type="and",
        children=[
            StringCondition(type="condition", field="name", op="contains", value="heute"),
            # Every Setup folder contains a slash, so a negated "/" selects the hosts that have
            # no folder at all: the ones not managed via Setup.
            NotNode(
                type="not",
                child=FolderCondition(type="condition", field="folder", op="contains", value="/"),
            ),
        ],
    )

    expected = "\n".join(  # noqa: FLY002
        [
            "Filter: name ~~ heute",
            r"Filter: filename ~~ ^/wato/.*/.*/hosts\.mk$",
            r"Filter: filename ~~ ^/wato/.*/hosts\.mk$",
            "Filter: filename = /wato/hosts.mk",
            "Or: 3",
            "Negate:",
            "And: 2",
        ]
    )

    assert parse_as_livestatus_filter(nodes) == expected


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
    assert parse_as_livestatus_filter(condition) == "Filter: state = 1"


def test_query_builder_state_choice_multiple_with_or() -> None:
    condition = StateChoiceCondition(
        type="condition",
        field="state",
        op="one_of",
        value=["DOWN", "UNREACHABLE"],
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


# `@api_model` classes are plain dataclasses: constructing one directly (as these tests do) never
# runs the pydantic converters (e.g. `SiteIdConverter.should_exist`) that only fire when a request
# body is actually parsed - see the openapi-level `test_filters_validation_errors` for that. So this
# doesn't need to be a real configured site, and `all_site_ids` below is free to include others.
_SITE_ID = SiteId("NO_SITE")


def test_extract_site_scope_bare_condition() -> None:
    condition = SiteChoiceCondition(
        type="condition",
        field="site_id",
        op="one_of",
        value=[_SITE_ID],
    )

    residual, site_ids = extract_site_scope(condition, frozenset({_SITE_ID, SiteId("other")}))

    assert residual is None
    assert site_ids == [_SITE_ID]


def test_extract_site_scope_negated_condition_is_a_complement() -> None:
    node = NotNode(
        type="not",
        child=SiteChoiceCondition(
            type="condition",
            field="site_id",
            op="one_of",
            value=[_SITE_ID],
        ),
    )

    residual, site_ids = extract_site_scope(node, frozenset({_SITE_ID, SiteId("other")}))

    assert residual is None
    assert site_ids == [SiteId("other")]


def test_extract_site_scope_negating_every_site_yields_empty_set() -> None:
    node = NotNode(
        type="not",
        child=SiteChoiceCondition(
            type="condition",
            field="site_id",
            op="one_of",
            value=[_SITE_ID],
        ),
    )

    _, site_ids = extract_site_scope(node, frozenset({_SITE_ID}))

    assert site_ids == []


def test_extract_site_scope_and_combined_with_unrelated_condition() -> None:
    node = AndNode(
        type="and",
        children=[
            SiteChoiceCondition(
                type="condition",
                field="site_id",
                op="one_of",
                value=[_SITE_ID],
            ),
            StringCondition(type="condition", field="name", op="contains", value="heute"),
        ],
    )

    residual, site_ids = extract_site_scope(node, frozenset({_SITE_ID}))

    assert residual == StringCondition(type="condition", field="name", op="contains", value="heute")
    assert site_ids == [_SITE_ID]


def test_extract_site_scope_at_various_and_nesting_depths() -> None:
    node = AndNode(
        type="and",
        children=[
            AndNode(
                type="and",
                children=[
                    SiteChoiceCondition(
                        type="condition",
                        field="site_id",
                        op="one_of",
                        value=[_SITE_ID],
                    ),
                    StringCondition(type="condition", field="name", op="contains", value="heute"),
                ],
            ),
            NumericCondition(type="condition", field="num_services", op="gt", value=0),
        ],
    )

    residual, site_ids = extract_site_scope(node, frozenset({_SITE_ID}))

    assert residual == AndNode(
        type="and",
        children=[
            StringCondition(type="condition", field="name", op="contains", value="heute"),
            NumericCondition(type="condition", field="num_services", op="gt", value=0),
        ],
    )
    assert site_ids == [_SITE_ID]


def test_extract_site_scope_leaves_a_site_free_tree_unaffected() -> None:
    node = AndNode(
        type="and",
        children=[
            StringCondition(type="condition", field="name", op="contains", value="heute"),
            NumericCondition(type="condition", field="num_services", op="gt", value=0),
        ],
    )

    residual, site_ids = extract_site_scope(node, frozenset({_SITE_ID}))

    assert residual == node
    assert site_ids is None


def test_extract_site_scope_rejects_a_second_site_condition() -> None:
    node = AndNode(
        type="and",
        children=[
            SiteChoiceCondition(
                type="condition",
                field="site_id",
                op="one_of",
                value=[_SITE_ID],
            ),
            SiteChoiceCondition(
                type="condition",
                field="site_id",
                op="one_of",
                value=[_SITE_ID],
            ),
        ],
    )

    with pytest.raises(ValueError, match="Only one"):
        extract_site_scope(node, frozenset({_SITE_ID}))


def test_extract_site_scope_rejects_nesting_under_or() -> None:
    node = OrNode(
        type="or",
        children=[
            SiteChoiceCondition(
                type="condition",
                field="site_id",
                op="one_of",
                value=[_SITE_ID],
            ),
            StringCondition(type="condition", field="name", op="contains", value="heute"),
        ],
    )

    with pytest.raises(ValueError, match="'or'"):
        extract_site_scope(node, frozenset({_SITE_ID}))


def test_extract_site_scope_rejects_negating_a_mixed_subtree() -> None:
    node = NotNode(
        type="not",
        child=AndNode(
            type="and",
            children=[
                SiteChoiceCondition(
                    type="condition",
                    field="site_id",
                    op="one_of",
                    value=[_SITE_ID],
                ),
                StringCondition(type="condition", field="name", op="contains", value="heute"),
            ],
        ),
    )

    with pytest.raises(ValueError, match="'or'"):
        extract_site_scope(node, frozenset({_SITE_ID}))


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
    op: TimestampOp,
    ls_op: str,
) -> None:
    condition = TimestampCondition(type="condition", field=field, op=op, value=1752405510)
    assert parse_as_livestatus_filter(condition) == f"Filter: {field} {ls_op} 1752405510"


def test_query_builder_timestamp_range() -> None:
    nodes = AndNode(
        type="and",
        children=[
            TimestampCondition(type="condition", field="last_check", op="gte", value=1752405510),
            TimestampCondition(type="condition", field="last_check", op="lte", value=1752491910),
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
        TypeAdapter(FilterNode).validate_python(  # astrein: disable=pydantic-type-adapter
            payload, strict=False
        )
