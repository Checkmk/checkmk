#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from collections.abc import Iterator

import pytest

import cmk.utils.paths
from cmk.gui.watolib.sites import site_management_registry
from cmk.update_config.lib import ExpiryVersion
from cmk.update_config.plugins.actions.initialize_site_configuration import (
    InitializeSiteConfiguration,
)


@pytest.fixture
def move_sites_mk_out_of_the_way() -> Iterator[None]:
    sites_mk = cmk.utils.paths.default_config_dir / "multisite.d/sites.mk"
    sites_mk_sav = cmk.utils.paths.default_config_dir / "multisite.d/sites.mk.sav"
    if sites_mk.exists():
        sites_mk.rename(sites_mk_sav)
        yield
        sites_mk_sav.rename(sites_mk)


@pytest.mark.usefixtures("load_config", "move_sites_mk_out_of_the_way")
def test_initialize_missing_file() -> None:
    assert not (sites_mk := cmk.utils.paths.default_config_dir / "multisite.d/sites.mk").exists()

    InitializeSiteConfiguration(
        name="initialize_site_configuration",
        title="Initialize site configuration",
        sort_index=30,
        expiry_version=ExpiryVersion.CMK_300,
    )(logging.getLogger())

    assert sites_mk.exists()
    sites_mk.unlink()


@pytest.mark.usefixtures("load_config", "move_sites_mk_out_of_the_way")
def test_initialize_empty_config() -> None:
    (
        sites_mk := cmk.utils.paths.default_config_dir / "multisite.d/sites.mk"
    ).write_text("""# Written by Checkmk store

sites.update({})""")

    InitializeSiteConfiguration(
        name="initialize_site_configuration",
        title="Initialize site configuration",
        sort_index=30,
        expiry_version=ExpiryVersion.CMK_300,
    )(logging.getLogger())

    site_mgmt = site_management_registry["site_management"]
    assert "NO_SITE" in site_mgmt.load_sites()
    sites_mk.unlink()


@pytest.mark.usefixtures("load_config", "move_sites_mk_out_of_the_way")
def test_initialize_missing_file_not_touch_existing_file() -> None:
    (sites_mk := cmk.utils.paths.default_config_dir / "multisite.d/sites.mk").write_text(
        "sites.update({'x': {}})"
    )

    InitializeSiteConfiguration(
        name="initialize_site_configuration",
        title="Initialize site configuration",
        sort_index=30,
        expiry_version=ExpiryVersion.CMK_300,
    )(logging.getLogger())

    assert sites_mk.read_text() == "sites.update({'x': {}})"
    sites_mk.unlink()
