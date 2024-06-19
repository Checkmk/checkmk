#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Helper to register a new-style section based on config.check_info
"""
from collections.abc import Callable, Sequence
from typing import cast

from cmk.base.api.agent_based.plugin_classes import AgentSectionPlugin, SNMPSectionPlugin
from cmk.base.api.agent_based.register.section_plugins import (
    create_agent_section_plugin,
    create_snmp_section_plugin,
)

from cmk.agent_based.v2 import (
    AgentSection,
    SimpleSNMPSection,
    SNMPDetectSpecification,
    SNMPSection,
    SNMPTree,
    StringTable,
)


def create_section_plugin_from_legacy(
    *,
    name: str,
    parse_function: Callable[[list], object],
    detect: SNMPDetectSpecification | None,
    fetch: SNMPTree | Sequence[SNMPTree] | None,
) -> SNMPSectionPlugin | AgentSectionPlugin:
    match fetch:
        case None:
            return create_agent_section_plugin(
                AgentSection(
                    name=name,
                    parse_function=parse_function,
                ),
                location=None,
                validate=False,
            )

        case SNMPTree():
            assert detect
            return create_snmp_section_plugin(
                SimpleSNMPSection[StringTable, object](
                    name=name,
                    parse_function=parse_function,
                    fetch=fetch,
                    detect=detect,
                ),
                location=None,
                validate=False,
            )

        case fetch_list:
            assert detect
            return create_snmp_section_plugin(
                SNMPSection(
                    name=name,
                    parse_function=cast(Callable[[Sequence], object], parse_function),
                    fetch=fetch_list,
                    detect=detect,
                ),
                location=None,
                validate=False,
            )
