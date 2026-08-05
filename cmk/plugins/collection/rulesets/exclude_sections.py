#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DictElement,
    Dictionary,
    MultipleChoice,
    MultipleChoiceElement,
)
from cmk.rulesets.v1.rule_specs import AgentConfig, Topic


def _skippable_linux_agent_sections() -> Mapping[str, Title]:
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


def _form_spec() -> Dictionary:
    return Dictionary(
        title=Title("Disabled sections (Linux agent)"),
        elements={
            "sections": DictElement(
                parameter_form=MultipleChoice(
                    title=Title("Disabled sections"),
                    help_text=Help(
                        "This option allows to skip specific sections of the Checkmk agent. "
                        "By default, all of the sections will be executed. "
                        "Selected sections will not be executed by the agent. "
                        "Skipping sections reduces CPU load on the monitored host and the amount "
                        "of transferred data. However, it may result in the absence of the "
                        "associated Checkmk service or services."
                    ),
                    elements=[
                        MultipleChoiceElement(name=name, title=title)
                        for name, title in _skippable_linux_agent_sections().items()
                    ],
                    show_toggle_all=True,
                ),
            ),
        },
    )


rule_spec_agent_exclude_sections = AgentConfig(
    title=Title("Disabled sections (Linux agent)"),
    name="agent_exclude_sections",
    topic=Topic.LINUX,
    parameter_form=_form_spec,
)
