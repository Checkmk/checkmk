#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Example output:
# <<<esx_vsphere_clusters:sep(9)>>>
# datacenter-41  hostsystems VM-Cluster-Clients-Neu  abl-h1-esx84.abl.ads.bayerwald.de
# datacenter-41  vms VM-Cluster-Clients-Neu  abl-h1-w7v232   abl-h1-w7v233   abl-h1-w7v236

from typing import Dict

from cmk.base.plugins.agent_based.agent_based_api.v1 import register, TableRow
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import InventoryResult, StringTable

Section = Dict[str, Dict[str, str]]


def parse_esx_vsphere_clusters(string_table: StringTable) -> Section:
    """
    >>> for k, v in parse_esx_vsphere_clusters([
    ...     ['datacenter-1', 'hostsystems', 'cluster-1', 'host-2', 'host-3'],
    ...     ['datacenter-1', 'vms', 'cluster-1'],
    ...     ['datacenter-2', 'hostsystems', 'cluster-2', 'host-7', 'host-8', 'host-9'],
    ...     ['datacenter-2', 'vms', 'cluster-2'],
    ... ]).items():
    ...   print(k, v)
    cluster-1 {'datacenter': 'datacenter-1', 'hostsystems': 'host-2, host-3', 'vms': ''}
    cluster-2 {'datacenter': 'datacenter-2', 'hostsystems': 'host-7, host-8, host-9', 'vms': ''}
    """
    # We now understand that every cluster is assigned to exactly one data center,
    # aparrently this was not clear when designing the sections output
    section: Section = {}
    for datacenter_name, key, cluster_name, *values in string_table:
        section.setdefault(cluster_name, {"datacenter": datacenter_name})[key] = ", ".join(values)
    return section


def inventory_esx_vsphere_clusters(section: Section) -> InventoryResult:
    for cluster_name, cluster_data in section.items():
        yield TableRow(
            path=["software", "applications", "vmwareesx"],
            key_columns={
                "cluster": cluster_name,
                "datacenter": cluster_data["datacenter"],
                "hostsystems": cluster_data["hostsystems"],
                "vms": cluster_data["vms"],
            },
        )


register.agent_section(
    name="esx_vsphere_clusters",
    parse_function=parse_esx_vsphere_clusters,
)

register.inventory_plugin(
    name="inventory_esx_vsphere_clusters",
    sections=["esx_vsphere_clusters"],
    inventory_function=inventory_esx_vsphere_clusters,
)
