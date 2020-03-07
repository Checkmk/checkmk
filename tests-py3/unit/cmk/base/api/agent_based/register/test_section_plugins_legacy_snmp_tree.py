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
    _create_snmp_trees,
)

FLAT_DATA_LAYOUT = [
    [None],
    [None],
    [None],
    [None],
    [None],
    [None],
]


@pytest.mark.parametrize("element_lengths, expected_output", [
    ([1, 1, 1, 1, 1, 1], FLAT_DATA_LAYOUT),
    ([1, 2, 3], [[None], [None, None], [None, None, None]]),
    ([6], [[None, None, None, None, None, None]]),
])
def test_create_layout_recover_function(element_lengths, expected_output):
    layout_recover_func = _create_layout_recover_function(element_lengths)
    assert layout_recover_func(FLAT_DATA_LAYOUT) == expected_output


@pytest.mark.parametrize(
    "element, expected_output",
    [
        ((".1.2.3", ["4", "5"]), [SNMPTree(base=".1.2.3", oids=["4", "5"])]),
        ((".1.2.3", ["4", ""]), [SNMPTree(base=".1.2", oids=["3.4", "3"])]),
        ((".1.2", ["3.4", "3.5"]), [SNMPTree(base=".1.2.3", oids=["4", "5"])]),
        ((".1.2.3", range(4, 6)), [SNMPTree(base=".1.2.3", oids=["4", "5"])]),
        ((".1.2.3", [OID_END]), [SNMPTree(base=".1.2.3", oids=[OIDEnd()])]),
        ((".1.2.3", ["4", 5], ["1", "2", "3"]), [
            SNMPTree(base=".1.2.3.4", oids=["1", "2", "3"]),
            SNMPTree(base=".1.2.3.5", oids=["1", "2", "3"]),
        ]),
        # not used in mainline code, but test it anyway:
        ((".1.2.3", [OID_STRING]), [SNMPTree(base=".1.2.3", oids=[OID_STRING])]),
    ])
def test_create_snmp_trees_from_tuple(element, expected_output):
    assert _create_snmp_trees_from_tuple(element) == expected_output
