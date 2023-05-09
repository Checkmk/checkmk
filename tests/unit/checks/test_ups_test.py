#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from testlib import Check  # type: ignore[import]


@pytest.mark.usefixtures("config_load_all_checks")
def test_ups_test_unknown_test_result():
    check = Check("ups_test")
    assert list(check.run_check(
        None,
        (0, 0),
        [[['2400776998']], [['0', '0', 'aardvark']]],
    ))[0] == (3, "Last test: unknown (aardvark)")
