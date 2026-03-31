#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.agent_bakery import RulespecGroupMonitoringAgentsLinuxUnixAgent
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import Dictionary, ListChoice


def _skippable_linux_agent_sections() -> dict[str, str]:
    return {
        # The key must match the section exclude parameter in the checkmk_agent i.e. MK_SKIP_<key>
        "areca": _("Raid controllers from Areca"),
        "bonding_if": _("Bonding interfaces"),
        "cfggen": _("Raid status of LSI controllers"),
        "checkmk_agent_plugins": _("Inventory of all deployed agent plug-ins and their versions"),
        "chrony": _("Chrony time synchronization"),
        "cpu": _("CPU"),
        "df": _("File systems usage"),
        "diskstat": _("Diskstat"),
        "dm_raid": _("Raid status of Linux Raid"),
        "drbd": _("DRBD"),
        "fileinfo": _("Fileinfo"),
        "haproxy": _("Haproxy"),
        "heartbeat": _("Heartbeat clusters"),
        "corosync_latency": _("Corosync latency"),
        "http_accelerator": _("HTTP accelerator statistics"),
        "ipmisensors": _("Ipmisensors"),
        "ipmitool": _("Ipmitool"),
        "job": _("Monitored jobs"),
        "kernel": _("Kernel"),
        "labels": _("Host label"),
        "libelle": _("Libelle Business Shadow"),
        "lnx_if": _("Linux interfaces"),
        "mailqueue": _("Mailqueue"),
        "md": _("Raid status of Linux software"),
        "megaraid": _("Raid status of LSI MegaRAID controller"),
        "mem": _("Memory"),
        "mounts": _("Mount options"),
        "multipathing": _("Multipathing"),
        "nfs_mounts": ("NFS mounts"),
        "nvidia": _("Nvidia"),
        "omd_cores": _("OMD monitoring cores"),
        "omd": _("Status of OMD sites and Checkmk notification spooler"),
        "openvpn": _("OpenVPN clients"),
        "proxmox": _("Proxmox cluster"),
        "ps": _("Running processes"),
        "systemd": _("Systemd services"),
        "tcp": _("TCP"),
        "thermal": _("Thermal information"),
        "three_ware_raid": _("Raid status of 3WARE disk controller"),
        "timesynchronisation": _("NTP or timesyncd time synchronization"),
        "uptime": _("UPTIME"),
        "vbox_guest": _("VirtualBox Guests"),
        "veritas": _("Veritas cluster server"),
        "vswitch_bonding": _("Vswitch bonding"),
        "zfs": _("ZFS file system usage"),
        "zpool": _("Zpool status"),
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
                        "By default all of the sections will be executed. "
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
