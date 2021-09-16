#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.testlib import Check


@pytest.mark.parametrize(
    "info, expected_result",
    [
        (
            [[51]],
            (
                1,
                "Disk percentage usage: 51 % (warn/crit at 40 %/60 %)",
                [("disk_utilization", 51, 40.0, 60.0)],
            ),
        )
    ],
)
def test_check_sophos_disk(info, expected_result):
    parsed_info = Check("sophos_disk").run_parse(info)
    result = Check("sophos_disk").run_check(None, {"disk_levels": (40, 60)}, parsed_info)
    assert result == expected_result
