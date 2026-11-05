#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections import Counter
from collections.abc import Mapping, Sequence

import pytest

from cmk.ccc.hostaddress import HostName
from cmk.inventory.delta import ImmutableDeltaTree, SDDeltaValue
from cmk.inventory.filtering import (
    filter_delta_tree,
    filter_tree,
    InventoryPathsConfig,
    make_filter_choices_from_api_request_paths,
    make_filter_choices_from_contact_groups,
    PermittedPath,
    SDFilterChoice,
)
from cmk.inventory.trees import ImmutableTree, SDKey, SDNodeName, SDPath

from ._fixtures import (
    filled_delta_tree,
    filled_immutable_tree,
    filled_mutable_tree,
    immutable_tree,
    inventory_store,
)

_RowCounts = Counter[frozenset[tuple[SDKey, object]]]


def _row_counts(*rows: Mapping[SDKey, object]) -> _RowCounts:
    return Counter(frozenset(row.items()) for row in rows)


def _size(tree: ImmutableTree | ImmutableDeltaTree, *names: str) -> int:
    return len(tree.get_tree(tuple(SDNodeName(n) for n in names)))


def _node(
    tree: ImmutableTree | ImmutableDeltaTree, *names: str
) -> tuple[int, SDPath, Mapping[SDKey, object], _RowCounts]:
    node = tree.get_tree(tuple(SDNodeName(n) for n in names))
    return (len(node), node.path, node.attributes.pairs, _row_counts(*node.table.rows))


def test_filter_delta_tree_keeps_the_chosen_columns_of_a_table_node() -> None:
    filtered = filter_delta_tree(
        filled_delta_tree(),
        [
            SDFilterChoice(
                path=(SDNodeName("path-to-nta"), SDNodeName("nt")),
                pairs=[SDKey("nt1")],
                columns=[SDKey("nt1")],
                nodes="nothing",
            )
        ],
    )

    assert (
        _size(filtered, "path-to-nta", "na"),
        _size(filtered, "path-to-nta", "ta"),
        _node(filtered, "path-to-nta", "nt"),
    ) == (
        0,
        0,
        (
            2,
            ("path-to-nta", "nt"),
            {},
            _row_counts(
                {SDKey("nt1"): SDDeltaValue(old=None, new="NT 01")},
                {SDKey("nt1"): SDDeltaValue(old=None, new="NT 11")},
            ),
        ),
    )


def test_filter_delta_tree_keeps_the_chosen_pairs_of_an_attributes_node() -> None:
    filtered = filter_delta_tree(
        filled_delta_tree(),
        [
            SDFilterChoice(
                path=(SDNodeName("path-to-nta"), SDNodeName("na")),
                pairs=[SDKey("na1")],
                columns=[SDKey("na1")],
                nodes="nothing",
            )
        ],
    )

    assert (
        _size(filtered, "path-to-nta", "nt"),
        _size(filtered, "path-to-nta", "ta"),
        _node(filtered, "path-to-nta", "na"),
    ) == (
        0,
        0,
        (1, ("path-to-nta", "na"), {"na1": SDDeltaValue(old=None, new="NA 1")}, _row_counts()),
    )


def test_filter_delta_tree_keeps_the_chosen_pairs_and_columns() -> None:
    filtered = filter_delta_tree(
        filled_delta_tree(),
        [
            SDFilterChoice(
                path=(SDNodeName("path-to-nta"), SDNodeName("ta")),
                pairs=[SDKey("ta1")],
                columns=[SDKey("ta1")],
                nodes="nothing",
            )
        ],
    )

    assert (
        _size(filtered, "path-to-nta", "nt"),
        _size(filtered, "path-to-nta", "na"),
        _node(filtered, "path-to-nta", "ta"),
    ) == (
        0,
        0,
        (
            3,
            ("path-to-nta", "ta"),
            {"ta1": SDDeltaValue(old=None, new="TA 1")},
            _row_counts(
                {SDKey("ta1"): SDDeltaValue(old=None, new="TA 01")},
                {SDKey("ta1"): SDDeltaValue(old=None, new="TA 11")},
            ),
        ),
    )


