#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Sequence
from pathlib import Path

import cmk.ccc.store
from cmk.inventory.transformation.tree_files import (
    show_transformation_results,
    transform_inventory_trees,
    TransformationResult,
    TransformationResultsStore,
)

from ._fixtures import gzipped_repr, raw_tree
from ._logger import null_logger


def test_transformation_nothing_to_do(tmp_path: Path) -> None:
    transform_inventory_trees(
        logger=null_logger(),
        omd_root=tmp_path,
        bundle_length=0,
        filter_host_names=[],
        all_host_names=[],
    )


def test_transform_inventory_tree(tmp_path: Path) -> None:
    tree = raw_tree("val")
    gzipped = gzipped_repr(tree)
    cmk.ccc.store.save_object_to_file(tmp_path / "var/check_mk/inventory/hostname", tree)
    cmk.ccc.store.save_bytes_to_file(tmp_path / "var/check_mk/inventory/hostname.gz", gzipped)

    transform_inventory_trees(
        logger=null_logger(),
        omd_root=tmp_path,
        bundle_length=0,
        filter_host_names=["hostname"],
        all_host_names=["hostname"],
    )

    assert not (tmp_path / "var/check_mk/inventory/hostname").exists()
    assert not (tmp_path / "var/check_mk/inventory/hostname.gz").exists()
    assert (tmp_path / "var/check_mk/inventory/hostname.json").exists()
    assert (tmp_path / "var/check_mk/inventory/hostname.json.gz").exists()


def test_transform_status_data_tree(tmp_path: Path) -> None:
    tree = raw_tree("val")
    cmk.ccc.store.save_object_to_file(tmp_path / "tmp/check_mk/status_data/hostname", tree)

    transform_inventory_trees(
        logger=null_logger(),
        omd_root=tmp_path,
        bundle_length=0,
        filter_host_names=["hostname"],
        all_host_names=["hostname"],
    )

    assert not (tmp_path / "tmp/check_mk/status_data/hostname").exists()
    assert (tmp_path / "tmp/check_mk/status_data/hostname.json").exists()


def test_transform_archive_tree(tmp_path: Path) -> None:
    tree = raw_tree("val")
    cmk.ccc.store.save_object_to_file(
        tmp_path / "var/check_mk/inventory_archive/hostname/123", tree
    )

    transform_inventory_trees(
        logger=null_logger(),
        omd_root=tmp_path,
        bundle_length=0,
        filter_host_names=["hostname"],
        all_host_names=["hostname"],
    )

    assert not (tmp_path / "var/check_mk/inventory_archive/hostname/123").exists()
    assert (tmp_path / "var/check_mk/inventory_archive/hostname/123.json").exists()


def test_transform_delta_cache_tree(tmp_path: Path) -> None:
    tree = raw_tree("val")
    cmk.ccc.store.save_object_to_file(
        tmp_path / "var/check_mk/inventory_delta_cache/hostname/123_456", tree
    )

    transform_inventory_trees(
        logger=null_logger(),
        omd_root=tmp_path,
        bundle_length=0,
        filter_host_names=["hostname"],
        all_host_names=["hostname"],
    )

    assert not (tmp_path / "var/check_mk/inventory_delta_cache/hostname/123_456").exists()
    assert (tmp_path / "var/check_mk/inventory_delta_cache/hostname/123_456.json").exists()


def test_transformation_results_store_is_empty_without_a_file(tmp_path: Path) -> None:
    assert not TransformationResultsStore(tmp_path).load()


def test_transformation_results_store_reads_back_what_it_saved(tmp_path: Path) -> None:
    results = [TransformationResult(host_name="hostname", path="a/path", duration=1.5, size=23)]
    store = TransformationResultsStore(tmp_path)
    store.save(results)
    assert list(store.load()) == results


def test_show_transformation_results_leaves_the_legacy_tree(tmp_path: Path) -> None:
    cmk.ccc.store.save_object_to_file(tmp_path / "var/check_mk/inventory/hostname", raw_tree("val"))

    show_transformation_results(
        omd_root=tmp_path,
        filter_host_names=["hostname"],
        all_host_names=["hostname"],
    )

    assert (tmp_path / "var/check_mk/inventory/hostname").exists()


def _save_legacy_inventory_trees(omd_root: Path, host_names: Sequence[str]) -> None:
    for host_name in host_names:
        cmk.ccc.store.save_object_to_file(
            omd_root / f"var/check_mk/inventory/{host_name}", raw_tree("val")
        )


def test_the_bundle_length_limits_the_transformed_trees(tmp_path: Path) -> None:
    _save_legacy_inventory_trees(tmp_path, ["host1", "host2", "host3"])

    transform_inventory_trees(
        logger=null_logger(),
        omd_root=tmp_path,
        bundle_length=2,
        filter_host_names=[],
        all_host_names=["host1", "host2", "host3"],
    )

    assert len(list((tmp_path / "var/check_mk/inventory").glob("*.json"))) == 2


def test_without_a_bundle_length_at_least_one_tree_is_transformed(tmp_path: Path) -> None:
    _save_legacy_inventory_trees(tmp_path, ["host1", "host2"])

    transform_inventory_trees(
        logger=null_logger(),
        omd_root=tmp_path,
        bundle_length=0,
        filter_host_names=[],
        all_host_names=["host1", "host2"],
    )

    assert len(list((tmp_path / "var/check_mk/inventory").glob("*.json"))) == 1


def test_a_transformed_tree_is_not_overwritten_by_its_legacy_tree(tmp_path: Path) -> None:
    cmk.ccc.store.save_object_to_file(tmp_path / "var/check_mk/inventory/hostname", raw_tree("old"))
    cmk.ccc.store.save_text_to_file(
        tmp_path / "var/check_mk/inventory/hostname.json", json.dumps(raw_tree("new"))
    )

    transform_inventory_trees(
        logger=null_logger(),
        omd_root=tmp_path,
        bundle_length=0,
        filter_host_names=["hostname"],
        all_host_names=["hostname"],
    )

    assert json.loads((tmp_path / "var/check_mk/inventory/hostname.json").read_text()) == raw_tree(
        "new"
    )


def test_a_stray_file_in_the_archive_directory_is_skipped(tmp_path: Path) -> None:
    (tmp_path / "var/check_mk/inventory_archive").mkdir(parents=True)
    (tmp_path / "var/check_mk/inventory_archive/stray-file").touch()
    cmk.ccc.store.save_object_to_file(
        tmp_path / "var/check_mk/inventory_archive/hostname/123", raw_tree("val")
    )

    transform_inventory_trees(
        logger=null_logger(),
        omd_root=tmp_path,
        bundle_length=0,
        filter_host_names=["hostname"],
        all_host_names=["hostname"],
    )

    assert (tmp_path / "var/check_mk/inventory_archive/hostname/123.json").exists()
