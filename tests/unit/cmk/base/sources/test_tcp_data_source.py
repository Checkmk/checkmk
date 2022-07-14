#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import socket
from pathlib import Path

from tests.testlib.base import Scenario

from cmk.utils.type_defs import HostName

from cmk.base.config import HostConfig
from cmk.base.sources.tcp import TCPSource


def test_attribute_defaults(monkeypatch) -> None:  # type:ignore[no-untyped-def]
    ipaddress = "1.2.3.4"
    hostname = HostName("testhost")

    ts = Scenario()
    ts.add_host(hostname)
    ts.apply(monkeypatch)

    host_config = HostConfig.make_host_config(hostname)
    source = TCPSource(
        host_config,
        ipaddress,
        simulation_mode=True,
        agent_simulator=True,
        translation={},
        encoding_fallback="ascii",
    )
    monkeypatch.setattr(source, "file_cache_base_path", Path("/my/path/"))
    assert source.fetcher_configuration == {
        "family": socket.AF_INET,
        "address": (ipaddress, 6556),
        "host_name": str(hostname),
        "timeout": 5.0,
        "encryption_settings": {
            "use_realtime": "enforce",
            "use_regular": "disable",
        },
    }
    assert source.description == "TCP: %s:%s" % (ipaddress, 6556)
    assert source.id == "agent"