def test_filter_delta_tree_joins_two_choices_for_one_node() -> None:
    filtered = filter_delta_tree(
        filled_delta_tree(),
        [
            SDFilterChoice(
                path=(SDNodeName("path-to-nta"), SDNodeName("ta")),
                pairs=[SDKey("ta0")],
                columns=[SDKey("ta0")],
                nodes="nothing",
            ),
            SDFilterChoice(
                path=(SDNodeName("path-to-nta"), SDNodeName("ta")),
                pairs="nothing",
                columns=[SDKey("ta1")],
                nodes="nothing",
            ),
        ],
    )

    assert (
        _node(filtered, "path-to-nta"),
        _size(filtered, "path-to-nta", "nt"),
        _size(filtered, "path-to-nta", "na"),
        _node(filtered, "path-to-nta", "ta"),
    ) == (
        (5, ("path-to-nta",), {}, _row_counts()),
        0,
        0,
        (
            5,
            ("path-to-nta", "ta"),
            {"ta0": SDDeltaValue(old=None, new="TA 0")},
            _row_counts(
                {
                    SDKey("ta0"): SDDeltaValue(old=None, new="TA 00"),
                    SDKey("ta1"): SDDeltaValue(old=None, new="TA 01"),
                },
                {
                    SDKey("ta0"): SDDeltaValue(old=None, new="TA 10"),
                    SDKey("ta1"): SDDeltaValue(old=None, new="TA 11"),
                },
            ),
        ),
    )


def test_filter_tree_without_choices_is_empty() -> None:
    assert len(filter_tree(filled_immutable_tree(), [])) == 0


def test_filter_tree_keeps_only_the_chosen_node() -> None:
    filtered = filter_tree(
        filled_immutable_tree(),
        [
            SDFilterChoice(
                path=(SDNodeName("path-to-nta"), SDNodeName("ta")),
                pairs="all",
                columns="all",
                nodes="all",
            ),
        ],
    )
    assert (
        _size(filtered, "path-to-nta", "na"),
        _size(filtered, "path-to-nta", "nt"),
        _size(filtered, "path-to-nta", "ta"),
    ) == (0, 0, 6)


def test_filter_tree_keeps_all_keys_of_a_chosen_node() -> None:
    filtered = filter_tree(
        filled_immutable_tree(),
        [
            SDFilterChoice(
                path=(SDNodeName("path-to-nta"), SDNodeName("ta")),
                pairs="all",
                columns="all",
                nodes="all",
            ),
        ],
    )

    assert _node(filtered, "path-to-nta", "ta") == (
        6,
        ("path-to-nta", "ta"),
        {"ta0": "TA 0", "ta1": "TA 1"},
        _row_counts(
            {SDKey("ta0"): "TA 00", SDKey("ta1"): "TA 01"},
            {SDKey("ta0"): "TA 10", SDKey("ta1"): "TA 11"},
        ),
    )


def test_filter_tree_keeps_only_the_chosen_keys() -> None:
    filtered = filter_tree(
        filled_immutable_tree(),
        [
            SDFilterChoice(
                path=(SDNodeName("path-to-nta"), SDNodeName("ta")),
                pairs=[SDKey("ta1")],
                columns=[SDKey("ta1")],
                nodes="all",
            ),
        ],
    )

    assert _node(filtered, "path-to-nta", "ta") == (
        3,
        ("path-to-nta", "ta"),
        {"ta1": "TA 1"},
        _row_counts({SDKey("ta1"): "TA 01"}, {SDKey("ta1"): "TA 11"}),
    )


def test_filter_tree_joins_choices_of_different_paths() -> None:
    filled_root_ = filled_mutable_tree()
    filled_root_.add(
        path=(SDNodeName("path-to"), SDNodeName("another"), SDNodeName("node1")),
        pairs=[{SDKey("ak11"): "Another value 11", SDKey("ak12"): "Another value 12"}],
    )
    filled_root_.add(
        path=(SDNodeName("path-to"), SDNodeName("another"), SDNodeName("node2")),
        key_columns=[SDKey("ak21")],
        rows=[
            {
                SDKey("ak21"): "Another value 211",
                SDKey("ak22"): "Another value 212",
            },
            {
                SDKey("ak21"): "Another value 221",
                SDKey("ak22"): "Another value 222",
            },
        ],
    )

    filtered = filter_tree(
        immutable_tree(filled_root_),
        [
            SDFilterChoice(
                path=(SDNodeName("path-to"), SDNodeName("another")),
                pairs="all",
                columns="all",
                nodes="all",
            ),
            SDFilterChoice(
                path=(SDNodeName("path-to-nta"), SDNodeName("ta")),
                pairs=[SDKey("ta0")],
                columns=[SDKey("ta1")],
                nodes="all",
            ),
        ],
    )

    assert (
        len(filtered),
        _size(filtered, "path-to-nta", "nt"),
        _size(filtered, "path-to-nta", "na"),
        _size(filtered, "path-to", "another", "node1"),
        _size(filtered, "path-to", "another", "node2"),
    ) == (9, 0, 0, 2, 4)


