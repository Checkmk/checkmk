#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

from cmk.base.legacy_checks.netgear_powersupplies import (
    check_netgear_powersupplies,
    parse_netgear_powersupplies,
)


def test_check_netgear_powersupplies_reports_unknown_state() -> None:
    # The switch reports a power supply state the plugin does not know.
    section = parse_netgear_powersupplies([["1.0", "11"], ["1.1", "2"]])
    assert check_netgear_powersupplies("1/0", None, section) == (
        3,
        "Status: unknown state '11' (expected 1, 2 or 3)",
    )
