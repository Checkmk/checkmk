#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

import pytest

from cmk.base.legacy_checks.oracle_longactivesessions import (
    check_oracle_longactivesessions,
    parse_oracle_longactivesessions,
)


@pytest.mark.xfail(
    strict=True,
    raises=ValueError,
    reason="Crash report 2e48e266-d1c2-11f0-9c9f-00155d017705: ValueError",
)
def test_check_session_row_with_extra_field() -> None:
    # Crash group 4502: a non-ASCII OS user name was split into two fields, so
    # the session row has ten fields instead of nine.
    section = parse_oracle_longactivesessions(
        [
            ["orcl", "398", "64367", "machine", "4352:6876", "os", "user", "prog.exe", "1805", "x"],
            ["orcl", "", "", "", "", "", "", "", ""],
        ]
    )

    assert check_oracle_longactivesessions("orcl", {"levels": (500, 1000)}, section) == (
        0,
        "1 Session 398: cannot parse session details, got 10 fields (expected 9)",
        [("count", 1, 500, 1000)],
    )
