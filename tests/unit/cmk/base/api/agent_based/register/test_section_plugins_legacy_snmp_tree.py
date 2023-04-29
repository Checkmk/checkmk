#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Sequence

import pytest

from cmk.base.api.agent_based.register.section_plugins_legacy import _create_snmp_trees_from_tuple
from cmk.base.api.agent_based.section_classes import OIDEnd, SNMPTree
from cmk.base.check_api import OID_END


@pytest.mark.parametrize(
    "element, expected_tree",
    [
        (
            (".1.2.3", ["4", "5"]),
            SNMPTree(base=".1.2.3", oids=["4", "5"]),
        ),
        (
            (".1.2.3", ["4", ""]),
            SNMPTree(base=".1.2", oids=["3.4", "3"]),
        ),
        (
            (".1.2", ["3.4", "3.5"]),
            SNMPTree(base=".1.2.3", oids=["4", "5"]),
        ),
        (
            (".1.2.3", list(range(4, 6))),
            SNMPTree(base=".1.2.3", oids=["4", "5"]),
        ),
        (
            (".1.2.3", [OID_END]),
            SNMPTree(base=".1.2.3", oids=[OIDEnd()]),
        ),
    ],
)
def test_create_snmp_trees_from_tuple(
    element: tuple[str, Sequence[str | int], Sequence[str]],
    expected_tree: Sequence[SNMPTree],
) -> None:
    assert _create_snmp_trees_from_tuple(element) == expected_tree
