#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Example output from agent:
# <<<lnx_sysctl:persist(1592223569)>>>
# abi.vsyscall32 = 1
# debug.exception-trace = 1
# debug.kprobes-optimization = 1
# dev.cdrom.autoclose = 1
# dev.cdrom.autoeject = 0
# dev.cdrom.check_media = 0
# dev.cdrom.debug = 0
# dev.cdrom.info = CD-ROM information, Id: cdrom.c 3.20 2003/12/17
# dev.cdrom.info =
# dev.cdrom.info = drive name:
# dev.cdrom.info = drive speed:
# dev.cdrom.info = drive # of slots:
# dev.cdrom.info = Can close tray:
# dev.cdrom.info = Can open tray:
# dev.cdrom.info = Can lock tray:
# dev.cdrom.info = Can change speed:
# dev.cdrom.info = Can select disk:

import re
from collections.abc import Mapping, Sequence

from cmk.agent_based.v2 import AgentSection, InventoryPlugin, InventoryResult, StringTable, TableRow

Section = Mapping[str, set[str]]


def parse_lnx_sysctl(string_table: StringTable) -> Section:
    kernel_config: dict[str, set[str]] = {}
    for line in string_table:
        kernel_config.setdefault(line[0], set()).add(" ".join(line[2:]))
    return kernel_config


agent_section_lnx_sysctl = AgentSection(
    name="lnx_sysctl",
    parse_function=parse_lnx_sysctl,
)


def inventory_lnx_sysctl(params: Mapping[str, Sequence[str]], section: Section) -> InventoryResult:
    include_patterns = params["include_patterns"]
    if not include_patterns:
        return

    exclude_patterns = params["exclude_patterns"]

    for name, values in section.items():
        if _include_parameter(
            name,
            include_patterns,
            exclude_patterns,
        ):
            for value in values:
                yield TableRow(
                    path=["software", "kernel_config"],
                    key_columns={
                        "name": name,
                        "value": value,
                    },
                    inventory_columns={},
                    status_columns={},
                )


def _include_parameter(
    par_name: str,
    include_patterns: Sequence[str],
    exclude_patterns: Sequence[str],
) -> bool:
    return (not any(re.match(pattern, par_name) for pattern in exclude_patterns)) and any(
        re.match(pattern, par_name) for pattern in include_patterns
    )


inventory_plugin_lnx_sysctl = InventoryPlugin(
    name="lnx_sysctl",
    inventory_function=inventory_lnx_sysctl,
    inventory_default_parameters={
        "include_patterns": [],
        "exclude_patterns": [],
    },
    inventory_ruleset_name="lnx_sysctl",
)
