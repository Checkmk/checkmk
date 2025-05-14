#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import gzip
import io
from pathlib import Path

import cmk.ccc.store

from cmk.utils.structured_data import (
    make_meta,
    SDKey,
    SDMetaAndRawTree,
    SDNodeName,
    SDRawTree,
)

from cmk.inventory.transformation import transform_inventory_trees


def test_transformation_nothing_to_do(tmp_path: Path) -> None:
    transform_inventory_trees(
        omd_root=tmp_path,
        show_results=False,
        bundle_length=0,
        filter_host_names=[],
        all_host_names=[],
    )


def _raw_tree() -> SDRawTree:
    return SDRawTree(
        Attributes={"Pairs": {SDKey("key"): "val"}},
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


def _gzipped_repr(raw_tree: SDRawTree) -> bytes:
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb") as f:
        f.write(
            (
                repr(SDMetaAndRawTree(meta=make_meta(do_archive=False), raw_tree=raw_tree)) + "\n"
            ).encode("utf-8")
        )
    return buf.getvalue()


def test_transform_inventory_tree(tmp_path: Path) -> None:
    raw_tree = _raw_tree()
    gzipped = _gzipped_repr(raw_tree)
    cmk.ccc.store.save_object_to_file(tmp_path / "var/check_mk/inventory/hostname", raw_tree)
    cmk.ccc.store.save_bytes_to_file(tmp_path / "var/check_mk/inventory/hostname.gz", gzipped)

    transform_inventory_trees(
        omd_root=tmp_path,
        show_results=False,
        bundle_length=0,
        filter_host_names=["hostname"],
        all_host_names=["hostname"],
    )

    assert not (tmp_path / "var/check_mk/inventory/hostname").exists()
    assert not (tmp_path / "var/check_mk/inventory/hostname.gz").exists()
    assert (tmp_path / "var/check_mk/inventory/hostname.json").exists()
    assert (tmp_path / "var/check_mk/inventory/hostname.json.gz").exists()


def test_transform_status_data_tree(tmp_path: Path) -> None:
    raw_tree = _raw_tree()
    cmk.ccc.store.save_object_to_file(tmp_path / "tmp/check_mk/status_data/hostname", raw_tree)

    transform_inventory_trees(
        omd_root=tmp_path,
        show_results=False,
        bundle_length=0,
        filter_host_names=["hostname"],
        all_host_names=["hostname"],
    )

    assert not (tmp_path / "tmp/check_mk/status_data/hostname").exists()
    assert (tmp_path / "tmp/check_mk/status_data/hostname.json").exists()


def test_transform_archive_tree(tmp_path: Path) -> None:
    raw_tree = _raw_tree()
    cmk.ccc.store.save_object_to_file(
        tmp_path / "var/check_mk/inventory_archive/hostname/123", raw_tree
    )

    transform_inventory_trees(
        omd_root=tmp_path,
        show_results=False,
        bundle_length=0,
        filter_host_names=["hostname"],
        all_host_names=["hostname"],
    )

    assert not (tmp_path / "var/check_mk/inventory_archive/hostname/123").exists()
    assert (tmp_path / "var/check_mk/inventory_archive/hostname/123.json").exists()


def test_transform_delta_cache_tree(tmp_path: Path) -> None:
    raw_tree = _raw_tree()
    cmk.ccc.store.save_object_to_file(
        tmp_path / "var/check_mk/inventory_delta_cache/hostname/123_456", raw_tree
    )

    transform_inventory_trees(
        omd_root=tmp_path,
        show_results=False,
        bundle_length=0,
        filter_host_names=["hostname"],
        all_host_names=["hostname"],
    )

    assert not (tmp_path / "var/check_mk/inventory_delta_cache/hostname/123_456").exists()
    assert (tmp_path / "var/check_mk/inventory_delta_cache/hostname/123_456.json").exists()
