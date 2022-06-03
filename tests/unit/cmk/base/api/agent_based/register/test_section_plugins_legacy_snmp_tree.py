#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.snmplib.type_defs import SpecialColumn

from cmk.base.api.agent_based.register.section_plugins_legacy import (
    _create_layout_recover_function,
    _create_snmp_trees_from_tuple,
)
from cmk.base.api.agent_based.section_classes import OIDEnd, SNMPTree
from cmk.base.check_api import OID_END, OID_STRING

DATA_2X2 = [["1", "2"], ["3", "4"]]


@pytest.mark.parametrize(
    "suboids_list, input_data, expected_output",
    [
        (
            [None],
            [DATA_2X2],
            [DATA_2X2],
        ),
        (
            [None, ["2", "3"]],
            [DATA_2X2, DATA_2X2, DATA_2X2],
            [
                DATA_2X2,
                [
                    ["2.1", "2"],
                    ["2.3", "4"],
                    ["3.1", "2"],
                    ["3.3", "4"],
                ],
            ],
        ),
    ],
)
def test_create_layout_recover_function(suboids_list, input_data, expected_output):
    layout_recover_func = _create_layout_recover_function(suboids_list)
    assert layout_recover_func(input_data) == expected_output


@pytest.mark.parametrize(
    "element, expected_tree, expected_suboids",
    [
        (
            (".1.2.3", ["4", "5"]),
            [SNMPTree(base=".1.2.3", oids=["4", "5"])],
            None,
        ),
        (
            (".1.2.3", ["4", ""]),
            [SNMPTree(base=".1.2", oids=["3.4", "3"])],
            None,
        ),
        (
            (".1.2", ["3.4", "3.5"]),
            [SNMPTree(base=".1.2.3", oids=["4", "5"])],
            None,
        ),
        (
            (".1.2.3", list(range(4, 6))),
            [SNMPTree(base=".1.2.3", oids=["4", "5"])],
            None,
        ),
        (
            (".1.2.3", [OID_END]),
            [SNMPTree(base=".1.2.3", oids=[OIDEnd()])],
            None,
        ),
        (
            (".1.2.3", ["4", 5], ["1", "2", "3"]),
            [
                SNMPTree(base=".1.2.3.4", oids=["1", "2", "3"]),
                SNMPTree(base=".1.2.3.5", oids=["1", "2", "3"]),
            ],
            ["4", 5],
        ),
        # not used in mainline code, but test it anyway:
        (
            (".1.2.3", [OID_STRING]),
            # discouraged by typing, but will still work:
            [SNMPTree(base=".1.2.3", oids=[SpecialColumn.STRING])],
            None,
        ),
    ],
)
def test_create_snmp_trees_from_tuple(element, expected_tree, expected_suboids):
    assert _create_snmp_trees_from_tuple(element) == (expected_tree, expected_suboids)
