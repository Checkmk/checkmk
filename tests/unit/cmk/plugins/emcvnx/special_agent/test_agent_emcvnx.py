#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pytest

from cmk.plugins.emcvnx.special_agent import agent_emcvnx


@pytest.mark.parametrize(
    "line, expected",
    [
        ("aa\n", "aa"),
        ("aa\r", "aa"),
        ("aa\r\n", "aa"),
        ("aa", "aa"),
    ],
)
def test_normalize_str(line: str, expected: str) -> None:
    assert expected == agent_emcvnx.normalize_str(line)
