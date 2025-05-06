#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from cmk.mkp_tool import PackagePart, PathConfig
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
