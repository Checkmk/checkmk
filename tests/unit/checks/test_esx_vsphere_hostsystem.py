#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]

pytestmark = pytest.mark.checks

section = {
    'hardware.cpuInfo.hz': '2599999766',
    'hardware.cpuInfo.numCpuCores': '16',
    'hardware.cpuInfo.numCpuPackages': '2',
    'hardware.cpuInfo.numCpuThreads': '16',
    'summary.quickStats.overallCpuUsage': '7393',
}


@pytest.mark.parametrize("section,params,result", [
    (section, {}, (0, 3)),
    (section, {
        'core_util_time_total': (0.0, 0, 0)
    }, (2, 4)),
])
def test_esx_vsphere_hostsystem_cpu_usage(check_manager, monkeypatch, section, params, result):
    max_state, len_result = result
    # To be indenpendent on NOW we use len(result)
    check = check_manager.get_check("esx_vsphere_hostsystem.cpu_usage")
    # Mock timestamp = get_item_state to zero
    # Then we calculate: high_load_duration = (this_time - timestamp)
    # Thereby we get     high_load_duration = NOW which is always greater than above levels
    #                    and we get an additional sub result
    monkeypatch.setitem(check.context, "get_item_state", lambda _, __: 1)
    check_result = list(check.run_check(None, params, [section, None]))
    assert len_result == len(check_result)
    assert max_state == max([entry[0] for entry in check_result])
