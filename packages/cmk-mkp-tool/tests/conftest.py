#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable
from dataclasses import astuple
from pathlib import Path

import pytest

from cmk.mkp_tool import Installer, PackageStore, PathConfig


@pytest.fixture(scope="function", name="path_config")
def fixture_path_config(tmp_path: Path) -> Iterable[PathConfig]:
    local_root = tmp_path / "local_root"
    path_congfig = PathConfig(
        cmk_plugins_dir=local_root / "cmk_plugins_dir",
        cmk_addons_plugins_dir=local_root / "cmk_addons_plugins_dir",
        agent_based_plugins_dir=local_root / "agent_based_plugins_dir",
        agents_dir=local_root / "agents_dir",
        alert_handlers_dir=local_root / "alert_handlers_dir",
        bin_dir=local_root / "bin_dir",
        check_manpages_dir=local_root / "legacy_check_manpages_dir",
        checks_dir=local_root / "checks_dir",
        doc_dir=local_root / "doc_dir",
        gui_plugins_dir=local_root / "gui_plugins_dir",
        inventory_dir=local_root / "inventory_dir",
        lib_dir=local_root / "lib_dir",
        locale_dir=local_root / "locale_dir",
        local_root=local_root,
        mib_dir=local_root / "mib_dir",
        mkp_rule_pack_dir=tmp_path / "mkp_rule_pack_dir",
        notifications_dir=local_root / "notifications_dir",
        pnp_templates_dir=local_root / "pnp_templates_dir",
        web_dir=local_root / "web_dir",
    )

    for path in astuple(path_congfig):
        Path(path).mkdir(parents=True, exist_ok=True)

    yield path_congfig


@pytest.fixture(scope="function", name="package_store")
def fixture_package_store(tmp_path: Path) -> PackageStore:
    local_root = tmp_path / "local_root"
    return PackageStore(
        shipped_dir=tmp_path / "optional_packages_dir",
        local_dir=local_root / "optional_packages_dir",
        enabled_dir=local_root / "enabled_packages_dir",
    )


@pytest.fixture(scope="function", name="installer")
def fixture_installer(tmp_path: Path) -> Installer:
    (install_dir := tmp_path / "installed_packages_dir").mkdir(parents=True, exist_ok=True)
    return Installer(install_dir)
