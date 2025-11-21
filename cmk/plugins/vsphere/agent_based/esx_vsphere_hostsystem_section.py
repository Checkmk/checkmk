#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

from collections.abc import Mapping, Sequence

from cmk.agent_based.v2 import AgentSection, HostLabel, HostLabelGenerator, StringTable

type HostSystemSection = Mapping[str, Sequence[str]]


def parse_esx_vsphere_hostsystem(string_table: StringTable) -> HostSystemSection:
    """
    >>> from pprint import pprint
    >>> pprint(parse_esx_vsphere_hostsystem([
    ...     ['hardware.cpuInfo.numCpuCores', '12'],
    ...     ['hardware.cpuInfo.numCpuPackages', '2'],
    ...     ['hardware.cpuInfo.numCpuThreads', '24'],
    ...     ['hardware.cpuInfo.hz', '2933436846'],  # --> In Hz per CPU Core
    ...     ['summary.quickStats.overallCpuUsage', '7539'],  # --> In MHz
    ... ]))
    {'hardware.cpuInfo.numCpuCores': ['12'],
     'hardware.cpuInfo.numCpuPackages': ['2'],
     'hardware.cpuInfo.numCpuThreads': ['24'],
     'hardware.cpuInfo.hz': ['2933436846'],
     'summary.quickStats.overallCpuUsage': ['7539']}

    """
    section = dict[str, list[str]]()
    # From what is being done in checks/esx_vsphere_hostsystem.cpu_util_cluster
    # it seems that the order of the keys must not be changed, or data will be lost
    # and/or scrambled up.
    for key, *value in string_table:
        section[key] = value
    return section


def host_label_function(section: HostSystemSection) -> HostLabelGenerator:
    """
    For some reason all docs for the same host label have to be identical.
    Here we only set this to server because this plug-in is executed on
    ESXi piggy back data.

    Labels:

        cmk/vsphere_object:
            This label is set to "server" if the host is an ESXi hostsystem
            and to "vm" if the host is a virtual machine.

    """
    # ^- Note: They have to be identical, because the user can not (easily) see
    # which plug-in set any given label. There has to be a unique semantical meaning
    # for each label value.
    # If you feel the need to set different docs, you should not be using the same labels!
    yield HostLabel("cmk/vsphere_object", "server")


agent_section_esx_vsphere_hostsystem = AgentSection(
    name="esx_vsphere_hostsystem",
    parse_function=parse_esx_vsphere_hostsystem,
    host_label_function=host_label_function,
)
