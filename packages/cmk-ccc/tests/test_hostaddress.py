#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.ccc.hostaddress import HostAddress, HostName, Hosts


def test_all_configured_hosts() -> None:
    hostnames = (
        HostName("un"),
        HostName("deux"),
        HostName("deux"),
        HostName("trois"),
        HostName("trois"),
        HostName("trois"),
    )
    hosts_config = Hosts(hosts=hostnames, clusters={}, shadow_hosts=(), host_paths={})
    assert set(hosts_config.all_configured_hosts) == {"un", "deux", "trois"}


def test_duplicate_hosts() -> None:
    hostnames = (
        HostName("un"),
        HostName("deux"),
        HostName("deux"),
        HostName("trois"),
        HostName("trois"),
        HostName("trois"),
    )
    hosts_config = Hosts(hosts=hostnames, clusters={}, shadow_hosts=(), host_paths={})
    assert list(hosts_config.duplicates(lambda _hn: True)) == ["deux", "trois"]


@pytest.mark.parametrize(
    "hostaddress",
    [
        pytest.param("ec2-11-111-222-333.cd-blahblah-1.compute.amazonaws.com", id="AWS host name"),
        pytest.param("subdomain.domain.com", id="subdomain"),
        pytest.param("domain.com", id="domain"),
        pytest.param("domain", id="single label"),
    ],
)
def test_valid_hostaddress(hostaddress: str) -> None:
    HostAddress(hostaddress)


@pytest.mark.parametrize(
    "hostaddress",
    [
        pytest.param(".", id="dot"),
        pytest.param("..", id="two dots"),
        pytest.param(".domain", id="leading dot"),
        pytest.param(".domain.com", id="leading dot with subdomain"),
        pytest.param("-subdomain.domain.com", id="leading hyphen"),
        pytest.param("email@domain.com", id="at sign"),
        pytest.param("@subdomain.domain.com", id="leading at sign"),
        pytest.param("domain.com\n", id="trailing newline"),
        pytest.param("\ndomain.com", id="leading newline"),
        pytest.param("domain\ncom", id="inner newline"),
    ],
)
def test_invalid_hostaddress(hostaddress: str) -> None:
    with pytest.raises(ValueError):
        HostAddress(hostaddress)
