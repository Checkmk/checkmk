#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v1 import regex


def test_regex() -> None:
    """
    We use `re.compile`. This is just a sanity check."""
    assert regex("foo").match("foobar")
