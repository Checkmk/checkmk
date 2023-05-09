#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]
from testlib import Check  # type: ignore[import]

from checktestlib import DiscoveryResult, assertDiscoveryResultsEqual


@pytest.mark.usefixtures("config_load_all_checks")
def test_cisco_ucs_hdd_parse_and_discovery():
    info = [
        ['1', 'HDD', '1', '10L0A089FJPF', '572325', 'TOSHIBA', '1'],
        ['5', '', '6', '', '0', '', '0'],
        ['5', '', '9', '', '0', '', '0'],
    ]

    expected = DiscoveryResult([
        ('1', None),
        ('5', None),
    ])

    check = Check('cisco_ucs_hdd')
    actual = DiscoveryResult(check.run_discovery(check.run_parse(info)))
    assertDiscoveryResultsEqual(check, actual=actual, expected=expected)
