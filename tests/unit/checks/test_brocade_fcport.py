#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.testlib import Check


@pytest.mark.parametrize(
    "info, expected_result",
    [([[], [], [["", "", ""]], []], None), ([[["", "", 3]], [], [["", "", ""]], []], None)],
)
def test_services_split(info, expected_result):
    result = Check("brocade_fcport").run_parse(info)
    assert result == expected_result
