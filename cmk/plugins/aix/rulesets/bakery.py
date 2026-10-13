#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DictElement,
    Dictionary,
    MultipleChoice,
    MultipleChoiceElement,
)
from cmk.rulesets.v1.rule_specs import AgentConfig, Topic


def _skippable_aix_agent_sections() -> dict[str, Title]:
    return {
        # The key must match the section exclude parameter in the checkmk_agent i.e. MK_SKIP_<key>
        "checkmk_agent_plugins": Title(
            "Inventory of all deployed agent plug-ins and their versions"
        ),
        "df": Title("File systems usage"),
        "nfs_mounts": Title("NFS mounts"),
        "ps": Title("Running processes"),
        "aix_lparstat": Title("LPAR statistics for AIX"),
        "aix_vmstat": Title("VM statistics for AIX"),
        "aix_diskio": Title("Disk I/O statistics for AIX"),
        "aix_mem": Title("Memory usage for AIX"),
        "aix_mpstat": Title("MP statistics for AIX"),
        "aix_paging": Title("Paging statistics for AIX"),
        "cpu": Title("CPU"),
        "aix_if": Title("AIX network interfaces"),
        "timesynchronisation": Title("NTP time synchronization"),
        "multipathing": Title("Multipathing"),
        "aix_lvm": Title("Logical volume manager for AIX"),
        "tcp": Title("TCP"),
        "libelle": Title("Libelle Business Shadow"),
        "mailqueue": Title("Mailqueue"),
        "uptime": Title("Uptime"),
        "fileinfo": Title("File information"),
        "aix_hacmp": Title("HACMP cluster for AIX"),
        "job": Title("Monitored jobs"),
    }


def _form_spec() -> Dictionary:
    return Dictionary(
        title=Title("Disabled sections (AIX agent)"),
        elements={
            "sections_aix": DictElement(
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
                        for name, title in _skippable_aix_agent_sections().items()
                    ],
                    show_toggle_all=True,
                ),
            ),
        },
    )


rule_spec_exclude_sections_aix = AgentConfig(
    title=Title("Disabled sections (AIX agent)"),
    name="exclude_sections_aix",
    topic=Topic.LINUX,
    parameter_form=_form_spec,
)
