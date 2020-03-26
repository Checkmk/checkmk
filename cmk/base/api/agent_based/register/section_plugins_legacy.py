#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Helper to register a new-style section based on config.check_info
"""
from typing import Any, Callable, Dict, Generator, List, Optional, Tuple

from cmk.base.check_api_utils import Service
from cmk.base.snmp_utils import SNMPTable
from cmk.base.discovered_labels import HostLabel, DiscoveredHostLabels
from cmk.base.api.agent_based.section_types import (
    AgentParseFunction,
    AgentSectionContent,
    AgentSectionPlugin,
    HostLabelFunction,
    SNMPParseFunction,
    SNMPSectionPlugin,
    SNMPTree,
)
from cmk.base.api.agent_based.utils import parse_string_table
from cmk.base.api.agent_based.register.section_plugins import (
    create_agent_section_plugin,
    create_snmp_section_plugin,
)

from cmk.base.api.agent_based.register.section_plugins_legacy_scan_function import (
    create_detect_spec,)

LayoutRecoverSuboids = List[Tuple[str]]


def get_section_name(check_plugin_name):
    # type: (str) -> str
    return check_plugin_name.split(".", 1)[0]


def _create_agent_parse_function(original_parse_function):
    # type: (Optional[Callable]) -> AgentParseFunction
    """Wrap parse function to comply to signature requirement"""

    if original_parse_function is None:
        return parse_string_table

    # do not use functools.wraps, the point is the new argument name!
    def parse_function(string_table):
        # type: (AgentSectionContent) -> Any
        return original_parse_function(string_table)  # type: ignore

    parse_function.__name__ = original_parse_function.__name__
    return parse_function


def _create_layout_recover_function(suboids_list):
    # type: (List[Optional[LayoutRecoverSuboids]]) -> Callable
    """Get a function that recovers the legacy data layout

    By adding the created elements to one long list,
    we change the data structure of created OID values.
    We have to define a function to undo this, and restore the old data layout.
    """
    elements_lengths = [len(i) if i is not None else 1 for i in suboids_list]
    cumulative_lengths = [sum(elements_lengths[:i]) for i in range(len(elements_lengths) + 1)]
    index_pairs = list(zip(cumulative_lengths, cumulative_lengths[1:]))

    def layout_recover_function(table):
        reformatted = []
        for suboids, (begin, end) in zip(suboids_list, index_pairs):
            if suboids is None:
                new_table = table[begin]
            else:
                new_table = []
                for suboid, subtable in zip(suboids, table[begin:end]):
                    new_table += [["%s.%s" % (suboid, row[0])] + row[1:] for row in subtable]
            reformatted.append(new_table)
        return reformatted

    return layout_recover_function


def _extract_conmmon_part(oids):
    # type: (list) -> Tuple[str, list]
    common = ''

    def _get_head(oids):
        for oid in oids:
            if isinstance(oid, int):
                continue
            oid = str(oid).strip('.')
            if '.' in oid:
                return oid.split('.', 1)[0]
        return None

    head = _get_head(oids)
    while (head is not None and all('.' in str(o) and str(o).split('.')[0] == head
                                    for o in oids
                                    if not isinstance(o, int))):
        oids = [o if isinstance(o, int) else type(o)(str(o).split('.', 1)[1]) for o in oids]
        common = "%s.%s" % (common, head)
        head = _get_head(oids)

    return common.strip('.'), oids


def _create_snmp_trees_from_tuple(snmp_info_element):
    # type: (tuple) -> Tuple[List[SNMPTree], Optional[LayoutRecoverSuboids]]
    """Create a SNMPTrees from (part of) a legacy definition

    Legacy definition *elements* can be 2-tuple or 3-tuple.
    We are quite generous here: we will make sure that
     * base will not end with '.'
     * subtrees are strings, starting but not ending with '.'
     * oids are not the empty string.
    """
    assert isinstance(snmp_info_element, tuple)
    assert len(snmp_info_element) in (2, 3)
    base = snmp_info_element[0].rstrip('.')

    # "Triple"-case: recursively return a list
    if len(snmp_info_element) == 3:
        tmp_base, suboids, oids = snmp_info_element
        base_list = [("%s.%s" % (tmp_base, str(i).strip('.'))) for i in suboids]
        return sum((_create_snmp_trees_from_tuple((base, oids))[0] for base in base_list),
                   []), suboids

    # this fixes 7 weird cases:
    oids = ["%d" % oid if isinstance(oid, int) and oid > 0 else oid for oid in snmp_info_element[1]]

    if '' in oids:  # this fixes 19 cases
        base, tail = str(base).rsplit('.', 1)
        oids = [
            o if isinstance(o, int) else type(o)(("%s.%s" % (tail, o)).strip('.')) for o in oids
        ]
    else:  # this fixes 21 cases
        common, oids = _extract_conmmon_part(oids)
        if common:
            base = "%s.%s" % (base, common)

    return [SNMPTree(base=base, oids=oids)], None


def _create_snmp_trees(snmp_info):
    # type: (Any) -> Tuple[List[SNMPTree], Callable]
    """Create SNMPTrees from legacy definition

    Legacy definitions can be 2-tuple, 3-tuple, or a list
    of any of those.
    We convert these to a list of SNMPTree objects, and also return
    a function to transform the resulting value data structure back
    to the one the legacy prase or function expects.
    """
    if isinstance(snmp_info, tuple):
        tree_spec, reco_oids = _create_snmp_trees_from_tuple(snmp_info)
        if reco_oids is None:
            return tree_spec, lambda table: table[0]
        recovery = _create_layout_recover_function([reco_oids])
        return tree_spec, lambda table: recovery(table)[0]

    assert isinstance(snmp_info, list)

    trees_and_suboids = [_create_snmp_trees_from_tuple(element) for element in snmp_info]
    trees = sum((tree for tree, _suboids in trees_and_suboids), [])  # type: List[SNMPTree]
    suboids_list = [suboids for _tree, suboids in trees_and_suboids]

    layout_recover_function = _create_layout_recover_function(suboids_list)

    return trees, layout_recover_function


def _create_snmp_parse_function(original_parse_function, recover_layout_function):
    # type: (Optional[Callable], Callable) -> SNMPParseFunction
    """Wrap parse function to comply to new API

    The created parse function will comply to the new signature requirement of
    accepting exactly one argument by the name "string_table".

    Additionally we undo the change of the data layout induced by the new
    spec for SNMPTrees.
    """
    if original_parse_function is None:
        original_parse_function = parse_string_table

    # do not use functools.wraps, the point is the new argument name!
    def parse_function(string_table):
        # type: (List[SNMPTable]) -> Any
        return original_parse_function(  # type: ignore
            recover_layout_function(string_table),)

    parse_function.__name__ = original_parse_function.__name__
    return parse_function


def _create_host_label_function(discover_function, extra_sections):
    # type: (Optional[Callable], List[str]) -> Optional[HostLabelFunction]
    """Wrap discover_function to filter for HostLabels"""
    if discover_function is None:
        return None

    extra_sections_count = len(extra_sections)

    def host_label_function(section):
        # type: (Any) -> Generator[HostLabel, None, None]
        if not extra_sections_count:
            discover_arg = section
        else:
            discover_arg = [section] + [[]] * extra_sections_count

        discovery_iter = discover_function(discover_arg)  # type: ignore
        if discovery_iter is None:
            return

        for service_or_host_label in discovery_iter:
            if isinstance(service_or_host_label, Service):
                for host_label in service_or_host_label.host_labels.to_list():
                    yield host_label
            elif isinstance(service_or_host_label, HostLabel):
                yield service_or_host_label
            elif isinstance(service_or_host_label, DiscoveredHostLabels):
                for host_label in service_or_host_label.to_list():
                    yield host_label

    return host_label_function


def create_agent_section_plugin_from_legacy(check_plugin_name, check_info_dict):
    # type: (str, Dict[str, Any]) -> AgentSectionPlugin

    parse_function = _create_agent_parse_function(check_info_dict.get('parse_function'),)

    host_label_function = _create_host_label_function(
        check_info_dict.get('inventory_function'),
        check_info_dict.get('extra_sections', []),
    )

    return create_agent_section_plugin(
        name=get_section_name(check_plugin_name),
        parse_function=parse_function,
        host_label_function=host_label_function,
        forbidden_names=[],
    )


def create_snmp_section_plugin_from_legacy(check_plugin_name, check_info_dict, snmp_scan_function,
                                           snmp_info):
    # type: (str, Dict[str, Any], Callable, Any) -> SNMPSectionPlugin
    trees, recover_layout_function = _create_snmp_trees(snmp_info)

    parse_function = _create_snmp_parse_function(
        check_info_dict.get('parse_function'),
        recover_layout_function,
    )

    host_label_function = _create_host_label_function(
        check_info_dict.get('inventory_function'),
        check_info_dict.get('extra_sections', []),
    )

    detect_spec = create_detect_spec(
        check_plugin_name,
        snmp_scan_function,
    )

    return create_snmp_section_plugin(
        name=get_section_name(check_plugin_name),
        parse_function=parse_function,
        host_label_function=host_label_function,
        forbidden_names=[],
        trees=trees,
        detect_spec=detect_spec,
    )
