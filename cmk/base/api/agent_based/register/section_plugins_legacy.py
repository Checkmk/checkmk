#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Helper to register a new-style section based on config.check_info
"""
from typing import Any, Callable, List, Tuple

from cmk.base.api.agent_based.section_types import (
    SNMPTree,)


def _create_layout_recover_function(elements_lengths):
    """Get a function that recovers the legacy data layout

    By adding the created elements to one long list,
    we change the data structure of created OID values.
    We have to define a function to undo this, and restore the old data layout.
    """
    cumulative_lengths = [sum(elements_lengths[:i]) for i in range(len(elements_lengths) + 1)]
    index_pairs = list(zip(cumulative_lengths, cumulative_lengths[1:]))

    def layout_recover_function(table):
        return [sum(table[begin:end], []) for begin, end in index_pairs]

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
    # type: (tuple) -> List[SNMPTree]
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
        base_list = [("%s.%s" % (base, str(i).strip('.'))) for i in snmp_info_element[1]]
        return sum(
            (_create_snmp_trees_from_tuple((base, snmp_info_element[2])) for base in base_list), [])

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

    return [SNMPTree(base=base, oids=oids)]


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
        tree_spec = _create_snmp_trees_from_tuple(snmp_info)
        if len(tree_spec) == 1:
            return tree_spec, lambda table: table[0]
        return tree_spec, lambda table: sum(table, [])

    assert isinstance(snmp_info, list)

    created_elements = [_create_snmp_trees_from_tuple(element) for element in snmp_info]
    trees = sum(created_elements, [])  # type: List[SNMPTree]

    element_lengths = [len(e) for e in created_elements]
    layout_recover_function = _create_layout_recover_function(element_lengths)

    return trees, layout_recover_function