@pytest.mark.parametrize(
    "entry, expected_filter_choice",
    [
        (
            ".path.to.node.",
            SDFilterChoice(
                path=(SDNodeName("path"), SDNodeName("to"), SDNodeName("node")),
                pairs="all",
                columns="all",
                nodes="all",
            ),
        ),
        (
            ".path.to.node:",
            SDFilterChoice(
                path=(SDNodeName("path"), SDNodeName("to"), SDNodeName("node")),
                pairs="all",
                columns="all",
                nodes="all",
            ),
        ),
        (
            ".path.to.node:*.key",
            SDFilterChoice(
                path=(SDNodeName("path"), SDNodeName("to"), SDNodeName("node")),
                pairs=[SDKey("key")],
                columns=[SDKey("key")],
                nodes="nothing",
            ),
        ),
        (
            ".path.to.node.key",
            SDFilterChoice(
                path=(SDNodeName("path"), SDNodeName("to"), SDNodeName("node")),
                pairs=[SDKey("key")],
                columns=[SDKey("key")],
                nodes="nothing",
            ),
        ),
    ],
)
def test_make_filter_choices_from_api_request_paths(
    entry: str, expected_filter_choice: SDFilterChoice
) -> None:
    assert make_filter_choices_from_api_request_paths([entry])[0] == expected_filter_choice


@pytest.mark.parametrize(
    "filters, unavail",
    [
        (
            [
                SDFilterChoice(
                    path=(SDNodeName("hardware"), SDNodeName("components")),
                    pairs="all",
                    columns="all",
                    nodes="all",
                ),
                SDFilterChoice(
                    path=(SDNodeName("networking"), SDNodeName("interfaces")),
                    pairs="all",
                    columns="all",
                    nodes="all",
                ),
                SDFilterChoice(
                    path=(SDNodeName("software"), SDNodeName("os")),
                    pairs="all",
                    columns="all",
                    nodes="all",
                ),
            ],
            [("hardware", "system"), ("software", "applications")],
        ),
    ],
)
def test_filter_real_tree_drops_the_unchosen_nodes(
    filters: Sequence[SDFilterChoice],
    unavail: Sequence[tuple[str, str]],
) -> None:
    tree = inventory_store().load_inventory_tree(host_name=HostName("tree_new_interfaces"))
    filtered = filter_tree(tree, filters)
    assert (tree == filtered, [_size(filtered, *path) for path in unavail]) == (
        False,
        [0] * len(unavail),
    )


@pytest.mark.parametrize(
    "filters, amount_if_entries",
    [
        (
            [
                SDFilterChoice(
                    path=(SDNodeName("networking"),),
                    pairs="all",
                    columns="all",
                    nodes="all",
                )
            ],
            3178,
        ),
        (
            [
                SDFilterChoice(
                    path=(SDNodeName("networking"),),
                    pairs=(
                        [
                            SDKey("total_interfaces"),
                            SDKey("total_ethernet_ports"),
                            SDKey("available_ethernet_ports"),
                        ]
                    ),
                    columns=(
                        [
                            SDKey("total_interfaces"),
                            SDKey("total_ethernet_ports"),
                            SDKey("available_ethernet_ports"),
                        ]
                    ),
                    nodes="nothing",
                ),
            ],
            0,
        ),
        (
            [
                SDFilterChoice(
                    path=(SDNodeName("networking"), SDNodeName("interfaces")),
                    pairs="all",
                    columns="all",
                    nodes="all",
                ),
            ],
            3178,
        ),
        (
            [
                SDFilterChoice(
                    path=(SDNodeName("networking"), SDNodeName("interfaces")),
                    pairs=[SDKey("admin_status")],
                    columns=[SDKey("admin_status")],
                    nodes="nothing",
                ),
            ],
            326,
        ),
        (
            [
                SDFilterChoice(
                    path=(SDNodeName("networking"), SDNodeName("interfaces")),
                    pairs=[SDKey("admin_status"), SDKey("FOOBAR")],
                    columns=[SDKey("admin_status"), SDKey("FOOBAR")],
                    nodes="nothing",
                ),
            ],
            326,
        ),
        (
            [
                SDFilterChoice(
                    path=(SDNodeName("networking"), SDNodeName("interfaces")),
                    pairs=[SDKey("admin_status"), SDKey("oper_status")],
                    columns=[SDKey("admin_status"), SDKey("oper_status")],
                    nodes="nothing",
                ),
            ],
            652,
        ),
        (
            [
                SDFilterChoice(
                    path=(SDNodeName("networking"), SDNodeName("interfaces")),
                    pairs=[SDKey("admin_status"), SDKey("oper_status"), SDKey("FOOBAR")],
                    columns=[SDKey("admin_status"), SDKey("oper_status"), SDKey("FOOBAR")],
                    nodes="nothing",
                ),
            ],
            652,
        ),
    ],
)
def test_filter_networking_tree_keeps_only_networking(
    filters: Sequence[SDFilterChoice],
    amount_if_entries: int,
) -> None:
    filtered = filter_tree(
        inventory_store().load_inventory_tree(host_name=HostName("tree_new_interfaces")),
        filters,
    )
    assert (
        _size(filtered, "networking") > 0,
        _size(filtered, "hardware"),
        _size(filtered, "software"),
        _size(filtered, "networking", "interfaces"),
    ) == (True, 0, 0, amount_if_entries)


