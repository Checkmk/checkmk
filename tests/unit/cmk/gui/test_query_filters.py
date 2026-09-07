#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

from contextlib import AbstractContextManager as ContextManager
from contextlib import nullcontext
from typing import Literal

import pytest

from cmk.gui.exceptions import MKUserError
from cmk.gui.query_filters import AllLabelGroupsQuery, MultipleQuery
from cmk.gui.type_defs import FilterHTTPVariables, Rows, VisualContext
from cmk.ruleset_matcher.labels import LabelGroups


@pytest.mark.parametrize(
    "object_type, value, parsed_value, expectation, error_msg",
    [
        pytest.param(
            "host",
            {
                "host_labels_count": "2",
                # Group 1
                "host_labels_1_vs_count": "2",
                "host_labels_1_bool": "and",
                "host_labels_1_vs_1_bool": "and",
                "host_labels_1_vs_1_vs": "label:abc",
                "host_labels_1_vs_2_bool": "or",
                "host_labels_1_vs_2_vs": "label:xyz",
                # Group 2
                "host_labels_2_vs_count": "1",
                "host_labels_2_bool": "not",
                "host_labels_2_vs_1_bool": "and",
                "host_labels_2_vs_1_vs": "label:mno",
            },
            [
                ("and", [("and", "label:abc"), ("or", "label:xyz")]),
                ("not", [("and", "label:mno")]),
            ],
            nullcontext(),
            None,
        ),
        pytest.param(
            "service",
            {
                "service_labels_count": "2",
                # Group 1
                "service_labels_1_vs_count": "2",
                "service_labels_1_bool": "and",
                "service_labels_1_vs_1_bool": "and",
                "service_labels_1_vs_1_vs": "label:abc",
                "service_labels_1_vs_2_bool": "or",
                "service_labels_1_vs_2_vs": "label:xyz",
                # Group 2
                "service_labels_2_vs_count": "1",
                "service_labels_2_bool": "not",
                "service_labels_2_vs_1_bool": "and",
                "service_labels_2_vs_1_vs": "label:mno",
            },
            [
                ("and", [("and", "label:abc"), ("or", "label:xyz")]),
                ("not", [("and", "label:mno")]),
            ],
            nullcontext(),
            None,
        ),
        pytest.param(
            "host",
            {
                "host_labels_count": "not an integer",
            },
            [],
            pytest.raises(MKUserError),
            'The value "not an integer" of HTTP variable "host_labels_count" is not an integer.',
        ),
        pytest.param(
            "service",
            {
                "service_labels_count": "1",
                # Group 1
                "service_labels_1_vs_count": "2",
                "service_labels_1_bool": "annnd",
            },
            [],
            pytest.raises(MKUserError),
            'The value "annnd" of HTTP variable "service_labels_1_bool" is not a valid operator ({"and", "or", "not"}).',
        ),
    ],
)
def test_label_value_parsing(  # type: ignore[misc]
    object_type: Literal["host", "service"],
    value: FilterHTTPVariables,
    parsed_value: LabelGroups,
    expectation: ContextManager,
    error_msg: str | None,
) -> None:
    inst: AllLabelGroupsQuery = AllLabelGroupsQuery(object_type=object_type)
    with expectation as e:
        assert parsed_value == inst.parse_value(value)
    assert error_msg is None or error_msg in str(e)


def _service_groups_query() -> MultipleQuery:
    return MultipleQuery(ident="servicegroups", column="service_groups", op=">=", negateable=True)


def _context(selection: str, negate: str = "") -> VisualContext:
    return {"servicegroups": {"servicegroups": selection, "neg_servicegroups": negate}}


def _rows(*groups_per_row: list[str]) -> Rows:
    return [{"service_groups": groups} for groups in groups_per_row]


def test_rows_of_the_selected_group_are_kept() -> None:
    query = _service_groups_query()

    rows = query.filter_table(_context("cpu"), _rows(["cpu"], ["mem"]))

    assert rows == _rows(["cpu"])


def test_rows_of_a_negated_group_are_dropped() -> None:
    query = _service_groups_query()

    rows = query.filter_table(_context("cpu", negate="on"), _rows(["cpu"], ["mem"]))

    assert rows == _rows(["mem"])


def test_a_row_matches_by_any_of_its_groups() -> None:
    query = _service_groups_query()

    rows = query.filter_table(_context("cpu"), _rows(["disk", "cpu"]))

    assert rows == _rows(["disk", "cpu"])


def test_any_of_several_selected_groups_matches() -> None:
    query = _service_groups_query()

    rows = query.filter_table(_context("cpu|disk"), _rows(["cpu"], ["disk"], ["mem"]))

    assert rows == _rows(["cpu"], ["disk"])


def test_a_negation_drops_every_selected_group() -> None:
    query = _service_groups_query()

    rows = query.filter_table(_context("cpu|disk", negate="on"), _rows(["cpu"], ["disk"], ["mem"]))

    assert rows == _rows(["mem"])


def test_an_empty_selection_keeps_every_row() -> None:
    query = _service_groups_query()

    rows = query.filter_table(_context(""), _rows(["cpu"], ["mem"]))

    assert rows == _rows(["cpu"], ["mem"])


def test_a_row_without_the_column_is_kept() -> None:
    # BI aggregation rows have no group columns, and the caller of filter_table does not
    # know which filter needs which column
    query = _service_groups_query()

    rows = query.filter_table(_context("cpu"), [{"aggr_name": "an aggregation"}])

    assert rows == [{"aggr_name": "an aggregation"}]


def test_a_row_of_no_group_at_all_is_dropped() -> None:
    query = _service_groups_query()

    rows = query.filter_table(_context("cpu"), _rows([]))

    assert rows == []


def test_a_column_compared_as_a_whole_keeps_every_row() -> None:
    # "=" says nothing about the other values a matching row carries, so there is nothing
    # this implementation could decide
    query = MultipleQuery(ident="whatever", column="service_groups", op="=")

    rows = query.filter_table({"whatever": {"whatever": "cpu"}}, _rows(["mem"]))

    assert rows == _rows(["mem"])


def test_post_filtering_agrees_with_the_livestatus_filter() -> None:
    # Any non-empty value negates the Livestatus filter, so it has to negate here as well
    query = _service_groups_query()
    negated: FilterHTTPVariables = {"servicegroups": "cpu", "neg_servicegroups": "off"}

    assert query.filter(negated) == "Filter: service_groups !>= cpu\n"
    assert query.filter_table({"servicegroups": negated}, _rows(["cpu"], ["mem"])) == _rows(["mem"])
