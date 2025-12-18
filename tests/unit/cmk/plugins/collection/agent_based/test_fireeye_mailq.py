#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

import pytest

from cmk.base.legacy_checks.fireeye_mailq import (
    check_fireeye_mailq,
    dicsover_fireeye_mailq,
    parse_fireeye_mailq,
)


@pytest.fixture(scope="module", name="section")
def _get_section() -> object:
    return parse_fireeye_mailq([["0", "0", "0", "3", "5"]])


def test_discover_somehting(section: object) -> None:
    assert list(dicsover_fireeye_mailq(section)) == [(None, {})]


def test_check(section: object) -> None:
    params = {
        # deferred not present
        "hold": (1, 5),  # OK case
        "active": (1, 5),  # WARN case
        "drop": (1, 5),  # CRIT case
    }
    result = list(check_fireeye_mailq(None, params, section))
    # Legacy check returns list of tuples (state, text, perfdata)
    # Perfdata format: (name, value, warn, crit) - check_levels format
    assert result == [
        (0, "Mails in deferred queue: 0", [("mail_queue_deferred_length", 0, None, None)]),
        (0, "Mails in hold queue: 0", [("mail_queue_hold_length", 0, 1, 5)]),
        (0, "Mails in incoming queue: 0", [("mail_queue_incoming_length", 0, None, None)]),
        (1, "Mails in active queue: 3 (warn/crit at 1/5)", [("mail_queue_active_length", 3, 1, 5)]),
        (2, "Mails in drop queue: 5 (warn/crit at 1/5)", [("mail_queue_drop_length", 5, 1, 5)]),
    ]
