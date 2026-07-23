#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from tests.testlib.site import Site


def test_rabbitmq_version(site: Site) -> None:
    cmd = [
        "rabbitmqctl",
        "version",
    ]
    assert "3.13.6" in site.check_output(cmd)


def test_rabbitmq_shovel_plugin(site: Site) -> None:
    cmd = [
        "rabbitmq-plugins",
        "list",
    ]
    assert "rabbitmq_shovel" in site.check_output(cmd)
