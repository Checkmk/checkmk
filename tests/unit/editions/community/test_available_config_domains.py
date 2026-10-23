#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.watolib.config_domain_name import config_domain_registry


@pytest.mark.usefixtures("load_gui_plugins")
def test_registered_config_domains() -> None:
    expected_config_domains = [
        "apache",
        "ca-certificates",
        "check_mk",
        "diskspace",
        "ec",
        "maps",
        "multisite",
        "omd",
        "rrdcached",
        "site-certificate",
        "product_usage_analytics",
        "release_flags",
    ]

    registered = sorted(config_domain_registry.keys())
    assert registered == sorted(expected_config_domains)