def test_filter_networking_tree_with_nothing_chosen_is_empty() -> None:
    filtered = filter_tree(
        inventory_store().load_inventory_tree(host_name=HostName("tree_new_interfaces")),
        [
            SDFilterChoice(
                path=(SDNodeName("networking"),),
                pairs="nothing",
                columns="nothing",
                nodes="nothing",
            ),
        ],
    )
    assert (
        _size(filtered, "networking"),
        _size(filtered, "hardware"),
        _size(filtered, "software"),
    ) == (0, 0, 0)


@pytest.mark.parametrize(
    "entry, expected_filter_choice",
    [
        (
            {
                "visible_raw_path": "path.to.node",
            },
            SDFilterChoice(
                path=(SDNodeName("path"), SDNodeName("to"), SDNodeName("node")),
                pairs="all",
                columns="all",
                nodes="all",
            ),
        ),
        (
            {
                "visible_raw_path": "path.to.node",
                "nodes": ("choices", ["node"]),
            },
            SDFilterChoice(
                path=(SDNodeName("path"), SDNodeName("to"), SDNodeName("node")),
                pairs="all",
                columns="all",
                nodes=[SDNodeName("node")],
            ),
        ),
        (
            {
                "visible_raw_path": "path.to.node",
                "attributes": ("choices", ["key"]),
            },
            SDFilterChoice(
                path=(SDNodeName("path"), SDNodeName("to"), SDNodeName("node")),
                pairs=[SDKey("key")],
                columns="all",
                nodes="all",
            ),
        ),
        (
            {
                "visible_raw_path": "path.to.node",
                "columns": ("choices", ["key"]),
            },
            SDFilterChoice(
                path=(SDNodeName("path"), SDNodeName("to"), SDNodeName("node")),
                pairs="all",
                columns=[SDKey("key")],
                nodes="all",
            ),
        ),
        (
            {
                "visible_raw_path": "path.to.node",
                "nodes": "nothing",
            },
            SDFilterChoice(
                path=(SDNodeName("path"), SDNodeName("to"), SDNodeName("node")),
                pairs="all",
                columns="all",
                nodes="nothing",
            ),
        ),
        (
            {
                "visible_raw_path": "path.to.node",
                "attributes": "nothing",
            },
            SDFilterChoice(
                path=(SDNodeName("path"), SDNodeName("to"), SDNodeName("node")),
                pairs="nothing",
                columns="all",
                nodes="all",
            ),
        ),
        (
            {
                "visible_raw_path": "path.to.node",
                "columns": "nothing",
            },
            SDFilterChoice(
                path=(SDNodeName("path"), SDNodeName("to"), SDNodeName("node")),
                pairs="all",
                columns="nothing",
                nodes="all",
            ),
        ),
    ],
)
def test_make_filter_choices_from_contact_groups_translates_a_permitted_path(
    entry: PermittedPath, expected_filter_choice: SDFilterChoice
) -> None:
    assert make_filter_choices_from_contact_groups([("paths", [entry])]) == [expected_filter_choice]


_PATHS_A = PermittedPath(visible_raw_path="a")
_PATHS_B = PermittedPath(visible_raw_path="b")


@pytest.mark.parametrize(
    "configs",
    [
        pytest.param([], id="no-contact-group"),
        pytest.param([None], id="unconfigured"),
        pytest.param(["allow_all"], id="allow-all"),
        pytest.param([("paths", [_PATHS_A]), "allow_all"], id="allow-all-wins"),
    ],
)
def test_make_filter_choices_from_contact_groups_permits_everything(
    configs: Sequence[InventoryPathsConfig | None],
) -> None:
    assert make_filter_choices_from_contact_groups(configs) is None


@pytest.mark.parametrize(
    "configs",
    [
        pytest.param(["forbid_all"], id="forbid-all"),
        pytest.param([("paths", [])], id="no-paths"),
    ],
)
def test_make_filter_choices_from_contact_groups_permits_nothing(
    configs: Sequence[InventoryPathsConfig | None],
) -> None:
    assert make_filter_choices_from_contact_groups(configs) == []


def test_make_filter_choices_from_contact_groups_joins_the_paths() -> None:
    assert make_filter_choices_from_contact_groups(
        [("paths", [_PATHS_A]), "forbid_all", ("paths", [_PATHS_B])]
    ) == [
        SDFilterChoice(path=(SDNodeName("a"),), pairs="all", columns="all", nodes="all"),
        SDFilterChoice(path=(SDNodeName("b"),), pairs="all", columns="all", nodes="all"),
    ]
