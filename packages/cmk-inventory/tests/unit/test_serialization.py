#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Literal

import pytest

from cmk.inventory.delta import compare_trees, ImmutableDeltaTree
from cmk.inventory.serialization import (
    deserialize_delta_tree,
    deserialize_tree,
    SDRawDeltaTree,
    serialize_delta_tree,
    serialize_tree,
)
from cmk.inventory.trees import (
    ImmutableAttributes,
    ImmutableTree,
    MutableTree,
    RetentionInterval,
    SDKey,
    SDNodeName,
)

from ._fixtures import (
    empty_immutable_tree,
    empty_mutable_tree,
    filled_immutable_tree,
    filled_mutable_tree,
)


def test_serialize_empty_mut_tree() -> None:
    assert serialize_tree(empty_mutable_tree()) == {"Attributes": {}, "Table": {}, "Nodes": {}}


def test_serialize_filled_mut_tree() -> None:
    raw_tree = serialize_tree(filled_mutable_tree())
    assert not raw_tree["Attributes"]
    assert not raw_tree["Table"]
    assert not raw_tree["Nodes"][SDNodeName("path-to-nta")]["Attributes"]
    assert not raw_tree["Nodes"][SDNodeName("path-to-nta")]["Table"]

    assert raw_tree["Nodes"][SDNodeName("path-to-nta")]["Nodes"][SDNodeName("na")]["Attributes"][
        "Pairs"
    ] == {
        "na0": "NA 0",
        "na1": "NA 1",
    }
    assert not raw_tree["Nodes"][SDNodeName("path-to-nta")]["Nodes"][SDNodeName("na")]["Table"]
    assert not raw_tree["Nodes"][SDNodeName("path-to-nta")]["Nodes"][SDNodeName("na")]["Nodes"]

    assert not raw_tree["Nodes"][SDNodeName("path-to-nta")]["Nodes"][SDNodeName("nt")]["Attributes"]
    assert raw_tree["Nodes"][SDNodeName("path-to-nta")]["Nodes"][SDNodeName("nt")]["Table"][
        "KeyColumns"
    ] == ["nt0"]
    nt_rows = raw_tree["Nodes"][SDNodeName("path-to-nta")]["Nodes"][SDNodeName("nt")]["Table"][
        "Rows"
    ]
    assert len(nt_rows) == 2
    for row in [
        {"nt0": "NT 00", "nt1": "NT 01"},
        {"nt0": "NT 10", "nt1": "NT 11"},
    ]:
        assert row in nt_rows
    assert not raw_tree["Nodes"][SDNodeName("path-to-nta")]["Nodes"][SDNodeName("nt")]["Nodes"]

    assert raw_tree["Nodes"][SDNodeName("path-to-nta")]["Nodes"][SDNodeName("ta")]["Attributes"][
        "Pairs"
    ] == {
        "ta0": "TA 0",
        "ta1": "TA 1",
    }
    assert raw_tree["Nodes"][SDNodeName("path-to-nta")]["Nodes"][SDNodeName("ta")]["Table"][
        "KeyColumns"
    ] == ["ta0"]
    ta_rows = raw_tree["Nodes"][SDNodeName("path-to-nta")]["Nodes"][SDNodeName("ta")]["Table"][
        "Rows"
    ]
    assert len(ta_rows) == 2
    for row in [
        {"ta0": "TA 00", "ta1": "TA 01"},
        {"ta0": "TA 10", "ta1": "TA 11"},
    ]:
        assert row in ta_rows
    assert not raw_tree["Nodes"][SDNodeName("path-to-nta")]["Nodes"][SDNodeName("ta")]["Nodes"]


def test_deserialize_empty_imm_tree() -> None:
    assert deserialize_tree({}) == MutableTree()
    assert deserialize_tree({}) == ImmutableTree()


