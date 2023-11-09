#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.mkp_tool import PathConfig


def test_config_from_toml() -> None:
    assert (
        PathConfig.from_toml(
            """
this = "this ignored"

[paths]
agent_based_plugins_dir = "local_agent_based_plugins_dir"
agents_dir = "local_agents_dir"
alert_handlers_dir = "local_alert_handlers_dir"
bin_dir = "local_bin_dir"
check_manpages_dir = "local_check_manpages_dir"
checks_dir = "local_checks_dir"
doc_dir = "local_doc_dir"
gui_plugins_dir = "local_gui_plugins_dir"
installed_packages_dir = "installed_packages_dir"
inventory_dir = "local_inventory_dir"
lib_dir = "local_lib_dir"
locale_dir = "local_locale_dir"
local_root = "local_root"
mib_dir = "local_mib_dir"
mkp_rule_pack_dir = "mkp_rule_pack_dir"
notifications_dir = "local_notifications_dir"
packages_enabled_dir = "local_enabled_packages_dir"
packages_local_dir = "local_optional_packages_dir"
packages_shipped_dir = "optional_packages_dir"
pnp_templates_dir = "local_pnp_templates_dir"
tmp_dir = "tmp_dir"
web_dir = "local_web_dir"
"""
        ).web_dir
        == "local_web_dir"
    )
