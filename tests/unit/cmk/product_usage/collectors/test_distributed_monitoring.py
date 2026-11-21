#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from pathlib import Path

import pytest

import cmk.product_usage.collectors.distributed_monitoring as distributed_monitoring_collector
from cmk.ccc import store
from cmk.product_usage.schema import DistributedMonitoring


def test_site_that_the_central_site_configures_is_a_remote_setup_site(tmp_path: Path) -> None:
    _write_distributed_wato_file(tmp_path, is_remote=True)
    _write_sites(tmp_path, {"remote": {"replication": None}})

    distributed_monitoring = _collect(tmp_path)

    assert distributed_monitoring == DistributedMonitoring(is_remote_setup_site=True)


@pytest.mark.parametrize(
    "is_remote",
    [
        pytest.param(False, id="central site"),
        pytest.param(True, id="former remote site that became a central site"),
    ],
)
def test_site_that_configures_remote_sites_is_no_remote_setup_site(
    tmp_path: Path, is_remote: bool
) -> None:
    _write_distributed_wato_file(tmp_path, is_remote=is_remote)
    _write_sites(tmp_path, {"central": {"replication": None}, "remote": {"replication": "slave"}})

    distributed_monitoring = _collect(tmp_path)

    assert distributed_monitoring == DistributedMonitoring(is_remote_setup_site=False)


def test_standalone_site_is_no_remote_setup_site(tmp_path: Path) -> None:
    distributed_monitoring = _collect(tmp_path)

    assert distributed_monitoring == DistributedMonitoring(is_remote_setup_site=False)


def test_central_site_without_remote_sites_is_no_remote_setup_site(tmp_path: Path) -> None:
    (tmp_path / "conf.d").mkdir()
    # A central site empties its file when it no longer configures any remote site
    (tmp_path / "conf.d/distributed_wato.mk").write_text("")

    distributed_monitoring = _collect(tmp_path)

    assert distributed_monitoring == DistributedMonitoring(is_remote_setup_site=False)


def _collect(site_dir: Path) -> DistributedMonitoring:
    return distributed_monitoring_collector.collect(
        default_config_dir=site_dir, cmk_config_dir=site_dir / "conf.d"
    )


def _write_distributed_wato_file(default_config_dir: Path, *, is_remote: bool) -> None:
    """Write the file in the format of a configuration push"""
    path = default_config_dir / "conf.d/distributed_wato.mk"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"distributed_wato_site = 'mysite'\nis_distributed_setup_remote_site = {is_remote!r}\n"
    )


def _write_sites(default_config_dir: Path, sites: Mapping[str, Mapping[str, object]]) -> None:
    """Write the sites in the format of the GUI's site store, shortened to what is read"""
    path = default_config_dir / "multisite.d/sites.mk"
    path.parent.mkdir(parents=True, exist_ok=True)
    store.save_to_mk_file(path, key="sites", value=sites)