def test_deserialize_filled_imm_tree() -> None:
    tree = deserialize_tree(
        {
            "Attributes": {},
            "Table": {},
            "Nodes": {
                "path-to-nta": {
                    "Attributes": {},
                    "Nodes": {
                        "na": {
                            "Attributes": {"Pairs": {"na0": "NA 0", "na1": "NA 1"}},
                            "Nodes": {},
                            "Table": {},
                        },
                        "nt": {
                            "Attributes": {},
                            "Nodes": {},
                            "Table": {
                                "KeyColumns": ["nt0"],
                                "Rows": [
                                    {"nt0": "NT 00", "nt1": "NT 01"},
                                    {"nt0": "NT 10", "nt1": "NT 11"},
                                ],
                            },
                        },
                        "ta": {
                            "Attributes": {"Pairs": {"ta0": "TA 0", "ta1": "TA 1"}},
                            "Nodes": {},
                            "Table": {
                                "KeyColumns": ["ta0"],
                                "Rows": [
                                    {"ta0": "TA 00", "ta1": "TA 01"},
                                    {"ta0": "TA 10", "ta1": "TA 11"},
                                ],
                            },
                        },
                    },
                    "Table": {},
                }
            },
        }
    )
    assert tree == filled_mutable_tree()
    assert tree == filled_immutable_tree()


def test_serialize_empty_delta_tree() -> None:
    assert serialize_delta_tree(compare_trees(empty_immutable_tree(), empty_immutable_tree())) == {
        "Attributes": {},
        "Table": {},
        "Nodes": {},
    }


def test_serialize_filled_delta_tree() -> None:
    raw_tree = serialize_delta_tree(compare_trees(empty_immutable_tree(), filled_immutable_tree()))
    assert not raw_tree["Attributes"]
    assert not raw_tree["Table"]
    assert not raw_tree["Nodes"][SDNodeName("path-to-nta")]["Attributes"]
    assert not raw_tree["Nodes"][SDNodeName("path-to-nta")]["Table"]

    assert raw_tree["Nodes"][SDNodeName("path-to-nta")]["Nodes"][SDNodeName("na")]["Attributes"][
        "Pairs"
    ] == {
        "na0": ("NA 0", None),
        "na1": ("NA 1", None),
    }
    assert not raw_tree["Nodes"][SDNodeName("path-to-nta")]["Nodes"][SDNodeName("na")]["Table"]
    assert not raw_tree["Nodes"][SDNodeName("path-to-nta")]["Nodes"][SDNodeName("na")]["Nodes"]

    assert not raw_tree["Nodes"][SDNodeName("path-to-nta")]["Nodes"][SDNodeName("nt")]["Attributes"]
    assert raw_tree["Nodes"][SDNodeName("path-to-nta")]["Nodes"][SDNodeName("nt")]["Table"][
        "KeyColumns"
    ] == ["nt0"]
    nt_rows = raw_tree["Nodes"][SDNodeName("path-to-nta")]["Nodes"][SDNodeName("nt")]["Table"][
        "Rows"
    ]
    assert len(nt_rows) == 2
    for row in [
        {"nt0": ("NT 00", None), "nt1": ("NT 01", None)},
        {"nt0": ("NT 10", None), "nt1": ("NT 11", None)},
    ]:
        assert row in nt_rows
    assert not raw_tree["Nodes"][SDNodeName("path-to-nta")]["Nodes"][SDNodeName("nt")]["Nodes"]

    assert raw_tree["Nodes"][SDNodeName("path-to-nta")]["Nodes"][SDNodeName("ta")]["Attributes"][
        "Pairs"
    ] == {
        "ta0": ("TA 0", None),
        "ta1": ("TA 1", None),
    }
    assert raw_tree["Nodes"][SDNodeName("path-to-nta")]["Nodes"][SDNodeName("ta")]["Table"][
        "KeyColumns"
    ] == ["ta0"]
    ta_rows = raw_tree["Nodes"][SDNodeName("path-to-nta")]["Nodes"][SDNodeName("ta")]["Table"][
        "Rows"
    ]
    assert len(ta_rows) == 2
    for row in [
        {"ta0": ("TA 00", None), "ta1": ("TA 01", None)},
        {"ta0": ("TA 10", None), "ta1": ("TA 11", None)},
    ]:
        assert row in ta_rows
    assert not raw_tree["Nodes"][SDNodeName("path-to-nta")]["Nodes"][SDNodeName("ta")]["Nodes"]


