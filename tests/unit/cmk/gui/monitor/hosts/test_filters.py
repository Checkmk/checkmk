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
    LabelChoiceCondition,
    NameChoiceCondition,
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
from tests.testlib.gui.web_test_app import SetConfig


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


_TITLES = {"": "Main", "dc_muc": "Data center Munich", "network": "Netzwerk"}


def test_query_builder_folder_condition() -> None:
    condition = FolderCondition(
        type="condition", field="folder", op="contains", value="Data center"
    )
    assert (
        parse_as_livestatus_filter(condition, setup_folders=lambda: _TITLES)
        == "Filter: filename = /wato/dc_muc/hosts.mk"
    )


def test_query_builder_folder_condition_selects_nothing_without_a_matching_title() -> None:
    """Emitting no filter at all would select every host, so it says "no host" out loud."""
    condition = FolderCondition(type="condition", field="folder", op="contains", value="dc_muc")

    assert parse_as_livestatus_filter(condition, setup_folders=lambda: _TITLES) == "\n".join(  # noqa: FLY002
        [
            "Filter: state >= 0",
            "Negate:",
        ]
    )


def test_query_builder_folder_condition_counts_as_a_single_child() -> None:
    """A folder condition may need several filters, which must not skew the and/or counts."""
    nodes = AndNode(
        type="and",
        children=[
            StringCondition(type="condition", field="name", op="contains", value="heute"),
            # All three titles carry an "n", so negating it selects the hosts left over: those
            # in no folder Setup knows a title for.
            NotNode(
                type="not",
                child=FolderCondition(type="condition", field="folder", op="contains", value="n"),
            ),
        ],
    )

    expected = "\n".join(  # noqa: FLY002
        [
            "Filter: name ~~ heute",
            "Filter: filename = /wato/hosts.mk",
            "Filter: filename = /wato/dc_muc/hosts.mk",
            "Filter: filename = /wato/network/hosts.mk",
            "Or: 3",
            "Negate:",
            "And: 2",
        ]
    )

    assert parse_as_livestatus_filter(nodes, setup_folders=lambda: _TITLES) == expected


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
    condition = BooleanCondition(type="condition", field="stale", op="eq", value=value)
    with set_config(staleness_threshold=3.5):
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


def test_query_builder_label_choice_single_no_or() -> None:
    condition = LabelChoiceCondition(
        type="condition", field="labels", op="one_of", value=["cmk/os_family:linux"]
    )

    assert parse_as_livestatus_filter(condition) == "Filter: labels = 'cmk/os_family' 'linux'"


def test_query_builder_label_choice_multiple_with_or() -> None:
    condition = LabelChoiceCondition(
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
    condition = LabelChoiceCondition(
        type="condition", field="labels", op="one_of", value=["url:https://example.com"]
    )

    assert parse_as_livestatus_filter(condition) == "Filter: labels = 'url' 'https://example.com'"


def test_query_builder_label_choice_value_prefix_matches_by_regex() -> None:
    condition = LabelChoiceCondition(
        type="condition", field="labels", op="one_of", value=["cmk/os_family:lin*"]
    )

    assert parse_as_livestatus_filter(condition) == "Filter: labels ~ 'cmk/os_family' '^lin'"


def test_query_builder_label_choice_key_prefix_matches_the_names_column() -> None:
    condition = LabelChoiceCondition(
        type="condition", field="labels", op="one_of", value=["cmk/os*"]
    )

    assert parse_as_livestatus_filter(condition) == "Filter: label_names ~ ^cmk/os"


def test_query_builder_tag_key_prefix_matches_its_own_names_column() -> None:
    condition = LabelChoiceCondition(type="condition", field="tags", op="one_of", value=["crit*"])

    assert parse_as_livestatus_filter(condition) == "Filter: tag_names ~ ^crit"


def test_query_builder_label_choice_prefix_is_a_literal_not_a_pattern() -> None:
    condition = LabelChoiceCondition(
        type="condition", field="labels", op="one_of", value=["cmk/os_family:a.b*"]
    )

    assert parse_as_livestatus_filter(condition) == "Filter: labels ~ 'cmk/os_family' '^a\\.b'"


def test_query_builder_name_choice_single_no_or() -> None:
    condition = NameChoiceCondition(
        type="condition", field="contact_groups", op="one_of", value=["all"]
    )

    assert parse_as_livestatus_filter(condition) == "Filter: contact_groups >= all"


def test_query_builder_name_choice_multiple_with_or() -> None:
    condition = NameChoiceCondition(
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
    condition = NameChoiceCondition(
        type="condition", field="contact_groups", op="one_of", value=["ops*"]
    )

    assert parse_as_livestatus_filter(condition) == "Filter: contact_groups ~ ^ops"


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
