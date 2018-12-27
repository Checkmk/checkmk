#!/usr/bin/env python
# encoding: utf-8

import os
import stat


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