def test_deserialize_empty_delta_tree() -> None:
    assert len(ImmutableDeltaTree()) == 0


def test_deserialize_filled_delta_tree() -> None:
    delta_tree = deserialize_delta_tree(
        SDRawDeltaTree(
            Attributes={},
            Nodes={
                SDNodeName("path-to-nta"): SDRawDeltaTree(
                    Attributes={},
                    Nodes={
                        SDNodeName("na"): SDRawDeltaTree(
                            Attributes={
                                "Pairs": {
                                    SDKey("na0"): ("NA 0", None),
                                    SDKey("na1"): ("NA 1", None),
                                }
                            },
                            Nodes={},
                            Table={},
                        ),
                        SDNodeName("nt"): SDRawDeltaTree(
                            Attributes={},
                            Nodes={},
                            Table={
                                "KeyColumns": [SDKey("nt0")],
                                "Rows": [
                                    {SDKey("nt0"): ("NT 00", None), SDKey("nt1"): ("NT 01", None)},
                                    {SDKey("nt0"): ("NT 10", None), SDKey("nt1"): ("NT 11", None)},
                                ],
                            },
                        ),
                        SDNodeName("ta"): SDRawDeltaTree(
                            Attributes={
                                "Pairs": {
                                    SDKey("ta0"): ("TA 0", None),
                                    SDKey("ta1"): ("TA 1", None),
                                }
                            },
                            Nodes={},
                            Table={
                                "KeyColumns": [SDKey("ta0")],
                                "Rows": [
                                    {SDKey("ta0"): ("TA 00", None), SDKey("ta1"): ("TA 01", None)},
                                    {SDKey("ta0"): ("TA 10", None), SDKey("ta1"): ("TA 11", None)},
                                ],
                            },
                        ),
                    },
                    Table={},
                )
            },
            Table={},
        )
    )
    assert len(delta_tree) == 12
    stats = delta_tree.get_stats()
    assert stats["new"] == 0
    assert stats["changed"] == 0
    assert stats["removed"] == 12


def test_legacy_tree() -> None:
    raw_tree = {
        "path-to": {
            "idx-node": [
                {
                    "idx-attr": "value",
                    "idx-enum": ["v1", 1.0, 2, None],
                    "idx-table": [{"idx-col": "value"}],
                    "idx-sub-node": {
                        "foo-node": {
                            "foo-attr": "value",
                        },
                    },
                    "idx-sub-idx-node": [
                        {
                            "bar-node": {
                                "bar-attr": "value",
                            },
                        },
                    ],
                },
            ],
            "node": {"attr": "value"},
            "table": [{"col": "value"}],
        },
    }

    tree = deserialize_tree(raw_tree)

    idx_node_attr = tree.get_tree((SDNodeName("path-to"), SDNodeName("idx-node"), SDNodeName("0")))
    assert len(idx_node_attr) > 0
    assert idx_node_attr.attributes.pairs == {"idx-attr": "value", "idx-enum": "v1, 1.0, 2"}
    assert not idx_node_attr.table.rows_by_ident
    assert not idx_node_attr.table.rows

    idx_sub_idx_node_attr = tree.get_tree(
        (
            SDNodeName("path-to"),
            SDNodeName("idx-node"),
            SDNodeName("0"),
            SDNodeName("idx-sub-idx-node"),
            SDNodeName("0"),
            SDNodeName("bar-node"),
        )
    )
    assert len(idx_sub_idx_node_attr) > 0
    assert idx_sub_idx_node_attr.attributes.pairs == {"bar-attr": "value"}
    assert not idx_sub_idx_node_attr.table.rows_by_ident
    assert not idx_sub_idx_node_attr.table.rows

    idx_sub_node_attr = tree.get_tree(
        (
            SDNodeName("path-to"),
            SDNodeName("idx-node"),
            SDNodeName("0"),
            SDNodeName("idx-sub-node"),
            SDNodeName("foo-node"),
        )
    )
    assert len(idx_sub_node_attr) > 0
    assert idx_sub_node_attr.attributes.pairs == {"foo-attr": "value"}
    assert not idx_sub_node_attr.table.rows_by_ident
    assert not idx_sub_node_attr.table.rows

    idx_table = tree.get_tree(
        (SDNodeName("path-to"), SDNodeName("idx-node"), SDNodeName("0"), SDNodeName("idx-table"))
    )
    assert len(idx_table) > 0
    assert not idx_table.attributes.pairs
    assert idx_table.table.rows_by_ident == {("value",): {"idx-col": "value"}}
    assert idx_table.table.rows == [{"idx-col": "value"}]

    attr_node = tree.get_tree((SDNodeName("path-to"), SDNodeName("node")))
    assert len(attr_node) > 0
    assert attr_node.attributes.pairs == {"attr": "value"}
    assert not attr_node.table.rows_by_ident
    assert not attr_node.table.rows

    table_node = tree.get_tree((SDNodeName("path-to"), SDNodeName("table")))
    assert len(table_node) > 0
    assert not table_node.attributes.pairs
    assert table_node.table.rows_by_ident == {("value",): {"col": "value"}}
    assert table_node.table.rows == [{"col": "value"}]


