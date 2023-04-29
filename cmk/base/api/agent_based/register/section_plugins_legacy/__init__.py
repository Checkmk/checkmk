#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Helper to register a new-style section based on config.check_info
"""
from collections.abc import Callable
from typing import Any, List, Optional, Tuple

from cmk.base.api.agent_based.register.section_plugins import (
    create_agent_section_plugin,
    create_snmp_section_plugin,
)
from cmk.base.api.agent_based.section_classes import SNMPTree
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


def _extract_conmmon_part(oids: list) -> tuple[str, list]:
    common = ""

    def _get_head(oids):
        for oid in oids:
            if isinstance(oid, int):
                continue
            oid = str(oid).strip(".")
            if "." in oid:
                return oid.split(".", 1)[0]
        return None

    head = _get_head(oids)
    while head is not None and all(
        "." in str(o) and str(o).split(".", 1)[0] == head for o in oids if not isinstance(o, int)
    ):
        oids = [o if isinstance(o, int) else type(o)(str(o).split(".", 1)[1]) for o in oids]
        common = f"{common}.{head}"
        head = _get_head(oids)

    return common.strip("."), oids


def _create_snmp_trees_from_tuple(
    snmp_info_element: tuple,
) -> SNMPTree:
    """Create a SNMPTrees from (part of) a legacy definition

    Legacy definition *elements* can be 2-tuple or 3-tuple.
    We are quite generous here: we will make sure that
     * base will not end with '.'
     * subtrees are strings, starting but not ending with '.'
     * oids are not the empty string.
    """
    assert isinstance(snmp_info_element, tuple)
    raw_base, raw_oids = snmp_info_element
    base = raw_base.rstrip(".")

    # this fixes 7 weird cases:
    oids = ["%d" % oid if isinstance(oid, int) and oid > 0 else oid for oid in raw_oids]

    if "" in oids:  # this fixes 19 cases
        base, tail = str(base).rsplit(".", 1)
        oids = [o if isinstance(o, int) else type(o)((f"{tail}.{o}").strip(".")) for o in oids]
    else:  # this fixes 21 cases
        common, oids = _extract_conmmon_part(oids)
        if common:
            base = f"{base}.{common}"

    return SNMPTree(base=base, oids=oids)


def _create_snmp_trees(snmp_info: Any) -> tuple[list[SNMPTree], Callable]:
    """Create SNMPTrees from legacy definition

    Legacy definitions can be 2-tuple or a list of those.
    We convert these to a list of SNMPTree objects, and also return
    a function to transform the resulting value data structure back
    to the one the legacy prase or function expects.
    """
    if isinstance(snmp_info, tuple):
        tree_spec = _create_snmp_trees_from_tuple(snmp_info)
        return [tree_spec], lambda table: table[0]

    assert isinstance(snmp_info, list)

    return [_create_snmp_trees_from_tuple(element) for element in snmp_info], lambda x: x


def _create_snmp_parse_function(
    original_parse_function: Callable | None,
    recover_layout_function: Callable,
    handle_empty_info: bool,
) -> SNMPParseFunction:
    """Wrap parse function to comply to new API

    The created parse function will comply to the new signature requirement of
    accepting exactly one argument by the name "string_table".

    Additionally we undo the change of the data layout induced by the new
    spec for SNMPTrees.

    The old API would stop processing if the parse function returned something falsey,
    while the new API will consider *everything but* None a valid parse result,
    so we add `or None` to the returned expression.
    """

    # do not use functools.wraps, the point is the new argument name!
    def parse_function(string_table) -> Any:  # type: ignore[no-untyped-def]
        if not handle_empty_info and not any(string_table):
            return None

        relayouted_string_table = recover_layout_function(string_table)

        if original_parse_function is None:
            return relayouted_string_table or None

        return original_parse_function(relayouted_string_table) or None

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
    snmp_info: Any,
    *,
    validate_creation_kwargs: bool,
) -> SNMPSectionPlugin:
    if check_info_element.get("node_info"):
        # We refuse to tranform these. There's no way we get the data layout recovery right.
        # This would add 19 plugins to list of failures, but some are on the list anyway.
        raise NotImplementedError("cannot auto-migrate cluster aware plugins")

    trees, recover_layout_function = _create_snmp_trees(snmp_info)

    parse_function = _create_snmp_parse_function(
        check_info_element.get("parse_function"),
        recover_layout_function,
        handle_empty_info=bool(check_info_element.get("handle_empty_info")),
    )

    return create_snmp_section_plugin(
        name=get_section_name(check_plugin_name),
        parse_function=parse_function,
        fetch=trees,
        detect_spec=check_info_element["detect"],
        validate_creation_kwargs=validate_creation_kwargs,
    )
