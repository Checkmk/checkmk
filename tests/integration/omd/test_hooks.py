#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os

from tests.testlib.site import Site


def test_hooks(site: Site) -> None:
    hooks = [
        "ADMIN_MAIL",
        "APACHE_MODE",
        "APACHE_TCP_ADDR",
        "APACHE_TCP_PORT",
        "AUTOSTART",
        "CORE",
        "LIVESTATUS_TCP",
        "LIVESTATUS_TCP_ONLY_FROM",
        "LIVESTATUS_TCP_PORT",
        "LIVESTATUS_TCP_TLS",
        "AGENT_RECEIVER",
        "AGENT_RECEIVER_PORT",
        "MKEVENTD",
        "MKEVENTD_SNMPTRAP",
        "MKEVENTD_SYSLOG",
        "MKEVENTD_SYSLOG_TCP",
        "MULTISITE_AUTHORISATION",
        "MULTISITE_COOKIE_AUTH",
        "NAGIOS_THEME",
        "PNP4NAGIOS",
        "TMPFS",
    ]

    if site.version.edition() == "enterprise":
        hooks += [
            "LIVEPROXYD",
        ]

    installed_hooks = os.listdir(os.path.join(site.root, "lib/omd/hooks"))

    assert sorted(hooks) == sorted(installed_hooks)