@pytest.mark.parametrize(
    "raw_retention_interval, expected_retention_interval",
    [
        ((1, 2, 3), RetentionInterval(1, 2, 3, "current")),
        ((4, 5, 6, "previous"), RetentionInterval(4, 5, 6, "previous")),
        ((7, 8, 9, "current"), RetentionInterval(7, 8, 9, "current")),
    ],
)
def test_deserialize_retention_interval(
    raw_retention_interval: (
        tuple[int, int, int] | tuple[int, int, int, Literal["previous", "current"]]
    ),
    expected_retention_interval: RetentionInterval,
) -> None:
    assert deserialize_tree(
        {
            "Attributes": {"Retentions": {SDKey("key"): raw_retention_interval}},
            "Table": {},
            "Nodes": {},
        }
    ).attributes.retentions == {SDKey("key"): expected_retention_interval}


@pytest.mark.parametrize(
    "retention_interval, expected_raw_retention_interval",
    [
        (RetentionInterval(1, 2, 3, "previous"), (1, 2, 3, "previous")),
        (RetentionInterval(4, 5, 6, "current"), (4, 5, 6, "current")),
    ],
)
def test_serialize_retention_interval(
    retention_interval: RetentionInterval,
    expected_raw_retention_interval: tuple[int, int, int, Literal["previous", "current"]],
) -> None:
    assert serialize_tree(
        ImmutableTree(attributes=ImmutableAttributes(retentions={SDKey("key"): retention_interval}))
    )["Attributes"]["Retentions"] == {SDKey("key"): expected_raw_retention_interval}


def test_deserialize_delta_tree_with_attributes_key() -> None:
    raw_delta_tree = SDRawDeltaTree(
        Attributes={"Pairs": {SDKey("k"): (None, "v")}},
        Table={},
        Nodes={},
    )
    delta_tree = deserialize_delta_tree(raw_delta_tree)
    assert delta_tree.attributes.pairs[SDKey("k")].old is None
    assert delta_tree.attributes.pairs[SDKey("k")].new == "v"


def test_deserialize_tree_rejects_a_raw_tree_that_is_no_dict() -> None:
    with pytest.raises(TypeError):
        deserialize_tree(["Attributes", "Table", "Nodes"])


def test_legacy_tree_skips_an_empty_list() -> None:
    assert deserialize_tree({"empty": [], "attr": "value"}).attributes.pairs == {"attr": "value"}


def test_legacy_tree_rejects_an_unsupported_value() -> None:
    with pytest.raises(TypeError):
        deserialize_tree({"attr": ("tuple", "value")})
