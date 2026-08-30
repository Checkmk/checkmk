#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.legacy_checks.fireeye_active_vms import (
    check_fireeye_active_vms,
    discover_fireeye_active_vms,
)

SECTION = [["42"]]


def test_discover_nothing() -> None:
    assert not list(discover_fireeye_active_vms([]))


def test_discover_something() -> None:
    assert list(discover_fireeye_active_vms(SECTION)) == [Service()]


def test_check_ok() -> None:
    assert list(check_fireeye_active_vms({"vms": (50, 100)}, SECTION)) == [
        Result(state=State.OK, summary="Active VMs: 42"),
        Metric("active_vms", 42.0, levels=(50.0, 100.0)),
    ]


def test_check_warn() -> None:
    assert list(check_fireeye_active_vms({"vms": (23, 50)}, SECTION)) == [
        Result(state=State.WARN, summary="Active VMs: 42 (warn/crit at 23/50)"),
        Metric("active_vms", 42.0, levels=(23.0, 50.0)),
    ]


def test_check_crit() -> None:
    assert list(check_fireeye_active_vms({"vms": (23, 36)}, SECTION)) == [
        Result(state=State.CRIT, summary="Active VMs: 42 (warn/crit at 23/36)"),
        Metric("active_vms", 42.0, levels=(23.0, 36.0)),
    ]
