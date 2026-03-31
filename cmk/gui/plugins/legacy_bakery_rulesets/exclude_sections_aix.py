#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.agent_bakery import RulespecGroupMonitoringAgentsLinuxUnixAgent
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import Dictionary, ListChoice
from cmk.utils.rulesets.definition import RuleGroup


def _skippable_aix_agent_sections() -> dict[str, str]:
    return {
        # The key must match the section exclude parameter in the checkmk_agent i.e. MK_SKIP_<key>
        "checkmk_agent_plugins": _("Inventory of all deployed agent plug-ins and their versions"),
        "df": _("File systems usage"),
        "nfs_mounts": _("NFS mounts"),
        "ps": _("Running processes"),
        "aix_lparstat": _("LPAR statistics for AIX"),
        "aix_vmstat": _("VM statistics for AIX"),
        "aix_diskio": _("Disk I/O statistics for AIX"),
        "aix_mem": _("Memory usage for AIX"),
        "aix_mpstat": _("MP statistics for AIX"),
        "aix_paging": _("Paging statistics for AIX"),
        "cpu": _("CPU"),
        "aix_if": _("AIX network interfaces"),
        "timesynchronisation": _("NTP time synchronization"),
        "multipathing": _("Multipathing"),
        "aix_lvm": _("Logical volume manager for AIX"),
        "tcp": _("TCP"),
        "libelle": _("Libelle Business Shadow"),
        "mailqueue": _("Mailqueue"),
        "uptime": _("Uptime"),
        "fileinfo": _("File information"),
        "aix_hacmp": _("HACMP cluster for AIX"),
        "job": _("Monitored jobs"),
    }


def _valuespec_agent_config_agent_sections_aix() -> Dictionary:
    return Dictionary(
        title=_("Disabled sections (AIX agent)"),
        elements=[
            (
                "sections_aix",
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
                    choices=sorted(_skippable_aix_agent_sections().items(), key=lambda x: x[1]),
                ),
            ),
        ],
        optional_keys=[],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringAgentsLinuxUnixAgent,
        name=RuleGroup.AgentConfig("exclude_sections_aix"),
        valuespec=_valuespec_agent_config_agent_sections_aix,
    )
)
