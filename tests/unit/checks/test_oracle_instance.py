#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

import pytest

from tests.testlib import Check

from cmk.base.check_api import MKCounterWrapped
from cmk.base.plugins.agent_based.oracle_instance import parse_oracle_instance

pytestmark = pytest.mark.checks

PARSED = parse_oracle_instance([[
    '+ASM', 'FAILURE',
    'ORA-99999 tnsping failed for +ASM ERROR: ORA-28002: the password will expire within 1 days'
]])


def test_oracle_intance_uptime_discovery():
    check = Check('oracle_instance.uptime')
    assert list(check.run_discovery(PARSED)) == []


def test_oracle_instance_uptime_check_error():
    check = Check('oracle_instance.uptime')
    with pytest.raises(MKCounterWrapped):
        check.run_check("+ASM", {}, PARSED)
