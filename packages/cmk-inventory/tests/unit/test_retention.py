#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Literal

from cmk.inventory.config import RawIntervalFromConfig
from cmk.inventory.retention import update_from_previous
from cmk.inventory.serialization import deserialize_tree
from cmk.inventory.trees import (
    ImmutableTree,
    MutableTree,
    RetentionInterval,
    SDKey,
    SDNodeName,
    SDPath,
)

from ._fixtures import immutable_tree

_RETENTION_PATH = (SDNodeName("path"), SDNodeName("to"), SDNodeName("node"))


def _retention_config() -> Sequence[RawIntervalFromConfig]:
    return [
        RawIntervalFromConfig(
            interval=7,
            visible_raw_path="path.to.node",
            attributes=("choices", ["a1"]),
        ),
        RawIntervalFromConfig(
            interval=7,
            visible_raw_path="path.to.node",
            columns="all",
        ),
    ]


def _updated_tree(
    *, now: int, pairs_cache_info: Mapping[SDPath, tuple[int, int] | None]
) -> MutableTree:
    tree = MutableTree()
    tree.add(
        path=_RETENTION_PATH,
        pairs=[{SDKey("a1"): "value 1", SDKey("a2"): "value 2"}],
        key_columns=[SDKey("c0")],
        rows=[{SDKey("c0"): "row 0", SDKey("c1"): "value 1"}],
    )
    update_from_previous(
        tree,
        now=now,
        previous_tree=ImmutableTree(),
        raw_intervals_from_config=_retention_config(),
        pairs_cache_info=pairs_cache_info,
        columns_cache_info={},
    )
    return tree


def _retained_pairs(
    *, now: int, pairs_cache_info: Mapping[SDPath, tuple[int, int] | None]
) -> Mapping[SDKey, RetentionInterval]:
    return (
        _updated_tree(now=now, pairs_cache_info=pairs_cache_info)
        .get_tree(_RETENTION_PATH)
        .attributes.retentions
    )


def test_retention_filter_keeps_the_columns_of_the_same_path() -> None:
    assert _updated_tree(now=10, pairs_cache_info={}).get_tree(
        _RETENTION_PATH
    ).table.retentions == {
        ("row 0",): {
            SDKey("c0"): RetentionInterval(10, 0, 7, "current"),
            SDKey("c1"): RetentionInterval(10, 0, 7, "current"),
        }
    }


def test_retention_filter_keeps_only_the_configured_pairs() -> None:
    assert set(_retained_pairs(now=10, pairs_cache_info={})) == {SDKey("a1")}


def test_retention_filter_defaults_the_cache_info() -> None:
    assert _retained_pairs(now=10, pairs_cache_info={}) == {
        SDKey("a1"): RetentionInterval(10, 0, 7, "current")
    }


def test_retention_filter_uses_the_cache_info() -> None:
    assert _retained_pairs(now=10, pairs_cache_info={_RETENTION_PATH: (2, 3)}) == {
        SDKey("a1"): RetentionInterval(2, 3, 7, "current")
    }


def test_retention_filter_defaults_an_unset_cache_info() -> None:
    assert _retained_pairs(now=10, pairs_cache_info={_RETENTION_PATH: None}) == {
        SDKey("a1"): RetentionInterval(10, 0, 7, "current")
    }


def _update_from(
    current_tree: MutableTree, previous_tree: ImmutableTree, raw_interval: RawIntervalFromConfig
) -> MutableTree:
    update_from_previous(
        current_tree,
        now=0,
        previous_tree=previous_tree,
        raw_intervals_from_config=[raw_interval],
        pairs_cache_info={(): (4, 5)},
        columns_cache_info={(): (4, 5)},
    )
    return current_tree


def _tree_with_updated_attributes() -> MutableTree:
    current_tree = MutableTree()
    current_tree.add(path=(), pairs=[{SDKey("a1"): "A1: cur", SDKey("a3"): "A3: only cur"}])
    return _update_from(
        current_tree,
        deserialize_tree(
            {
                "Attributes": {
                    "Pairs": {"a1": "A1: prev", "a2": "A2: only prev"},
                    "Retentions": {"a1": (1, 2, 3), "a2": (1, 2, 3)},
                },
                "Table": {},
                "Nodes": {},
            }
        ),
        RawIntervalFromConfig(interval=6, visible_raw_path="", attributes="all"),
    )


def test_update_reports_the_restored_pairs() -> None:
    assert _tree_with_updated_attributes().get_update_results() == {
        (): [
            "[Attributes] Added pairs: a2",
            "[Attributes] Keep until: a1 (15), a2 (6), a3 (15)",
        ]
    }


def test_update_restores_the_retained_pairs() -> None:
    attributes = immutable_tree(_tree_with_updated_attributes()).attributes
    assert (attributes.pairs, attributes.retentions) == (
        {"a1": "A1: cur", "a2": "A2: only prev", "a3": "A3: only cur"},
        {
            "a1": RetentionInterval(4, 5, 6, "current"),
            "a2": RetentionInterval(1, 2, 3, "previous"),
            "a3": RetentionInterval(4, 5, 6, "current"),
        },
    )


