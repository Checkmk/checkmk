#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]

from cmk.base.check_api import OID_END
from cmk.base.snmp_utils import (
    OIDSpec,
    OIDCached,
    OIDBytes,
)
from cmk.base.api.agent_based.section_types import (
    OIDEnd,
    SNMPTree,
)


def test_oid_end():
    oide = OIDEnd()
    assert oide == OIDEnd()
    assert repr(oide) == "OIDEnd()"
    assert oide == OID_END


@pytest.mark.parametrize(
    "base, oids",
    [
        ('1.2', ['1', '2']),  # base no leading dot
        ('.1.2', '12'),  # oids not a list
        # TODO: this should fail once CompatibleOIDEnd is not needed anymore
        # ('.1.2', ['1', 2]),  # int in list
        ('.1.2', ['42.1', '42.2']),  # 42 should be in base
    ])
def test_snmptree_valid(base, oids):
    with pytest.raises((ValueError, TypeError)):
        SNMPTree(base=base, oids=oids)


@pytest.mark.parametrize("base, oids", [
    ('.1.2', ['1', '2']),
    ('.1.2', ['1', OIDCached('2')]),
    ('.1.2', ['1', OIDBytes('2')]),
    ('.1.2', ['1', OIDEnd()]),
])
def test_snmptree(base, oids):
    tree = SNMPTree(base=base, oids=oids)

    assert tree.base == OIDSpec(base)
    assert isinstance(tree.oids, list)
    for oid in tree.oids:
        assert isinstance(oid, (OIDSpec, OIDEnd))
