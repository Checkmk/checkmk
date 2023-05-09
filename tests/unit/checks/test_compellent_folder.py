#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from testlib import Check

pytestmark = pytest.mark.checks


@pytest.mark.parametrize("info, expected_result",
                         [([["", "", ""], ["2", "237273", "130456"]], [("2", {})])])
@pytest.mark.usefixtures("config_load_all_checks")
def test_inventory_dell_compellent_folder(info, expected_result):
    result = Check("dell_compellent_folder").run_discovery(info)
    assert list(result) == expected_result