#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from tests.testlib.site import Site


def test_init_scripts(site: Site) -> None:
    scripts = [
        "apache",
        "core",
        "crontab",
        "mkeventd",
        "nagios",
        "npcd",
        "pnp_gearman_worker",
        "rrdcached",
        "xinetd",
        "stunnel",
        "redis",
        "agent-receiver",
    ]

    if not site.version.is_raw_edition():
        scripts += [
            "cmc",
            "dcd",
            "liveproxyd",
            "mknotifyd",
        ]

    installed_scripts = site.listdir("etc/init.d")

    assert sorted(scripts) == sorted(installed_scripts)
