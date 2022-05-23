#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.utils import site


def test_get_omd_config() -> None:
    assert site.get_omd_config() == {
        "CONFIG_ADMIN_MAIL": "",
        "CONFIG_AGENT_RECEIVER": "on",
        "CONFIG_AGENT_RECEIVER_PORT": "8000",
        "CONFIG_APACHE_MODE": "own",
        "CONFIG_APACHE_TCP_ADDR": "127.0.0.1",
        "CONFIG_APACHE_TCP_PORT": "5002",
        "CONFIG_AUTOSTART": "off",
        "CONFIG_CORE": "cmc",
        "CONFIG_LIVEPROXYD": "on",
        "CONFIG_LIVESTATUS_TCP": "off",
        "CONFIG_LIVESTATUS_TCP_ONLY_FROM": "0.0.0.0 ::/0",
        "CONFIG_LIVESTATUS_TCP_PORT": "6557",
        "CONFIG_LIVESTATUS_TCP_TLS": "on",
        "CONFIG_MKEVENTD": "on",
        "CONFIG_MKEVENTD_SNMPTRAP": "off",
        "CONFIG_MKEVENTD_SYSLOG": "on",
        "CONFIG_MKEVENTD_SYSLOG_TCP": "off",
        "CONFIG_MULTISITE_AUTHORISATION": "on",
        "CONFIG_MULTISITE_COOKIE_AUTH": "on",
        "CONFIG_NAGIOS_THEME": "classicui",
        "CONFIG_NSCA": "off",
        "CONFIG_NSCA_TCP_PORT": "5667",
        "CONFIG_PNP4NAGIOS": "on",
        "CONFIG_TMPFS": "on",
    }


def test_get_apache_port() -> None:
    assert site.get_apache_port() == 5002
