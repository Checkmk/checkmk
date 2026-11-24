#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Sequence
from pathlib import Path

import pytest

import cmk.ccc.store
from cmk.ccc.hostaddress import HostName
from cmk.inventory.history import HistoryStore
from cmk.inventory.store import InventoryStore
from cmk.inventory.transformation.tree_files import (
    _compute_bundle_size,
    show_transformation_results,
    transform_inventory_trees,
    TransformationResult,
    TransformationResultsStore,
)

from ._fixtures import (
    file_names,
    gzipped_repr,
    raw_tree,
    TABLE_RETENTIONS,
    tree_with_table_retentions,
)
from ._logger import null_logger


class FakeClock:
    def __init__(self, *times: float) -> None:
        self._times = list(times)

    def __call__(self) -> float:
        return self._times.pop(0) if len(self._times) > 1 else self._times[0]


def test_transform_replaces_the_legacy_inventory_trees(tmp_path: Path) -> None:
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
        clock=FakeClock(0.0),
    )

    assert file_names(tmp_path / "var/check_mk/inventory") == ["hostname.json", "hostname.json.gz"]


def test_transform_replaces_the_legacy_status_data_tree(tmp_path: Path) -> None:
    tree = raw_tree("val")
    cmk.ccc.store.save_object_to_file(tmp_path / "tmp/check_mk/status_data/hostname", tree)

    transform_inventory_trees(
        logger=null_logger(),
        omd_root=tmp_path,
        bundle_length=0,
        filter_host_names=["hostname"],
        all_host_names=["hostname"],
        clock=FakeClock(0.0),
    )

    assert file_names(tmp_path / "tmp/check_mk/status_data") == ["hostname.json"]


def test_transform_replaces_the_legacy_archive_tree(tmp_path: Path) -> None:
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
        clock=FakeClock(0.0),
    )

    assert file_names(tmp_path / "var/check_mk/inventory_archive/hostname") == ["123.json"]


def test_transform_replaces_the_legacy_delta_cache_tree(tmp_path: Path) -> None:
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
        clock=FakeClock(0.0),
    )

    assert file_names(tmp_path / "var/check_mk/inventory_delta_cache/hostname") == ["123_456.json"]


def _transform_all_trees_of_hostname(omd_root: Path) -> None:
    transform_inventory_trees(
        logger=null_logger(),
        omd_root=omd_root,
        bundle_length=0,
        filter_host_names=["hostname"],
        all_host_names=["hostname"],
        clock=FakeClock(0.0),
    )


def test_transform_archive_tree_keeps_the_table_retentions(tmp_path: Path) -> None:
    cmk.ccc.store.save_object_to_file(
        tmp_path / "var/check_mk/inventory_archive/hostname/123", tree_with_table_retentions()
    )
    _transform_all_trees_of_hostname(tmp_path)
    assert (
        InventoryStore(tmp_path)
        .load_previous_inventory_tree(host_name=HostName("hostname"))
        .table.retentions
        == TABLE_RETENTIONS
    )


def test_transform_delta_cache_tree_keeps_the_delta(tmp_path: Path) -> None:
    cmk.ccc.store.save_object_to_file(
        tmp_path / "var/check_mk/inventory_delta_cache/hostname/123_456",
        (1, 0, 0, {"Attributes": {"Pairs": {"key": (None, "val")}}, "Table": {}, "Nodes": {}}),
    )
    _transform_all_trees_of_hostname(tmp_path)
    assert [
        (e.new, e.changed, e.removed)
        for e in HistoryStore(tmp_path).load(HostName("hostname"), delta_tree_filters=None).entries
    ] == [(1, 0, 0)]


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
        clock=FakeClock(0.0),
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
        clock=FakeClock(0.0),
    )

    assert len(list((tmp_path / "var/check_mk/inventory").glob("*.json"))) == 1


def test_the_bundle_spreads_all_trees_including_the_transformed_ones() -> None:
    assert _compute_bundle_size(0, 400, 600) == 5


def test_a_tree_failing_to_transform_leaves_its_slot_to_the_next_tree(tmp_path: Path) -> None:
    cmk.ccc.store.save_object_to_file(
        tmp_path / "var/check_mk/inventory/broken",
        {"not", "a", "tree"},
    )
    _save_legacy_inventory_trees(tmp_path, ["hostname"])

    transform_inventory_trees(
        logger=null_logger(),
        omd_root=tmp_path,
        bundle_length=1,
        filter_host_names=[],
        all_host_names=["broken", "hostname"],
        clock=FakeClock(0.0),
    )

    assert (tmp_path / "var/check_mk/inventory/hostname.json").exists()


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
        clock=FakeClock(0.0),
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
        clock=FakeClock(0.0),
    )

    assert (tmp_path / "var/check_mk/inventory_archive/hostname/123.json").exists()


@pytest.mark.parametrize(
    "size, rendered_size",
    [
        pytest.param(500, "500 B", id="bytes"),
        pytest.param(1_500, "1.50 KB", id="kilobytes"),
        pytest.param(1_500_000, "1.50 MB", id="megabytes"),
        pytest.param(1_500_000_000, "1.50 GB", id="gigabytes"),
    ],
)
def test_show_transformation_results_renders_the_size(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], size: int, rendered_size: str
) -> None:
    TransformationResultsStore(tmp_path).save(
        [TransformationResult(host_name="hostname", path="a/path", duration=1.5, size=size)]
    )

    show_transformation_results(omd_root=tmp_path, filter_host_names=[], all_host_names=[])

    assert f"Size: {rendered_size}\n" in capsys.readouterr().out


def test_transform_records_the_precise_duration(tmp_path: Path) -> None:
    _save_legacy_inventory_trees(tmp_path, ["hostname"])

    transform_inventory_trees(
        logger=null_logger(),
        omd_root=tmp_path,
        bundle_length=0,
        filter_host_names=[],
        all_host_names=["hostname"],
        clock=FakeClock(10.0, 10.25),
    )

    assert [r["duration"] for r in TransformationResultsStore(tmp_path).load()] == [0.25]
