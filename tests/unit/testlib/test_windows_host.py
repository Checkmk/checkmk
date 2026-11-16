#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.testlib.system.windows_host import quote


@pytest.mark.parametrize(
    "argument, quoted",
    [
        ("C:\\cmk-test\\agent.msi", "'C:\\cmk-test\\agent.msi'"),
        ("it's", "'it''s'"),
        ("C:\\a b", "'C:\\a b'"),
        ("C:\\ab\\", "'C:\\ab\\'"),
    ],
)
def test_quote_makes_literal_powershell_string(argument: str, quoted: str) -> None:
    assert quote(argument) == quoted


@pytest.mark.parametrize(
    "argument",
    [
        pytest.param('say "hi"', id="double quote"),
        pytest.param("", id="empty string"),
        pytest.param("C:\\a b\\", id="space and trailing backslash"),
        pytest.param("C:\\a\tb\\", id="tab and trailing backslash"),
    ],
)
def test_quote_rejects_what_powershell_51_corrupts(argument: str) -> None:
    with pytest.raises(ValueError):
        quote(argument)
