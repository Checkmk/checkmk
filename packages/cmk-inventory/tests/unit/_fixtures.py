#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import gzip
import io
import json

from cmk.inventory.store import make_meta, SDMetaAndRawTree
from cmk.inventory.structured_data import SDKey, SDNodeName, SDRawTree


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
