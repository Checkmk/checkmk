#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

from cmk.inventory.retention import (
    RawIntervalFromConfig,
    update_from_previous,
)
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


def test_update_attributes_from_previous() -> None:
    previous_tree = deserialize_tree(
        {
            "Attributes": {
                "Pairs": {"a1": "A1: prev", "a2": "A2: only prev"},
                "Retentions": {"a1": (1, 2, 3), "a2": (1, 2, 3)},
            },
            "Table": {},
            "Nodes": {},
        }
    )
    current_tree_ = MutableTree()
    current_tree_.add(
        path=(),
        pairs=[{SDKey("a1"): "A1: cur", SDKey("a3"): "A3: only cur"}],
    )
    update_from_previous(
        current_tree_,
        now=0,
        previous_tree=previous_tree,
        raw_intervals_from_config=[
            RawIntervalFromConfig(interval=6, visible_raw_path="", attributes="all")
        ],
        pairs_cache_info={(): (4, 5)},
        columns_cache_info={(): (4, 5)},
    )
    assert current_tree_.get_update_results() == {
        (): [
            "[Attributes] Added pairs: a2",
            "[Attributes] Keep until: a1 (15), a2 (6), a3 (15)",
        ]
    }

    current_tree = immutable_tree(current_tree_)
    assert current_tree.attributes.pairs == {
        "a1": "A1: cur",
        "a2": "A2: only prev",
        "a3": "A3: only cur",
    }
    assert current_tree.attributes.retentions == {
        "a1": RetentionInterval(4, 5, 6, "current"),
        "a2": RetentionInterval(1, 2, 3, "previous"),
        "a3": RetentionInterval(4, 5, 6, "current"),
    }


def test_update_from_previous_1() -> None:
    previous_tree = deserialize_tree(
        {
            "Attributes": {},
            "Table": {
                "KeyColumns": ["kc"],
                "Rows": [{"kc": "KC", "c1": "C1: prev C1", "c2": "C2: only prev"}],
                "Retentions": {("KC",): {"c1": (1, 2, 3), "c2": (1, 2, 3)}},
            },
            "Nodes": {},
        }
    )
    current_tree_ = MutableTree()
    current_tree_.add(
        path=(),
        key_columns=[SDKey("kc")],
        rows=[
            {SDKey("kc"): "KC", SDKey("c1"): "C1: cur", SDKey("c3"): "C3: only cur"},
        ],
    )
    update_from_previous(
        current_tree_,
        now=0,
        previous_tree=previous_tree,
        raw_intervals_from_config=[
            RawIntervalFromConfig(interval=6, visible_raw_path="", columns="all")
        ],
        pairs_cache_info={(): (4, 5)},
        columns_cache_info={(): (4, 5)},
    )
    assert current_tree_.get_update_results() == {
        (): [
            "[Table] 'KC': Added row: c2, kc",
            "[Table] 'KC': Keep until: c1 (15), c2 (6), c3 (15), kc (15)",
        ]
    }

    current_tree = immutable_tree(current_tree_)
    assert current_tree.table.key_columns == ["kc"]
    assert current_tree.table.retentions == {
        ("KC",): {
            "c1": RetentionInterval(4, 5, 6, "current"),
            "c2": RetentionInterval(1, 2, 3, "previous"),
            "c3": RetentionInterval(4, 5, 6, "current"),
            "kc": RetentionInterval(4, 5, 6, "current"),
        }
    }
    assert current_tree.get_rows(()) == [
        {"c1": "C1: cur", "c2": "C2: only prev", "c3": "C3: only cur", "kc": "KC"}
    ]


def test_update_from_previous_2() -> None:
    previous_tree = deserialize_tree(
        {
            "Attributes": {},
            "Table": {
                "KeyColumns": ["kc"],
                "Rows": [{"kc": "KC", "c1": "C1: prev C1", "c2": "C2: only prev"}],
                "Retentions": {("KC",): {"c1": (1, 2, 3), "c2": (1, 2, 3)}},
            },
            "Nodes": {},
        }
    )
    current_tree_ = MutableTree()
    current_tree_.add(
        path=(),
        key_columns=[SDKey("kc")],
        rows=[
            {SDKey("kc"): "KC", SDKey("c3"): "C3: only cur"},
        ],
    )
    update_from_previous(
        current_tree_,
        now=0,
        previous_tree=previous_tree,
        raw_intervals_from_config=[
            RawIntervalFromConfig(
                interval=6, visible_raw_path="", columns=("choices", ["c2", "c3"])
            )
        ],
        pairs_cache_info={(): (4, 5)},
        columns_cache_info={(): (4, 5)},
    )
    assert current_tree_.get_update_results() == {
        (): [
            "[Table] 'KC': Added row: c2, kc",
            "[Table] 'KC': Keep until: c2 (6), c3 (15)",
        ],
    }

    current_tree = immutable_tree(current_tree_)
    assert current_tree.table.key_columns == ["kc"]
    assert current_tree.table.retentions == {
        ("KC",): {
            "c2": RetentionInterval(1, 2, 3, "previous"),
            "c3": RetentionInterval(4, 5, 6, "current"),
        }
    }
    assert current_tree.get_rows(()) == [{"c2": "C2: only prev", "c3": "C3: only cur", "kc": "KC"}]
