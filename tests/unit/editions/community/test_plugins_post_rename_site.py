#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.post_rename_site import main


def test_load_plugins() -> None:
    assert {p.name for p in main.load_plugins()} == {
        "sites",
        "messaging",
        "hosts_and_folders",
        "update_core_config",
        "warn_remote_site",
        "warn_about_network_ports",
        "warn_about_configs_to_review",
        "nagvis_maps",
    }
