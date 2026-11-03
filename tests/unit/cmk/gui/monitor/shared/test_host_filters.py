#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.monitor.shared import (
    AndNode,
    BooleanCondition,
    FilterNode,
    FolderCondition,
    LabelChoiceCondition,
    livestatus_filter_lines,
    NameChoiceCondition,
    NotNode,
    NumericCondition,
    OrNode,
    StateChoiceCondition,
    StringCondition,
    TimestampCondition,
)


@pytest.mark.parametrize(
    "node",
    [
        pytest.param(
            StringCondition(type="condition", field="name", op="contains", value="heute"),
            id="string",
        ),
        pytest.param(
            NumericCondition(type="condition", field="num_services", op="gt", value=0),
            id="numeric",
        ),
        pytest.param(
            TimestampCondition(type="condition", field="last_check", op="gte", value=1752405510),
            id="timestamp",
        ),
        *(
            pytest.param(
                BooleanCondition(type="condition", field=field, op="eq", value=True),
                id=f"boolean {field}",
            )
            for field in (
                "acknowledged",
                "in_downtime",
                "has_comments",
                "active_checks_disabled",
                "passive_checks_disabled",
                "stale",
            )
        ),
        pytest.param(
            StateChoiceCondition(
                type="condition", field="state", op="one_of", value=["UP", "PENDING"]
            ),
            id="state choice",
        ),
        pytest.param(
            LabelChoiceCondition(
                type="condition", field="labels", op="all_of", value=["env:prod", "os", "app:w*"]
            ),
            id="label choice",
        ),
        pytest.param(
            LabelChoiceCondition(type="condition", field="tags", op="one_of", value=["site"]),
            id="tag key",
        ),
        pytest.param(
            NameChoiceCondition(
                type="condition", field="groups", op="one_of", value=["linux", "win*"]
            ),
            id="name choice",
        ),
        pytest.param(
            NotNode(
                type="not",
                child=OrNode(
                    type="or",
                    children=[
                        StringCondition(type="condition", field="alias", op="matches", value="a"),
                        AndNode(
                            type="and",
                            children=[
                                BooleanCondition(
                                    type="condition", field="is_flapping", op="eq", value=False
                                ),
                                NumericCondition(
                                    type="condition", field="num_services_crit", op="eq", value=1
                                ),
                            ],
                        ),
                    ],
                ),
            ),
            id="nested nodes",
        ),
    ],
)
@pytest.mark.usefixtures("request_context")
def test_column_prefix_only_renames_the_columns(node: FilterNode) -> None:
    assert livestatus_filter_lines(node, column_prefix="host_") == [
        line.replace("Filter: ", "Filter: host_", 1) for line in livestatus_filter_lines(node)
    ]


def test_folder_condition_does_not_render_with_a_column_prefix() -> None:
    node = FolderCondition(type="condition", field="folder", op="contains", value="Munich")

    with pytest.raises(ValueError):
        livestatus_filter_lines(
            node, setup_folders=lambda: {"dc_muc": "Data center Munich"}, column_prefix="host_"
        )
