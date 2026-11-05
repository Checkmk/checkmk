#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import gzip
import json
from collections.abc import Mapping
from typing import Literal

import pytest

from cmk.inventory.delta import compare_trees, ImmutableDeltaTree, SDDeltaValue
from cmk.inventory.serialization import (
    deserialize_delta_cache_entry,
    deserialize_delta_tree,
    deserialize_tree,
    parse_from_gzipped,
    parse_from_raw_status_data_tree,
    SDMeta,
    SDMetaAndRawTree,
    SDRawDeltaTree,
    SDRawTree,
    serialize_delta_cache_entry,
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
    filled_delta_tree,
    filled_immutable_tree,
    filled_mutable_tree,
    immutable_tree,
    raw_tree,
)


def test_serialize_empty_mut_tree() -> None:
    assert serialize_tree(empty_mutable_tree()) == {"Attributes": {}, "Table": {}, "Nodes": {}}


_FILLED_RAW_TREE: Mapping[str, object] = {
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


def test_serialize_filled_mutable_tree() -> None:
    assert serialize_tree(filled_mutable_tree()) == _FILLED_RAW_TREE


@pytest.mark.parametrize(
    "tree",
    [pytest.param(MutableTree(), id="mutable"), pytest.param(ImmutableTree(), id="immutable")],
)
def test_deserialize_an_empty_raw_tree(tree: MutableTree | ImmutableTree) -> None:
    assert deserialize_tree({}) == tree


@pytest.mark.parametrize(
    "tree",
    [
        pytest.param(filled_mutable_tree(), id="mutable"),
        pytest.param(filled_immutable_tree(), id="immutable"),
    ],
)
def test_deserialize_a_filled_raw_tree(tree: MutableTree | ImmutableTree) -> None:
    assert deserialize_tree(_FILLED_RAW_TREE) == tree


def test_serialize_empty_delta_tree() -> None:
    assert serialize_delta_tree(compare_trees(empty_immutable_tree(), empty_immutable_tree())) == {
        "Attributes": {},
        "Table": {},
        "Nodes": {},
    }


_FILLED_RAW_DELTA_TREE = SDRawDeltaTree(
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


def test_serialize_a_compared_delta_tree() -> None:
    tree = MutableTree()
    tree.add(
        path=(SDNodeName("node"),),
        pairs=[{SDKey("key"): "value"}],
        key_columns=[SDKey("col0")],
        rows=[{SDKey("col0"): "value 0", SDKey("col1"): "value 1"}],
    )

    assert serialize_delta_tree(
        compare_trees(ImmutableTree(), immutable_tree(tree))
    ) == SDRawDeltaTree(
        Attributes={},
        Table={},
        Nodes={
            SDNodeName("node"): SDRawDeltaTree(
                Attributes={"Pairs": {SDKey("key"): ("value", None)}},
                Table={
                    "KeyColumns": [SDKey("col0")],
                    "Rows": [{SDKey("col0"): ("value 0", None), SDKey("col1"): ("value 1", None)}],
                },
                Nodes={},
            )
        },
    )


def test_serialize_a_deserialized_delta_tree_gives_the_raw_tree_back() -> None:
    assert (
        serialize_delta_tree(deserialize_delta_tree(_FILLED_RAW_DELTA_TREE))
        == _FILLED_RAW_DELTA_TREE
    )


def test_deserialize_empty_delta_tree() -> None:
    assert len(ImmutableDeltaTree()) == 0


def test_deserialize_a_filled_raw_delta_tree() -> None:
    delta_tree = deserialize_delta_tree(_FILLED_RAW_DELTA_TREE)
    stats = delta_tree.get_stats()
    assert (len(delta_tree), stats["new"], stats["changed"], stats["removed"]) == (12, 0, 0, 12)


def test_deserialize_a_legacy_tree() -> None:
    raw: Mapping[str, object] = serialize_tree(
        deserialize_tree(
            {
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
        )
    )
    assert raw == {
        "Attributes": {},
        "Table": {},
        "Nodes": {
            "path-to": {
                "Attributes": {},
                "Table": {},
                "Nodes": {
                    "idx-node": {
                        "Attributes": {},
                        "Table": {},
                        "Nodes": {
                            "0": {
                                "Attributes": {
                                    "Pairs": {"idx-attr": "value", "idx-enum": "v1, 1.0, 2"}
                                },
                                "Table": {},
                                "Nodes": {
                                    "idx-table": {
                                        "Attributes": {},
                                        "Table": {
                                            "KeyColumns": ["idx-col"],
                                            "Rows": [{"idx-col": "value"}],
                                        },
                                        "Nodes": {},
                                    },
                                    "idx-sub-node": {
                                        "Attributes": {},
                                        "Table": {},
                                        "Nodes": {
                                            "foo-node": {
                                                "Attributes": {"Pairs": {"foo-attr": "value"}},
                                                "Table": {},
                                                "Nodes": {},
                                            }
                                        },
                                    },
                                    "idx-sub-idx-node": {
                                        "Attributes": {},
                                        "Table": {},
                                        "Nodes": {
                                            "0": {
                                                "Attributes": {},
                                                "Table": {},
                                                "Nodes": {
                                                    "bar-node": {
                                                        "Attributes": {
                                                            "Pairs": {"bar-attr": "value"}
                                                        },
                                                        "Table": {},
                                                        "Nodes": {},
                                                    }
                                                },
                                            }
                                        },
                                    },
                                },
                            }
                        },
                    },
                    "node": {"Attributes": {"Pairs": {"attr": "value"}}, "Table": {}, "Nodes": {}},
                    "table": {
                        "Attributes": {},
                        "Table": {"KeyColumns": ["col"], "Rows": [{"col": "value"}]},
                        "Nodes": {},
                    },
                },
            }
        },
    }


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
    assert deserialize_delta_tree(raw_delta_tree).attributes.pairs == {
        SDKey("k"): SDDeltaValue(old=None, new="v")
    }


def test_deserialize_tree_rejects_a_raw_tree_that_is_no_dict() -> None:
    with pytest.raises(TypeError):
        deserialize_tree(["Attributes", "Table", "Nodes"])


def test_legacy_tree_skips_an_empty_list() -> None:
    assert deserialize_tree({"empty": [], "attr": "value"}).attributes.pairs == {"attr": "value"}


def test_legacy_tree_rejects_an_unsupported_value() -> None:
    with pytest.raises(TypeError):
        deserialize_tree({"attr": ("tuple", "value")})


@pytest.mark.parametrize(
    "raw, expected",
    [
        pytest.param(
            {"Attributes": {}, "Table": {}, "Nodes": {}},
            SDMetaAndRawTree(
                meta=SDMeta(version="1", do_archive=True),
                raw_tree=SDRawTree(Attributes={}, Table={}, Nodes={}),
            ),
            id="missing-version:missing-meta",
        ),
        pytest.param(
            {
                "meta_version": "0",
                "meta_do_archive": True,
                "Attributes": {},
                "Table": {},
                "Nodes": {},
            },
            SDMetaAndRawTree(
                meta=SDMeta(version="1", do_archive=True),
                raw_tree=SDRawTree(Attributes={}, Table={}, Nodes={}),
            ),
            id="version=0:do-archive",
        ),
        pytest.param(
            {
                "meta_version": "0",
                "meta_do_archive": False,
                "Attributes": {},
                "Table": {},
                "Nodes": {},
            },
            SDMetaAndRawTree(
                meta=SDMeta(version="1", do_archive=False),
                raw_tree=SDRawTree(Attributes={}, Table={}, Nodes={}),
            ),
            id="version=0:do-not-archive",
        ),
        pytest.param(
            {
                "meta": {"version": "1", "do_archive": True},
                "raw_tree": {"Attributes": {}, "Table": {}, "Nodes": {}},
            },
            SDMetaAndRawTree(
                meta=SDMeta(version="1", do_archive=True),
                raw_tree=SDRawTree(Attributes={}, Table={}, Nodes={}),
            ),
            id="version=1:do-archive",
        ),
        pytest.param(
            {
                "meta": {"version": "1", "do_archive": False},
                "raw_tree": {"Attributes": {}, "Table": {}, "Nodes": {}},
            },
            SDMetaAndRawTree(
                meta=SDMeta(version="1", do_archive=False),
                raw_tree=SDRawTree(Attributes={}, Table={}, Nodes={}),
            ),
            id="version=1:do-archive",
        ),
    ],
)
def test_parse_from_gzipped(raw: Mapping[str, object], expected: SDMetaAndRawTree) -> None:
    assert parse_from_gzipped(gzip.compress(json.dumps(raw).encode())) == expected


def test_parse_from_raw_status_data_tree() -> None:
    tree = raw_tree("val")
    assert parse_from_raw_status_data_tree(json.dumps(tree).encode()) == deserialize_tree(tree)


def test_parse_from_raw_status_data_tree_legacy() -> None:
    tree = raw_tree("val")
    assert parse_from_raw_status_data_tree(repr(tree).encode()) == deserialize_tree(tree)


@pytest.mark.parametrize(
    "raw",
    [
        pytest.param(["Attributes", "Table", "Nodes"], id="no-dict"),
        pytest.param({"meta": "1", "raw_tree": {}}, id="meta-no-dict"),
        pytest.param(
            {"meta": {"version": 1, "do_archive": True}, "raw_tree": {}}, id="version-no-str"
        ),
        pytest.param(
            {"meta": {"version": "1", "do_archive": 1}, "raw_tree": {}}, id="do-archive-no-bool"
        ),
        pytest.param(
            {"meta": {"version": "1", "do_archive": True}, "raw_tree": []}, id="raw-tree-no-dict"
        ),
    ],
)
def test_parse_from_gzipped_rejects_a_malformed_tree(raw: object) -> None:
    with pytest.raises(TypeError):
        parse_from_gzipped(gzip.compress(json.dumps(raw).encode()))


def test_parse_from_gzipped_rejects_an_unknown_version() -> None:
    with pytest.raises(ValueError):
        parse_from_gzipped(
            gzip.compress(
                json.dumps({"meta": {"version": "2", "do_archive": True}, "raw_tree": {}}).encode()
            )
        )


def test_delta_cache_entry_round_trip() -> None:
    delta_tree = filled_delta_tree()
    assert deserialize_delta_cache_entry(
        serialize_delta_cache_entry(new=1, changed=2, removed=3, delta_tree=delta_tree)
    ) == (1, 2, 3, delta_tree)
