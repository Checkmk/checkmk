#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import gzip
import io
import json
from collections.abc import Sequence
from pathlib import Path

from cmk.inventory.serialization import (
    make_meta,
    SDMetaAndRawTree,
    SDRawTree,
)
from cmk.inventory.store import InventoryStore
from cmk.inventory.trees import SDKey, SDNodeName


def file_names(directory: Path) -> Sequence[str]:
    return sorted(p.name for p in directory.iterdir())


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
