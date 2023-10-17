#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.utils.hostaddress import HostName, Hosts


def test_duplicate_hosts() -> None:
    hostnames = (
        HostName("un"),
        HostName("deux"),
        HostName("deux"),
        HostName("trois"),
        HostName("trois"),
        HostName("trois"),
    )
    hosts_config = Hosts(hosts=hostnames, clusters=(), shadow_hosts=())
    assert list(hosts_config.duplicates(lambda *args, **kw: True)) == ["deux", "trois"]
