#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import cmk.ccc.store
from cmk.inventory.transformation.__main__ import run

from ._fixtures import raw_tree
from ._logger import null_logger


@dataclass(frozen=True)
class FakeCollectHosts:
    host_names: Sequence[str]

    def __call__(self, _logger: logging.Logger, /) -> Sequence[str]:
        return self.host_names


def _save_legacy_inventory_trees(omd_root: Path, host_names: Sequence[str]) -> None:
    for host_name in host_names:
        cmk.ccc.store.save_object_to_file(
            omd_root / f"var/check_mk/inventory/{host_name}", raw_tree("val")
        )


def test_run_transforms_the_trees_of_the_given_host(tmp_path: Path) -> None:
    _save_legacy_inventory_trees(tmp_path, ["hostname"])

    run(
        ["cmk-transform-inventory-trees", "--host-name", "hostname"],
        omd_root=tmp_path,
        logger=null_logger(),
        collect_host_names=FakeCollectHosts(["hostname"]),
    )

    assert (tmp_path / "var/check_mk/inventory/hostname.json").exists()


def test_run_applies_the_bundle_length(tmp_path: Path) -> None:
    _save_legacy_inventory_trees(tmp_path, ["host1", "host2", "host3"])

    run(
        ["cmk-transform-inventory-trees", "--bundle-length", "2"],
        omd_root=tmp_path,
        logger=null_logger(),
        collect_host_names=FakeCollectHosts(["host1", "host2", "host3"]),
    )

    assert len(list((tmp_path / "var/check_mk/inventory").glob("*.json"))) == 2


def test_run_only_shows_the_results(tmp_path: Path) -> None:
    _save_legacy_inventory_trees(tmp_path, ["hostname"])

    run(
        ["cmk-transform-inventory-trees", "--show-results"],
        omd_root=tmp_path,
        logger=null_logger(),
        collect_host_names=FakeCollectHosts(["hostname"]),
    )

    assert (tmp_path / "var/check_mk/inventory/hostname").exists()


def test_run_exits_with_1_when_the_transformation_fails(tmp_path: Path) -> None:
    (tmp_path / "var/check_mk").mkdir(parents=True)
    (tmp_path / "var/check_mk/inventory").touch()

    assert (
        run(
            ["cmk-transform-inventory-trees"],
            omd_root=tmp_path,
            logger=null_logger(),
            collect_host_names=FakeCollectHosts(["hostname"]),
        )
        == 1
    )
