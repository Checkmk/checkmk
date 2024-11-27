#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Helper to register a new-style section based on config.check_info"""

from collections.abc import Callable, Iterable, Mapping, Sequence
from typing import cast

from cmk.base.api.agent_based.plugin_classes import (
    AgentSectionPlugin,
    LegacyPluginLocation,
    SNMPSectionPlugin,
)
from cmk.base.api.agent_based.register.section_plugins import (
    create_agent_section_plugin,
    create_snmp_section_plugin,
)

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
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
    location: LegacyPluginLocation,
) -> SNMPSectionPlugin | AgentSectionPlugin:
    match fetch:
        case None:
            return create_agent_section_plugin(
                AgentSection(
                    name=name,
                    parse_function=parse_function,
                ),
                location=location,
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
                location=location,
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
                location=location,
                validate=False,
            )


def convert_legacy_sections(
    legacy_checks: Iterable[LegacyCheckDefinition],
    tracked_files: Mapping[str, str],
    *,
    raise_errors: bool,
) -> tuple[list[str], Sequence[SNMPSectionPlugin | AgentSectionPlugin]]:
    errors = []
    sections = []

    for check_info_element in legacy_checks:
        if (parse_function := check_info_element.parse_function) is None:
            continue
        file = tracked_files[check_info_element.name]
        try:
            sections.append(
                create_section_plugin_from_legacy(
                    name=check_info_element.name,
                    parse_function=parse_function,
                    fetch=check_info_element.fetch,
                    detect=check_info_element.detect,
                    location=LegacyPluginLocation(file),
                )
            )
        except (NotImplementedError, KeyError, AssertionError, ValueError):
            # NOTE: missing section plug-ins may lead to missing data for a check plug-in
            #       *or* to more obscure errors, when a check/inventory plug-in will be
            #       passed un-parsed data unexpectedly.
            if raise_errors:
                raise
            errors.append(f"Failed to auto-migrate legacy plug-in to section: {file}\n")

    return errors, sections
