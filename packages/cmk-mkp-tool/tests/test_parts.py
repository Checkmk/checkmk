#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest

from cmk.mkp_tool import CONFIG_PARTS, PackagePart, PathConfig, ui_title
from cmk.mkp_tool._parts import make_path_config_template, permissions


def test_config_from_toml() -> None:
    assert PathConfig.from_toml(
        """
this = "this ignored"

[paths]
cmk_plugins_dir = "cmk_plugins_dir"
cmk_addons_plugins_dir = "cmk_addons_plugins_dir"
agent_based_plugins_dir = "local_agent_based_plugins_dir"
agents_dir = "local_agents_dir"
alert_handlers_dir = "local_alert_handlers_dir"
bin_dir = "local_bin_dir"
check_manpages_dir = "local_check_manpages_dir"
checks_dir = "local_checks_dir"
doc_dir = "local_doc_dir"
gui_plugins_dir = "local_gui_plugins_dir"
inventory_dir = "local_inventory_dir"
lib_dir = "local_lib_dir"
locale_dir = "local_locale_dir"
local_root = "local_root"
mib_dir = "local_mib_dir"
mkp_rule_pack_dir = "mkp_rule_pack_dir"
notifications_dir = "local_notifications_dir"
pnp_templates_dir = "local_pnp_templates_dir"
manifests_dir = "tmp_dir"
web_dir = "local_web_dir"
"""
    ).web_dir == Path("local_web_dir")


def test_toml_roundtrip() -> None:
    template = make_path_config_template()
    assert template == PathConfig.from_toml(template.to_toml())


def test_permissions() -> None:
    assert permissions(PackagePart.CMK_PLUGINS, Path("agent_based/foo.py")) == 0o600
    assert permissions(PackagePart.CMK_PLUGINS, Path("libexec/foo")) == 0o700
    assert permissions(PackagePart.AGENT_BASED, Path("some_check.py")) == 0o600
    assert permissions(PackagePart.BIN, Path("some_binary")) == 0o700
    assert permissions(PackagePart.LIB, Path("nagios/plugins/check_foobar")) == 0o700
    assert permissions(PackagePart.LIB, Path("something/else/check_foobar")) == 0o600


@pytest.mark.parametrize("part", list(PackagePart))
def test_permissions_are_defined_for_every_part(part: PackagePart) -> None:
    # guards the assert_never branch: a new part must be assigned permissions
    assert permissions(part, Path("some/file")) in (0o600, 0o700)


@pytest.mark.parametrize("part", list(PackagePart))
def test_ui_title_is_defined_for_every_part(part: PackagePart) -> None:
    # guards the assert_never branch: a new part must get a UI title
    assert ui_title(part, lambda s: s)


def test_ui_titles_are_distinct() -> None:
    titles = [ui_title(part, lambda s: s) for part in PackagePart]

    assert len(set(titles)) == len(titles)


def test_ui_title_is_translated() -> None:
    assert ui_title(PackagePart.AGENTS, lambda s: f"<{s}>") == "<Agents>"


@pytest.mark.parametrize("part", list(PackagePart))
def test_get_path_is_defined_for_every_part(part: PackagePart, path_config: PathConfig) -> None:
    # guards the assert_never branch: a new part must be mapped to a path
    _ = path_config.get_path(part)


def test_get_path_maps_every_part_to_a_distinct_path(path_config: PathConfig) -> None:
    paths = [path_config.get_path(part) for part in PackagePart]

    assert len(set(paths)) == len(paths)


def test_config_parts_are_package_parts() -> None:
    assert set(CONFIG_PARTS) <= set(PackagePart)


def test_package_part_idents_are_stable() -> None:
    # These strings end up in the 'files' mapping of every manifest on disk.
    # Changing one silently orphans the files of already-installed packages.
    assert {part.ident for part in PackagePart} == {
        "agent_based",
        "agents",
        "alert_handlers",
        "bin",
        "checkman",
        "checks",
        "cmk_addons_plugins",
        "cmk_plugins",
        "doc",
        "ec_rule_packs",
        "gui",
        "inventory",
        "lib",
        "locales",
        "mibs",
        "notifications",
        "pnp-templates",
        "web",
    }
