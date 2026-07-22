#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.diagnostics.engine import load_diagnostics_plugins


def test_available_diagnostics_plugins() -> None:
    discovered = load_diagnostics_plugins(raise_errors=True)
    assert {plugin.name for plugin in discovered.plugins.values()} == {
        "apache_config",
        "appliance_info",
        "checkmk_overview",
        "config_files_high",
        "config_files_low",
        "config_files_medium",
        "disk_usage",
        "environment_variables",
        "file_sizes",
        "general_info",
        "hw_info",
        "log_files_high",
        "log_files_low",
        "log_files_medium",
        "network_state",
        "omd_config",
        "os_packages",
        "parameters",
        "processes_and_logins",
        "python_packages",
        "selinux",
        "vendor_info",
    }