def _tree_with_updated_row(
    current_row: Mapping[SDKey, str], columns: Literal["all"] | tuple[str, list[str]]
) -> MutableTree:
    current_tree = MutableTree()
    current_tree.add(path=(), key_columns=[SDKey("kc")], rows=[current_row])
    return _update_from(
        current_tree,
        deserialize_tree(
            {
                "Attributes": {},
                "Table": {
                    "KeyColumns": ["kc"],
                    "Rows": [{"kc": "KC", "c1": "C1: prev C1", "c2": "C2: only prev"}],
                    "Retentions": {("KC",): {"c1": (1, 2, 3), "c2": (1, 2, 3)}},
                },
                "Nodes": {},
            }
        ),
        RawIntervalFromConfig(interval=6, visible_raw_path="", columns=columns),
    )


def _tree_with_all_columns_retained() -> MutableTree:
    return _tree_with_updated_row(
        {SDKey("kc"): "KC", SDKey("c1"): "C1: cur", SDKey("c3"): "C3: only cur"}, "all"
    )


def _tree_with_chosen_columns_retained() -> MutableTree:
    return _tree_with_updated_row(
        {SDKey("kc"): "KC", SDKey("c3"): "C3: only cur"}, ("choices", ["c2", "c3"])
    )


def test_update_reports_the_restored_columns_of_a_row() -> None:
    assert _tree_with_all_columns_retained().get_update_results() == {
        (): [
            "[Table] 'KC': Added row: c2, kc",
            "[Table] 'KC': Keep until: c1 (15), c2 (6), c3 (15), kc (15)",
        ]
    }


def test_update_restores_the_retained_columns_of_a_row() -> None:
    table = immutable_tree(_tree_with_all_columns_retained()).table
    assert (table.key_columns, table.rows, table.retentions) == (
        ["kc"],
        [{"c1": "C1: cur", "c2": "C2: only prev", "c3": "C3: only cur", "kc": "KC"}],
        {
            ("KC",): {
                "c1": RetentionInterval(4, 5, 6, "current"),
                "c2": RetentionInterval(1, 2, 3, "previous"),
                "c3": RetentionInterval(4, 5, 6, "current"),
                "kc": RetentionInterval(4, 5, 6, "current"),
            }
        },
    )


def test_update_reports_only_the_chosen_columns() -> None:
    assert _tree_with_chosen_columns_retained().get_update_results() == {
        (): [
            "[Table] 'KC': Added row: c2, kc",
            "[Table] 'KC': Keep until: c2 (6), c3 (15)",
        ],
    }


def test_update_restores_only_the_chosen_columns() -> None:
    table = immutable_tree(_tree_with_chosen_columns_retained()).table
    assert (table.key_columns, table.rows, table.retentions) == (
        ["kc"],
        [{"c2": "C2: only prev", "c3": "C3: only cur", "kc": "KC"}],
        {
            ("KC",): {
                "c2": RetentionInterval(1, 2, 3, "previous"),
                "c3": RetentionInterval(4, 5, 6, "current"),
            }
        },
    )


def test_update_from_previous_restores_nothing_of_a_row_present_again() -> None:
    previous_tree = deserialize_tree(
        {
            "Attributes": {},
            "Table": {
                "KeyColumns": ["kc"],
                "Rows": [{"kc": "KC", "c1": "C1: prev"}],
                "Retentions": {("KC",): {"c1": (1, 2, 3)}},
            },
            "Nodes": {},
        }
    )
    current_tree = MutableTree()
    current_tree.add(
        path=(), key_columns=[SDKey("kc")], rows=[{SDKey("kc"): "KC", SDKey("c1"): "C1: cur"}]
    )
    update_from_previous(
        current_tree,
        now=0,
        previous_tree=previous_tree,
        raw_intervals_from_config=[
            RawIntervalFromConfig(interval=6, visible_raw_path="", columns="all")
        ],
        pairs_cache_info={},
        columns_cache_info={(): (4, 5)},
    )
    assert current_tree.get_update_results() == {(): ["[Table] 'KC': Keep until: c1 (15), kc (15)"]}


def test_update_results_of_a_child_node() -> None:
    tree = MutableTree()
    tree.add(path=(SDNodeName("node"),), pairs=[{SDKey("key"): "value"}])
    update_from_previous(
        tree,
        now=0,
        previous_tree=ImmutableTree(),
        raw_intervals_from_config=[
            RawIntervalFromConfig(interval=30, visible_raw_path="node", attributes="all")
        ],
        pairs_cache_info={(SDNodeName("node"),): (10, 20)},
        columns_cache_info={},
    )
    assert tree.get_update_results() == {
        (SDNodeName("node"),): ["[Attributes] Keep until: key (60)"]
    }
