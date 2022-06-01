#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import socket
from pathlib import Path

from tests.testlib.base import Scenario

from cmk.utils.type_defs import HostName

from cmk.core_helpers.cache import FileCacheMode, MaxAge

from cmk.base.sources.tcp import TCPSource


def test_attribute_defaults(monkeypatch):
    ipaddress = "1.2.3.4"
    hostname = HostName("testhost")

    ts = Scenario()
    ts.add_host(hostname)
    ts.apply(monkeypatch)

    source = TCPSource(hostname, ipaddress)
    monkeypatch.setattr(source, "file_cache_base_path", Path("/my/path/"))
    assert source.fetcher_configuration == {
        "file_cache": {
            "hostname": "testhost",
            "max_age": MaxAge.none(),
            "base_path": "/my/path",
            "simulation": False,
            "use_outdated": False,
            "use_only_cache": False,
            "file_cache_mode": FileCacheMode.READ_WRITE.value,
        },
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
