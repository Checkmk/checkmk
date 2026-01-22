#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from tests.testlib.site import Site


def test_init_scripts(site: Site) -> None:
    scripts = {
        "agent-receiver",
        "apache",
        "automation-helper",
        "ui-job-scheduler",
        "core",
        "crontab",
        "mkeventd",
        "nagios",
        "npcd",
        "piggyback-hub",
        "pnp_gearman_worker",
        "rabbitmq",
        "redis",
        "rrdcached",
        "stunnel",
        "xinetd",
    }

    if not site.edition.is_community_edition():
        scripts |= {
            "cmc",
            "dcd",
            "liveproxyd",
            "mknotifyd",
        }
    if site.edition.is_ultimate_edition() or site.edition.is_ultimatemt_edition():
        scripts |= {"otel-collector", "metric-backend"}
    if not site.edition.is_cloud_edition():
        scripts |= {"jaeger"}

    installed_scripts = set(site.listdir("etc/init.d"))

    assert scripts == installed_scripts
