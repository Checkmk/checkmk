#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import socket
from pathlib import Path

from cmk.utils.type_defs import HostName, SourceType

import cmk.core_helpers.cache as file_cache
from cmk.core_helpers import FetcherType

from cmk.base.sources.tcp import TCPSource


def test_attribute_defaults() -> None:  # type:ignore[no-untyped-def]
    ipaddress = "1.2.3.4"
    hostname = HostName("testhost")
    source = TCPSource(
        hostname,
        ipaddress,
        source_type=SourceType.HOST,
        fetcher_type=FetcherType.TCP,
        id_="agent",
        cache_dir=Path(os.devnull),
        simulation_mode=True,
        address_family=socket.AF_INET,
        agent_port=6556,
        tcp_connect_timeout=5.0,
        agent_encryption={"use_realtime": "enforce", "use_regular": "disable"},
        file_cache_max_age=file_cache.MaxAge.none(),
    )
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
    assert source.id == "agent"
