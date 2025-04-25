#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.ccc.hostaddress import HostAddress, HostName, Hosts


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
    assert list(hosts_config.duplicates(lambda _hn: True)) == ["deux", "trois"]


@pytest.mark.parametrize(
    "hostaddress",
    [
        "ec2-11-111-222-333.cd-blahblah-1.compute.amazonaws.com",
        "subdomain.domain.com",
        "domain.com",
        "domain",
    ],
)
def test_valid_hostaddress(hostaddress: str) -> None:
    HostAddress(hostaddress)


@pytest.mark.parametrize(
    "hostaddress",
    [
        ".",
        "..",
        ".domain",
        ".domain.com",
        "-subdomain.domain.com",
        "email@domain.com",
        "@subdomain.domain.com",
    ],
)
def test_invalid_hostaddress(hostaddress: str) -> None:
    with pytest.raises(ValueError):
        HostAddress(hostaddress)
