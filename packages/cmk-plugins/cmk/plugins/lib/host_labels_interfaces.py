#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Mapping
from ipaddress import (
    IPv4Interface,
    IPv6Interface,
    IPv6Network,
)

from cmk.agent_based.v2 import HostLabel, HostLabelGenerator

TEMP_DEVICES = (
    "docker",
    "br-",
    "veth",
    "podman",
    "cni",
    "flannel",
    "calico",
    "weave",
    "vti",
    "virbr",
    "vnet",
    "vEthernet",
    "vmnet",
)
IPV6_ULA_NETWORK = IPv6Network("fc00::/7")  # fc.. and fd.. => ULA


def host_labels_if(
    interfaces: Mapping[str, Iterable[IPv4Interface | IPv6Interface]],
) -> HostLabelGenerator:
    """Return host labels describing the host's network 'single-/multihomed' property based on
    the IP addresses of its interfaces.
    Filters away temporary interfaces and local IP addresses (based on interface name and IP's
    ULA prefix, link-local/unspecified/local-host properties) and checks if the remaining IPs
    belong to one or more subnets.
    """
    # Original author: thl-cmk[at]outlook[dot]com

    for version in (4, 6):
        if valid_networks := set(
            # note: contains subnet mask, e.g. 1.2.3.4/24 != 1.2.3.4/32
            #       for now we define this to be different in terms of single-/multihomed
            #       for sake of simplicity, but we might want to change this in the future
            str(interface_ip.network)
            for name, interface_ips in interfaces.items()
            if not any(name.startswith(prefix) for prefix in TEMP_DEVICES)
            for interface_ip in interface_ips
            if interface_ip.version == version
            and not any(
                (
                    interface_ip.is_loopback,
                    interface_ip.is_link_local,
                    interface_ip.is_unspecified,
                    interface_ip in IPV6_ULA_NETWORK,
                )
            )
        ):
            yield HostLabel(
                name=f"cmk/l3v{version}_topology",
                value="singlehomed" if len(valid_networks) == 1 else "multihomed",
            )
