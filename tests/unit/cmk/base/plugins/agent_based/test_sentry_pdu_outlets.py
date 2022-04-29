#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based.sentry_pdu_outlets import parse_sentry_pdu_outlets


@pytest.mark.parametrize(
    "string_table, expected_section",
    [([["A1", "A_Outlet1", "0"], ["A2", "A_Outlet2", "3"]], {"A1 A_1": 0, "A2 A_2": 3})],
)
def test_parse_sentry_pdu_outlets(string_table, expected_section):
    section = parse_sentry_pdu_outlets(string_table)
    assert section == expected_section
