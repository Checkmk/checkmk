#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.monitor.services._api._filters import (
    parse_as_livestatus_filter,
    ServiceAndNode,
    ServiceNotNode,
    ServiceOrNode,
    ServiceStateChoiceCondition,
)


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
