#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import IgnoreResultsError
from cmk.plugins.vsphere.agent_based.esx_vsphere_counters import parse_esx_vsphere_counters
from cmk.plugins.vsphere.agent_based.esx_vsphere_counters_2 import (
    check_esx_vsphere_counters_uptime,
)


def test_check_esx_vsphere_counters_uptime_all_negative_one() -> None:
    """Regression: all-(-1) uptime samples must raise IgnoreResultsError."""
    section = parse_esx_vsphere_counters([["sys.uptime", "", "-1#-1#-1", "second"]])
    with pytest.raises(IgnoreResultsError):
        list(check_esx_vsphere_counters_uptime({}, section))


def test_check_esx_vsphere_counters_uptime_valid() -> None:
    """Normal uptime counter (no -1) should not raise."""
    section = parse_esx_vsphere_counters([["sys.uptime", "", "630664", "second"]])
    results = list(check_esx_vsphere_counters_uptime({}, section))
    assert results  # some output produced
