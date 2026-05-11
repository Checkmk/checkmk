#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.plugins.ucs_bladecenter.special_agent.agent_ucs_bladecenter import (
    B_SERIES_REGEX,
    C_SERIES_REGEX,
)


def test_c_series_regex_matches() -> None:
    assert C_SERIES_REGEX.match("UCSC")
    assert C_SERIES_REGEX.match("APIC")
    assert C_SERIES_REGEX.match("HX220C")
    assert C_SERIES_REGEX.match("HX240C")
    assert C_SERIES_REGEX.match("HX480C")
    assert C_SERIES_REGEX.match("HXAF220C")
    assert C_SERIES_REGEX.match("HXAF240C")
    assert C_SERIES_REGEX.match("HXAF480C")
    assert C_SERIES_REGEX.match("BE6H")
    assert C_SERIES_REGEX.match("BE7H")
    assert C_SERIES_REGEX.match("BE6M")
    assert C_SERIES_REGEX.match("BE7M")


def test_c_series_regex_no_match() -> None:
    assert not C_SERIES_REGEX.match("UNKNOWN")
    assert not C_SERIES_REGEX.match("UCSB")
    assert not C_SERIES_REGEX.match("UCSBA")
    assert not C_SERIES_REGEX.match("")


def test_b_series_regex_matches() -> None:
    assert B_SERIES_REGEX.match("UCSB")


def test_b_series_regex_no_match() -> None:
    assert not C_SERIES_REGEX.match("UNKNOWN")
    assert not B_SERIES_REGEX.match("UCSC")
    assert not B_SERIES_REGEX.match("APIC")
    assert not B_SERIES_REGEX.match("UCSBA")
    assert not B_SERIES_REGEX.match("BE6H")
    assert not B_SERIES_REGEX.match("")
