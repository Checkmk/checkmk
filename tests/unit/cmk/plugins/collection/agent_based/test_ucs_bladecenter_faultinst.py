#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-untyped-call"


from cmk.agent_based.v2 import Result, Service, State
from cmk.plugins.collection.agent_based.ucs_bladecenter_faultinst import (
    check_ucs_bladecenter_faultinst,
    discover_ucs_bladecenter_faultinst,
)
from cmk.plugins.ucs_bladecenter import lib as ucs_bladecenter

# Some real output to work with would be nice here instead of reverse engineering what it looks like
TABLE = [
    [
        "faultInst",
        "Dn sys/chassis-2/bl...ault-F1256 Descr Local disk 2 missing on server 2/3",
        "Severity major",
        "Descr test",
    ],
    [
        "faultInst",
        "Dn sys/chassis-2/bl...ault-F1256 Descr Local disk 1 missing on server 2/3",
        "Severity major",
        "Descr test2",
    ],
    [
        "faultInst",
        "Dn sys/chassis-1/bl...ault-F1256 Descr Local disk 2 missing on server 1/3",
        "Severity minor",
        "Descr baz",
    ],
]


def test_inventory_ucs_bladecenter_faultinst() -> None:
    """Test discovery function for ucs_bladecenter_faultinst check."""
    parsed = ucs_bladecenter.generic_parse(TABLE)
    result = list(discover_ucs_bladecenter_faultinst(parsed))
    assert result == [Service()]


def test_check_ucs_bladecenter_faultinst() -> None:
    """Test check function for ucs_bladecenter_faultinst check."""
    parsed = ucs_bladecenter.generic_parse(TABLE)
    result = list(check_ucs_bladecenter_faultinst({}, parsed))
    assert result == [
        Result(state=State.WARN, summary="2 MAJOR Instances: test, test2"),
        Result(state=State.WARN, summary="1 MINOR Instances: baz"),
    ]
