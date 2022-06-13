#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, State
from cmk.base.plugins.agent_based.zerto import check, parse


def test_parse_errors():
    section = parse([["Error: reason"]])
    assert section.has_errors
    assert section.error_details == "reason"


def test_parse_ok():
    section = parse([["Initialization OK"]])
    assert not section.has_errors


def test_check_errors():
    results = list(check(parse([["Error: reason"]])))
    assert len(results) == 1
    assert results[0] == Result(state=State.CRIT, summary="Error starting agent", details="reason")


def test_check_ok():
    results = list(check(parse([["Initializtion OK"]])))
    assert len(results) == 1
    assert results[0] == Result(state=State.OK, summary="Agent started without problem")
