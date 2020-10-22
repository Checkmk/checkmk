#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

import pytest  # type: ignore[import]
from testlib import Check  # type: ignore[import]
from cmk.base.check_api import MKCounterWrapped

pytestmark = pytest.mark.checks

_broken_info = [
    [
        '+ASM', 'FAILURE',
        'ORA-99999 tnsping failed for +ASM ERROR: ORA-28002: the password will expire within 1 days'
    ]
]

@pytest.mark.parametrize('info', [
    _broken_info,
])
@pytest.mark.usefixtures("config_load_all_checks")
def test_oracle_intance_uptime_discovery(info):
    main_check = Check('oracle_instance')
    check = Check('oracle_instance.uptime')
    assert list(check.run_discovery(main_check.run_parse(info))) == []


@pytest.mark.parametrize('info', [
    _broken_info,
])
@pytest.mark.usefixtures("config_load_all_checks")
def test_oracle_instance_uptime_check_error(info):
    main_check = Check('oracle_instance')
    check = Check('oracle_instance.uptime')
    with pytest.raises(MKCounterWrapped):
        check.run_check("+ASM", {}, main_check.run_parse(info))
