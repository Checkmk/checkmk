#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.plugins.ucs_bladecenter.special_agent.agent_ucs_bladecenter import (
    B_SERIES_REGEX,
    C_SERIES_REGEX,
)


def test_c_series_regex() -> None:
    assert C_SERIES_REGEX.match("HXAF240C")
    assert C_SERIES_REGEX.match("UCSC")
    assert C_SERIES_REGEX.match("APIC")


def test_b_series_regex() -> None:
    assert B_SERIES_REGEX.match("UCSB")
