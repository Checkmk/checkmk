#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Helper to register a new-style section based on config.check_info
"""
from collections.abc import Callable
from typing import Any

from cmk.base.api.agent_based.register.section_plugins import (
    create_agent_section_plugin,
    create_snmp_section_plugin,
)
from cmk.base.api.agent_based.type_defs import (
    AgentParseFunction,
    AgentSectionPlugin,
    SNMPParseFunction,
    SNMPSectionPlugin,
    StringTable,
)

from ..utils_legacy import CheckInfoElement


def get_section_name(check_plugin_name: str) -> str:
    return check_plugin_name.split(".", 1)[0]


def _create_agent_parse_function(
    original_parse_function: Callable | None,
) -> AgentParseFunction:
    """Wrap parse function to comply to signature requirement"""

    if original_parse_function is None:
        return lambda string_table: string_table
    original_parse_function_not_none = original_parse_function

    # do not use functools.wraps, the point is the new argument name!
    def parse_function(string_table: StringTable) -> Any:
        return original_parse_function_not_none(string_table)

    parse_function.__name__ = original_parse_function.__name__
    return parse_function


def _create_snmp_parse_function(
    original_parse_function: Callable | None,
    handle_empty_info: bool,
) -> SNMPParseFunction:
    """Wrap parse function to comply to new API

    The created parse function will comply to the new signature requirement of
    accepting exactly one argument by the name "string_table".

    The old API would stop processing if the parse function returned something falsey,
    while the new API will consider *everything but* None a valid parse result,
    so we add `or None` to the returned expression.
    """

    # do not use functools.wraps, the point is the new argument name!
    def parse_function(string_table) -> Any:  # type: ignore[no-untyped-def]
        if not handle_empty_info and not any(string_table):
            return None

        if original_parse_function is None:
            return string_table or None

        return original_parse_function(string_table) or None

    if original_parse_function is not None:
        parse_function.__name__ = original_parse_function.__name__

    return parse_function


def create_agent_section_plugin_from_legacy(
    check_plugin_name: str,
    check_info_element: CheckInfoElement,
    *,
    validate_creation_kwargs: bool,
) -> AgentSectionPlugin:
    if check_info_element.get("node_info"):
        # We refuse to tranform these. The requirement of adding the node info
        # makes rewriting of the base code too difficult.
        # Affected Plugins must be migrated manually after CMK-4240 is done.
        raise NotImplementedError("cannot auto-migrate cluster aware plugins")

    parse_function = _create_agent_parse_function(
        check_info_element.get("parse_function"),
    )

    return create_agent_section_plugin(
        name=get_section_name(check_plugin_name),
        parse_function=parse_function,
        validate_creation_kwargs=validate_creation_kwargs,
    )


def create_snmp_section_plugin_from_legacy(
    check_plugin_name: str,
    check_info_element: CheckInfoElement,
    *,
    validate_creation_kwargs: bool,
) -> SNMPSectionPlugin:
    if check_info_element.get("node_info"):
        # We refuse to tranform these. There's no way we get the data layout recovery right.
        # This would add 19 plugins to list of failures, but some are on the list anyway.
        raise NotImplementedError("cannot auto-migrate cluster aware plugins")

    parse_function = _create_snmp_parse_function(
        check_info_element.get("parse_function"),
        handle_empty_info=bool(check_info_element.get("handle_empty_info")),
    )

    return create_snmp_section_plugin(
        name=get_section_name(check_plugin_name),
        parse_function=parse_function,
        fetch=check_info_element["fetch"],
        detect_spec=check_info_element["detect"],
        validate_creation_kwargs=validate_creation_kwargs,
    )
