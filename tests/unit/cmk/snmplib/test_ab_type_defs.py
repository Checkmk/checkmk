#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.agent_based.v1 import OIDEnd, SNMPTree
from cmk.snmplib import SpecialColumn


def test_oid_end_repr() -> None:
    assert repr(OIDEnd()) == "OIDEnd()"


def test_oid_end_compat_with_backend() -> None:
    assert OIDEnd().column == SpecialColumn.END


@pytest.mark.parametrize(
    "base, oids",
    [
        ("1.2", ["1", "2"]),  # base no leading dot
        (".1.2", "12"),  # oids not a list
        (".1.2", ["1", 2]),  # int in list
        (".1.2", ["42.1", "42.2"]),  # 42 should be in base
    ],
)
def test_snmptree_valid(base: str, oids: Sequence) -> None:
    with pytest.raises((ValueError, TypeError)):
        SNMPTree(base=base, oids=oids).validate()
