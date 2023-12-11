#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Helper to register a new-style section based on config.check_info
"""
from collections.abc import Callable
from typing import Any, cast

from cmk.base.api.agent_based.plugin_classes import (
    AgentParseFunction,
    AgentSectionPlugin,
    SNMPSectionPlugin,
)
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
)
from cmk.agent_based.v2.type_defs import StringTable

from .utils_legacy import LegacyCheckDefinition


def get_section_name(check_plugin_name: str) -> str:
    return check_plugin_name.split(".", 1)[0]


def _create_agent_parse_function(original_parse_function: Callable) -> AgentParseFunction:
    """Wrap parse function to comply to signature requirement"""

    original_parse_function_not_none = original_parse_function

    # do not use functools.wraps, the point is the new argument name!
    def parse_function(string_table: StringTable) -> Any:
        return original_parse_function_not_none(string_table)

    parse_function.__name__ = original_parse_function.__name__
    return parse_function


def _create_snmp_parse_function(
    original_parse_function: Callable,
) -> Callable[[Any], object]:  # sorry, but this is what we know.
    """Wrap parse function to comply to new API

    The created parse function will comply to the new signature requirement of
    accepting exactly one argument by the name "string_table".

    The old API would stop processing if the parse function returned something falsey,
    while the new API will consider *everything but* None a valid parse result,
    so we add `or None` to the returned expression.
    """

    # do not use functools.wraps, the point is the new argument name!
    def parse_function(string_table: Any) -> object:
        if not any(string_table):
            return None

        return original_parse_function(string_table) or None

    if original_parse_function is not None:
        parse_function.__name__ = original_parse_function.__name__

    return parse_function


def create_agent_section_plugin_from_legacy(
    check_plugin_name: str,
    check_info_element: LegacyCheckDefinition,
) -> AgentSectionPlugin:
    if check_info_element.get("node_info"):
        # We refuse to tranform these. The requirement of adding the node info
        # makes rewriting of the base code too difficult.
        # Affected Plugins must be migrated manually after CMK-4240 is done.
        raise NotImplementedError("cannot auto-migrate cluster aware plugins")

    parse_function = _create_agent_parse_function(check_info_element["parse_function"])

    return create_agent_section_plugin(
        AgentSection(
            name=get_section_name(check_plugin_name),
            parse_function=parse_function,
        ),
        location=None,
        validate=False,
    )


def create_snmp_section_plugin_from_legacy(
    check_plugin_name: str,
    check_info_element: LegacyCheckDefinition,
) -> SNMPSectionPlugin:
    if check_info_element.get("node_info"):
        # We refuse to tranform these. There's no way we get the data layout recovery right.
        # This would add 19 plugins to list of failures, but some are on the list anyway.
        raise NotImplementedError("cannot auto-migrate cluster aware plugins")

    fetch = check_info_element["fetch"]
    detect = cast(SNMPDetectSpecification, check_info_element["detect"])

    parse_function = _create_snmp_parse_function(check_info_element["parse_function"])

    return create_snmp_section_plugin(
        SimpleSNMPSection(  # ty#pe: ignore[call-overload]
            name=get_section_name(check_plugin_name),
            parse_function=parse_function,
            fetch=fetch,
            detect=detect,
        )
        if isinstance(fetch, SNMPTree)
        else SNMPSection(  # ty#pe: ignore[call-overload]
            name=get_section_name(check_plugin_name),
            parse_function=parse_function,
            fetch=fetch,
            detect=detect,
        ),
        location=None,
        validate=False,
    )
