#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.gui.agent_bakery import RulespecGroupMonitoringAgentsLinuxUnixAgent
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import Dictionary, ListChoice

Title = _


def _skippable_linux_agent_sections() -> Mapping[str, str]:
    return {
        # The key must match the section exclude parameter in the checkmk_agent i.e. MK_SKIP_<key>
        "areca": Title("Raid controllers from Areca"),
        "bonding_if": Title("Bonding interfaces"),
        "cfggen": Title("Raid status of LSI controllers"),
        "checkmk_agent_plugins": Title(
            "Inventory of all deployed agent plug-ins and their versions"
        ),
        "chrony": Title("Chrony time synchronization"),
        "corosync_latency": Title("Corosync latency"),
        "cpu": Title("CPU"),
        "df": Title("File systems usage"),
        "diskstat": Title("Diskstat"),
        "dm_raid": Title("Raid status of Linux Raid"),
        "drbd": Title("DRBD"),
        "fileinfo": Title("Fileinfo"),
        "haproxy": Title("Haproxy"),
        "heartbeat": Title("Heartbeat clusters"),
        "http_accelerator": Title("HTTP accelerator statistics"),
        "ipmisensors": Title("Ipmisensors"),
        "ipmitool": Title("Ipmitool"),
        "job": Title("Monitored jobs"),
        "kernel": Title("Kernel"),
        "labels": Title("Host label"),
        "libelle": Title("Libelle Business Shadow"),
        "lnx_if": Title("Linux interfaces"),
        "mailqueue": Title("Mailqueue"),
        "md": Title("Raid status of Linux software"),
        "megaraid": Title("Raid status of LSI MegaRAID controller"),
        "mem": Title("Memory"),
        "mounts": Title("Mount options"),
        "multipathing": Title("Multipathing"),
        "nfs_mounts": Title("NFS mounts"),
        "nvidia": Title("Nvidia"),
        "omd_cores": Title("OMD monitoring cores"),
        "omd": Title("Status of OMD sites and Checkmk notification spooler"),
        "openvpn": Title("OpenVPN clients"),
        "proxmox": Title("Proxmox cluster"),
        "ps": Title("Running processes"),
        "systemd": Title("Systemd services"),
        "tcp": Title("TCP"),
        "thermal": Title("Thermal information"),
        "three_ware_raid": Title("Raid status of 3WARE disk controller"),
        "timesynchronisation": Title("NTP or timesyncd time synchronization"),
        "uptime": Title("UPTIME"),
        "vbox_guest": Title("VirtualBox Guests"),
        "veritas": Title("Veritas cluster server"),
        "vswitch_bonding": Title("Vswitch bonding"),
        "zfs": Title("ZFS file system usage"),
        "zpool": Title("Zpool status"),
    }


def _valuespec_agent_config_agent_sections() -> Dictionary:
    return Dictionary(
        title=_("Disabled sections (Linux agent)"),
        elements=[
            (
                "sections",
                ListChoice(
                    title=_("Disabled sections"),
                    help=_(
                        "This option allows to skip specific sections of the Checkmk agent. "
                        "By default, all of the sections will be executed. "
                        "Selected sections will not be executed by the agent. "
                        "Skipping sections reduces CPU load on the monitored host and the amount "
                        "of transferred data. However, it may result in the absence of the "
                        "associated Checkmk service or services."
                    ),
                    choices=sorted(_skippable_linux_agent_sections().items(), key=lambda x: x[1]),
                ),
            ),
        ],
        optional_keys=[],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringAgentsLinuxUnixAgent,
        name="agent_exclude_sections",
        valuespec=_valuespec_agent_config_agent_sections,
    )
)
