#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Note: this test only tests `parse_f5_bigip_vcmpfailover()` since f5_bigip_vcmpfailover
#       uses function from f5_bigip_cluster_status

import pytest  # type: ignore[import]

from cmk.base.plugins.agent_based.f5_bigip_vcmpfailover import parse_f5_bigip_vcmpfailover


@pytest.mark.parametrize("string_table,expected_parsed_data", [
    ([[['0', '4']]], 4),
    ([[['3', '4']]], None),
])
def test_parse_f5_bigip_vcmpfailover(string_table, expected_parsed_data):
    assert parse_f5_bigip_vcmpfailover(string_table) == expected_parsed_data
