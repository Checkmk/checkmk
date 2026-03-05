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
    IPNetworkAdapter,
    TEMP_DEVICE_PREFIXES,
)


def host_labels_if(adapters: Iterable[IPNetworkAdapter]) -> HostLabelGenerator:
    """Return host labels describing the host's network 'single-/multihomed' property based on
    the IP addresses of its interfaces.
    Filters away temporary interfaces and local IP addresses (based on interface name and IP's
    ULA prefix, link-local/unspecified/local-host properties) and counts non-overlapping
    networks of the remaining addresses.
    """
    # Original author: thl-cmk[at]outlook[dot]com
    if adapters is None:  # type: ignore[comparison-overlap]
        return  # type: ignore[unreachable]
    for version in (4, 6):
        valid_networks = {
            interface_ip.network
            for adapter in adapters
            if not any(adapter.name.startswith(prefix) for prefix in TEMP_DEVICE_PREFIXES)
            for interface_ip in (adapter.inet4 if version == 4 else adapter.inet6)
            if not any(
                (
                    interface_ip.is_broadcast,
                    interface_ip.is_loopback,
                    interface_ip.is_link_local,
                    interface_ip.is_unspecified,
                    interface_ip.is_ula,
                    interface_ip.is_temporary,
                )
            )
        }
        # left as homework: turn these two semantically identical blocks into
        # one (I gave up after a while trying to come up with a generic)
        if (
            independent_network_count := len(
                {
                    net
                    for net in valid_networks
                    if isinstance(net, IPv4Network)
                    if not any(
                        net != other and net.subnet_of(other)
                        for other in valid_networks
                        if isinstance(other, IPv4Network)
                    )
                }
            )
            if version == 4
            else len(
                {
                    net
                    for net in valid_networks
                    if isinstance(net, IPv6Network)
                    if not any(
                        net != other and net.subnet_of(other)
                        for other in valid_networks
                        if isinstance(other, IPv6Network)
                    )
                }
            )
        ):
            yield HostLabel(
                name=f"cmk/l3v{version}_topology",
                value="singlehomed" if independent_network_count == 1 else "multihomed",
            )
