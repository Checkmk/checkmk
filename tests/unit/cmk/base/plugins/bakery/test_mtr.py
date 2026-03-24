#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from cmk.bakery.v1 import OS, Plugin, PluginConfig
from cmk.base.plugins.bakery.mtr import get_mtr_files


def test_mtr_files_basic() -> None:
    conf = {
        "deployment": ("cached", 600.0),
        "mtr_config": [
            {"hostname": "example.com"},
        ],
    }
    result = sorted(get_mtr_files(conf), key=repr)
    expected = sorted(
        [
            Plugin(base_os=OS.LINUX, source=Path("mtr.py"), interval=600),
            PluginConfig(
                base_os=OS.LINUX,
                lines=[
                    "# [DEFAULTS]",
                    "# type=icmp    # icmp, tcp or udp",
                    "# count=10     # number of pings per mtr report",
                    "# force_ipv4=0 # force ipv4, exclusive with force_ipv6",
                    "# force_ipv6=0 # force ipv6, exclusive with force_ipv4",
                    "# size=64      # packet size",
                    "# time=0       # minimum time between runs, 0 / default means run if mtr doesn't run anymore",
                    "# port=80      # UDP/TCP port to connect to",
                    "# dns=0        # Use DNS resolution to lookup addresses",
                    "# address=     # Bind to source address",
                    "# interval=    # time MTR waits between sending pings",
                    "# timeout=     # ping Timeout, see mtr man page",
                    "# max_hops=30  # maximum number of hops",
                    "",
                    "",
                    "[example.com]",
                    "",
                ],
                target=Path("mtr.cfg"),
                include_header=True,
            ),
        ],
        key=repr,
    )
    assert result == expected


def test_mtr_files_with_options() -> None:
    conf = {
        "deployment": ("cached", 300.0),
        "mtr_config": [
            {
                "hostname": "10.0.0.1",
                "type": "tcp",
                "count": 5,
                "port": 443,
                "dns": 1,
                "enforce_what": "ipv4",
            },
        ],
    }
    result = list(get_mtr_files(conf))
    plugin_config = [r for r in result if isinstance(r, PluginConfig)][0]
    # Check that lines for the host section contain the expected settings
    lines = plugin_config.lines
    assert "[10.0.0.1]" in lines
    assert "type = tcp" in lines
    assert "count = 5" in lines
    assert "port = 443" in lines
    assert "dns = 1" in lines
    assert "force_ipv4 = True" in lines
