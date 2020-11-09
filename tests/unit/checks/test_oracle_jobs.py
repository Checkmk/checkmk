#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]
from testlib import Check  # type: ignore[import]
from cmk.base.check_api import MKCounterWrapped

pytestmark = pytest.mark.checks

_broken_info = [[
    'DB19',
    ' Debug (121): ORA-01219: database or pluggable database not open: queries allowed on fixed tables or views only'
]]


@pytest.mark.parametrize('info', [
    _broken_info,
])
@pytest.mark.usefixtures("config_load_all_checks")
def test_oracle_jobs_discovery_error(info):
    check = Check('oracle_jobs')
    assert list(check.run_discovery(info)) == []


@pytest.mark.parametrize('info', [
    _broken_info,
])
@pytest.mark.usefixtures("config_load_all_checks")
def test_oracle_jobs_check_error(info):
    check = Check('oracle_jobs')
    with pytest.raises(MKCounterWrapped):
        check.run_check("DB19.SYS.JOB1", {}, info)
