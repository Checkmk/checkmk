#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import StringTable

from .checktestlib import Check

pytestmark = pytest.mark.checks

CHECK_NAME = "alcatel_cpu"


def test_discovery_function() -> None:
    check = Check(CHECK_NAME)
    assert list(check.run_discovery([["doesnt matter", "doesent matter"], ["doesnt matter"]]))


@pytest.mark.parametrize(
    "info, state_expected",
    [([["29"]], 0), ([["91"]], 1), ([["99"]], 2)],
)
def test_check_function(info: StringTable, state_expected: int) -> None:
    """
    Verifies if check function asserts warn and crit CPU levels.
    """
    assert Check(CHECK_NAME).run_check(None, {}, info)[0] == state_expected
