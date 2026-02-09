#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable
from ipaddress import (
    IPv4Interface,
    IPv6Interface,
)

from cmk.agent_based.v2 import HostLabel, HostLabelGenerator


def host_labels_if(interfaces: Iterable[IPv4Interface | IPv6Interface]) -> HostLabelGenerator:
    """
    Host label function
    Labels:
        cmk/l3v4_topology:
            "singlehomed" is set for all devices with one IPv4 address
            "multihomed" is set for all devices with more than one IPv4 address.
        cmk/l3v6_topology:
            "singlehomed" is set for all devices with one IPv6 address
            "multihomed" is set for all devices with more than one IPv6 address.

        Link-local ("FE80::/64), unspecified ("::") and local-host ("127.0.0.0/8", "::1") IPs don't count.
    """
    # Original author: thl-cmk[at]outlook[dot]com
    valid_v4_ips = 0
    valid_v6_ips = 0
    for interface in interfaces:
        if interface.version == 4 and not interface.is_loopback:
            valid_v4_ips += 1
            if valid_v4_ips == 1:
                yield HostLabel(name="cmk/l3v4_topology", value="singlehomed")
            if valid_v4_ips == 2:
                yield HostLabel(name="cmk/l3v4_topology", value="multihomed")

        elif (
            interface.version == 6
            and not interface.is_loopback
            and not interface.is_link_local
            and not interface.is_unspecified
        ):
            valid_v6_ips += 1
            if valid_v6_ips == 1:
                yield HostLabel(name="cmk/l3v6_topology", value="singlehomed")
            if valid_v6_ips == 2:
                yield HostLabel(name="cmk/l3v6_topology", value="multihomed")
