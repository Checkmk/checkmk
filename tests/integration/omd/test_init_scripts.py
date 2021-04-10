#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os


def test_init_scripts(site):
    scripts = [
        "apache",
        "core",
        "crontab",
        "mkeventd",
        "nagios",
        "npcd",
        "nsca",
        "pnp_gearman_worker",
        "rrdcached",
        "xinetd",
        "stunnel",
        "redis",
    ]

    if site.version.edition() == "enterprise":
        scripts += [
            "cmc",
            "dcd",
            "liveproxyd",
            "mknotifyd",
        ]

    installed_scripts = os.listdir(os.path.join(site.root, "etc/init.d"))

    assert sorted(scripts) == sorted(installed_scripts)
