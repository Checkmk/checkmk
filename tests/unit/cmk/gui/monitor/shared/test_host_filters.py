#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator, Mapping, Sequence
from typing import get_args, get_type_hints, TypeAliasType

import pytest

from cmk.gui.monitor.shared import (
    AndNode,
    BooleanCondition,
    ConditionNode,
    FILTER_NODE,
    FilterNode,
    FolderCondition,
    HostStateLabel,
    LabelChoiceCondition,
    livestatus_filter_lines,
    NameChoiceCondition,
    NotNode,
    NumericCondition,
    OrNode,
    SiteChoiceCondition,
    StateChoiceCondition,
    StringCondition,
    TimestampCondition,
)
from cmk.livestatus_client.tables import Hosts, Services


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


@pytest.mark.parametrize("value", ["Rack", "Rack*", "*1", "rack*1"])
def test_folder_condition_takes_a_star_as_any_text(value: str) -> None:
    node = FolderCondition(type="condition", field="folder", op="contains", value=value)

    assert livestatus_filter_lines(
        node, setup_folders=lambda: {"dc_muc/rack1": "Data center Munich / Rack 1"}
    ) == ["Filter: filename = /wato/dc_muc/rack1/hosts.mk"]


def test_folder_condition_does_not_render_with_a_column_prefix() -> None:
    node = FolderCondition(type="condition", field="folder", op="contains", value="Munich")

    with pytest.raises(ValueError):
        livestatus_filter_lines(
            node, setup_folders=lambda: {"dc_muc": "Data center Munich"}, column_prefix="host_"
        )


def _literal_values(annotation: object) -> tuple[object, ...]:
    return get_args(annotation.__value__ if isinstance(annotation, TypeAliasType) else annotation)


# One value per form the filter lines take for that kind of condition.
_VALUES_BY_CONDITION: Mapping[type[object], Sequence[object]] = {
    StringCondition: ["x"],
    FolderCondition: ["Munich", "Nowhere"],
    StateChoiceCondition: [list(_literal_values(HostStateLabel))],
    NumericCondition: [1],
    TimestampCondition: [1],
    BooleanCondition: [True, False],
    LabelChoiceCondition: [["key:value", "key:val*", "key:*", "ke*"]],
    NameChoiceCondition: [["name", "na*"]],
}


def _every_condition(*, but: type[object] | None = None) -> Iterator[FilterNode]:
    for condition_type, values in _VALUES_BY_CONDITION.items():
        if condition_type is but:
            continue
        hints = get_type_hints(condition_type)
        for field in _literal_values(hints["field"]):
            for op in _literal_values(hints["op"]):
                for value in values:
                    yield FILTER_NODE.validate_python(
                        {"type": "condition", "field": field, "op": op, "value": value}
                    )


def test_every_kind_of_host_condition_but_the_site_has_values() -> None:
    # A site condition chooses the sites to query and never becomes a filter line.
    assert set(_VALUES_BY_CONDITION) == set(_literal_values(ConditionNode)) - {SiteChoiceCondition}


@pytest.mark.usefixtures("request_context")
def test_every_host_condition_filters_on_columns_of_the_core_hosts_table() -> None:
    folders = {"muc": "Munich"}
    unknown = {
        line.split()[1]
        for condition in _every_condition()
        for line in livestatus_filter_lines(condition, setup_folders=lambda: folders)
        if line.startswith("Filter: ")
    } - set(Hosts.__columns__())

    assert unknown == set()


@pytest.mark.usefixtures("request_context")
def test_every_host_condition_filters_on_host_columns_of_the_core_services_table() -> None:
    # The services table names the columns of a service's host with a "host_" prefix.
    unknown = {
        line.split()[1]
        for condition in _every_condition(but=FolderCondition)
        for line in livestatus_filter_lines(condition, column_prefix="host_")
        if line.startswith("Filter: ")
    } - set(Services.__columns__())

    assert unknown == set()
