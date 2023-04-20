#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os

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

    if site.version.is_enterprise_edition() or site.version.is_cloud_edition():
        scripts += [
            "cmc",
            "dcd",
            "liveproxyd",
            "mknotifyd",
        ]

    installed_scripts = os.listdir(os.path.join(site.root, "etc/init.d"))

    assert sorted(scripts) == sorted(installed_scripts)
