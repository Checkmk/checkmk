#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.ccc import site
from cmk.utils.paths import omd_root


def test_get_omd_config(patch_omd_site: None) -> None:
    assert site.get_omd_config(omd_root) == {
        "CONFIG_ADMIN_MAIL": "",
        "CONFIG_AGENT_RECEIVER": "on",
        "CONFIG_AGENT_RECEIVER_PORT": "8000",
        "CONFIG_APACHE_MODE": "own",
        "CONFIG_APACHE_TCP_ADDR": "127.0.0.1",
        "CONFIG_APACHE_TCP_PORT": "5002",
        "CONFIG_AUTOMATION_HELPER": "on",
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
        "CONFIG_NSCA": "off",
        "CONFIG_NSCA_TCP_PORT": "5667",
        "CONFIG_PNP4NAGIOS": "on",
        "CONFIG_RABBITMQ_PORT": "5672",
        "CONFIG_RABBITMQ_ONLY_FROM": "0.0.0.0 ::",
        "CONFIG_RABBITMQ_DIST_PORT": "25672",
        "CONFIG_TMPFS": "on",
        "CONFIG_TRACE_JAEGER_ADMIN_PORT": "14269",
        "CONFIG_TRACE_JAEGER_UI_PORT": "13333",
        "CONFIG_TRACE_RECEIVE": "off",
        "CONFIG_TRACE_RECEIVE_ADDRESS": "[::1]",
        "CONFIG_TRACE_RECEIVE_PORT": "4321",
        "CONFIG_TRACE_SEND": "off",
        "CONFIG_TRACE_SEND_TARGET": "local_site",
    }


def test_get_apache_port(patch_omd_site: None) -> None:
    assert site.get_apache_port(omd_root) == 5002
