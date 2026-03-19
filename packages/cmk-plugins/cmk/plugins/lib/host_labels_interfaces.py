#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable
from ipaddress import (
    IPv4Network,
    IPv6Network,
)

from cmk.agent_based.v2 import HostLabel, HostLabelGenerator
from cmk.plugins.lib.interfaces import (
    AugmentedIPv4Interface,
    AugmentedIPv6Interface,
    IPNetworkAdapter,
    TEMP_DEVICE_PREFIXES,
)


def host_labels_if(adapters: None | Iterable[IPNetworkAdapter]) -> HostLabelGenerator:
    """Return host labels describing the host's network 'single-/multihomed' property based on
    the IP addresses of its interfaces.
    Filters away temporary interfaces and local IP addresses (based on interface name and IP's
    ULA prefix, link-local/unspecified/local-host properties) and counts non-overlapping
    networks of the remaining addresses.
    """
    # Original author: thl-cmk[at]outlook[dot]com

    if adapters is None:
        return

    valid_networks_v4: set[IPv4Network] = set()
    valid_networks_v6: set[IPv6Network] = set()

    for network in (
        interface_ip.network
        for adapter in adapters
        if not any(adapter.name.startswith(prefix) for prefix in TEMP_DEVICE_PREFIXES)
        for interface_ip in (*adapter.inet4, *adapter.inet6)
        if isinstance(interface_ip, (AugmentedIPv4Interface, AugmentedIPv6Interface))
        if not any(
            (
                interface_ip.is_broadcast,
                interface_ip.is_loopback,
                interface_ip.is_link_local and interface_ip.version == 6,
                interface_ip.is_unspecified,
                interface_ip.is_ula,
                interface_ip.is_temporary,
            )
        )
    ):
        if isinstance(network, IPv4Network):
            valid_networks_v4.add(network)
        elif isinstance(network, IPv6Network):
            valid_networks_v6.add(network)

    for version, valid_networks in ((4, valid_networks_v4), (6, valid_networks_v6)):
        if independent_networks := {
            net
            for net in valid_networks
            # we need to ignore arg-type here, because mypy doesn't interfere `valid_networks` to be either
            # all IPv4Network or IPv6Network, making `other` `IPv4Network | IPv6Network`
            if not any(net != other and net.subnet_of(other) for other in valid_networks)  # type: ignore[arg-type]
        }:
            yield HostLabel(
                name=f"cmk/l3v{version}_topology",
                value="singlehomed" if len(independent_networks) == 1 else "multihomed",
            )
