# encoding: utf-8
# pylint: disable=protected-access

import pytest  # type: ignore[import]

from cmk.base.check_api import (
    OID_END,
    OID_STRING,
)

from cmk.base.api.agent_based.section_types import OIDEnd, SNMPTree
from cmk.base.api.agent_based.register.section_plugins_legacy import (
    _create_layout_recover_function,
    _create_snmp_trees_from_tuple,
)

DATA_2X2 = [["1", "2"], ["3", "4"]]


@pytest.mark.parametrize("suboids_list, input_data, expected_output", [
    (
        [None],
        [DATA_2X2],
        [DATA_2X2],
    ),
    (
        [None, ["2", "3"]],
        [DATA_2X2, DATA_2X2, DATA_2X2],
        [DATA_2X2, [
            ["2.1", "2"],
            ["2.3", "4"],
            ["3.1", "2"],
            ["3.3", "4"],
        ]],
    ),
])
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
            (".1.2.3", range(4, 6)),
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
            [SNMPTree(base=".1.2.3", oids=[OID_STRING])],
            None,
        ),
    ])
def test_create_snmp_trees_from_tuple(element, expected_tree, expected_suboids):
    assert _create_snmp_trees_from_tuple(element) == (expected_tree, expected_suboids)
