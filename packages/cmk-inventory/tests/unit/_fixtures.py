#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import gzip
import io
import json
from pathlib import Path

from cmk.inventory.serialization import (
    deserialize_delta_tree,
    deserialize_tree,
    SDRawDeltaTree,
    SDRawTree,
    serialize_tree,
)
from cmk.inventory.store import InventoryStore, make_meta, SDMetaAndRawTree
from cmk.inventory.structured_data import (
    ImmutableDeltaTree,
    ImmutableTree,
    MutableTree,
    SDKey,
    SDNodeName,
)


def inventory_store() -> InventoryStore:
    return InventoryStore(Path(__file__).parent / "tree_test_data")


def raw_tree(value: str) -> SDRawTree:
    return SDRawTree(
        Attributes={"Pairs": {SDKey("key"): value}},
        Table={
            "KeyColumns": [SDKey("col1")],
            "Rows": [
                {SDKey("col1"): "val11", SDKey("col2"): "val12"},
                {SDKey("col1"): "val21", SDKey("col2"): "val22"},
            ],
        },
        Nodes={
            SDNodeName("node"): SDRawTree(
                Attributes={"Pairs": {SDKey("nkey"): "nval"}},
                Table={
                    "KeyColumns": [SDKey("ncol1")],
                    "Rows": [
                        {SDKey("ncol1"): "nval11", SDKey("ncol2"): "nval12"},
                        {SDKey("ncol1"): "nval21", SDKey("ncol2"): "nval22"},
                    ],
                },
                Nodes={},
            ),
        },
    )


def gzipped_repr(raw_tree: SDRawTree) -> bytes:
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb") as f:
        f.write(
            (
                repr(SDMetaAndRawTree(meta=make_meta(do_archive=False), raw_tree=raw_tree)) + "\n"
            ).encode("utf-8")
        )
    return buf.getvalue()


def gzipped_json(raw_tree: SDRawTree) -> bytes:
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb") as f:
        f.write(
            (
                json.dumps(SDMetaAndRawTree(meta=make_meta(do_archive=False), raw_tree=raw_tree))
                + "\n"
            ).encode("utf-8")
        )
    return buf.getvalue()


def immutable_tree(tree: MutableTree) -> ImmutableTree:
    return deserialize_tree(serialize_tree(tree))


def empty_mutable_tree() -> MutableTree:
    root = MutableTree()
    root.add(path=(SDNodeName("path-to-nta"), SDNodeName("nt")))
    root.add(path=(SDNodeName("path-to-nta"), SDNodeName("na")))
    root.add(path=(SDNodeName("path-to-nta"), SDNodeName("ta")))
    return root


def empty_immutable_tree() -> ImmutableTree:
    return deserialize_tree(
        {
            "Attributes": {},
            "Table": {},
            "Nodes": {
                "path-to-nta": {
                    "Attributes": {},
                    "Table": {},
                    "Nodes": {
                        "na": {"Attributes": {}, "Table": {}, "Nodes": {}},
                        "nt": {"Attributes": {}, "Table": {}, "Nodes": {}},
                        "ta": {"Attributes": {}, "Table": {}, "Nodes": {}},
                    },
                }
            },
        }
    )


def filled_mutable_tree() -> MutableTree:
    root = MutableTree()
    root.add(
        path=(SDNodeName("path-to-nta"), SDNodeName("nt")),
        key_columns=[SDKey("nt0")],
        rows=[
            {SDKey("nt0"): "NT 00", SDKey("nt1"): "NT 01"},
            {SDKey("nt0"): "NT 10", SDKey("nt1"): "NT 11"},
        ],
    )
    root.add(
        path=(SDNodeName("path-to-nta"), SDNodeName("na")),
        pairs=[{SDKey("na0"): "NA 0", SDKey("na1"): "NA 1"}],
    )
    root.add(
        path=(SDNodeName("path-to-nta"), SDNodeName("ta")),
        pairs=[{SDKey("ta0"): "TA 0", SDKey("ta1"): "TA 1"}],
        key_columns=[SDKey("ta0")],
        rows=[
            {SDKey("ta0"): "TA 00", SDKey("ta1"): "TA 01"},
            {SDKey("ta0"): "TA 10", SDKey("ta1"): "TA 11"},
        ],
    )
    return root


def filled_immutable_tree() -> ImmutableTree:
    return immutable_tree(filled_mutable_tree())


def filled_delta_tree() -> ImmutableDeltaTree:
    return deserialize_delta_tree(
        SDRawDeltaTree(
            Attributes={},
            Nodes={
                SDNodeName("path-to-nta"): SDRawDeltaTree(
                    Attributes={},
                    Nodes={
                        SDNodeName("na"): SDRawDeltaTree(
                            Attributes={
                                "Pairs": {
                                    SDKey("na0"): (None, "NA 0"),
                                    SDKey("na1"): (None, "NA 1"),
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
                                    {SDKey("nt0"): (None, "NT 00"), SDKey("nt1"): (None, "NT 01")},
                                    {SDKey("nt0"): (None, "NT 10"), SDKey("nt1"): (None, "NT 11")},
                                ],
                            },
                        ),
                        SDNodeName("ta"): SDRawDeltaTree(
                            Attributes={
                                "Pairs": {
                                    SDKey("ta0"): (None, "TA 0"),
                                    SDKey("ta1"): (None, "TA 1"),
                                }
                            },
                            Nodes={},
                            Table={
                                "KeyColumns": [SDKey("ta0")],
                                "Rows": [
                                    {SDKey("ta0"): (None, "TA 00"), SDKey("ta1"): (None, "TA 01")},
                                    {SDKey("ta0"): (None, "TA 10"), SDKey("ta1"): (None, "TA 11")},
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
