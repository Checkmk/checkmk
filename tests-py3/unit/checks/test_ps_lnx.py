#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
import pytest  # type: ignore[import]

pytestmark = pytest.mark.checks


INFO1 = [
    ["NODE", "[header]", "CGROUP", "USER", "VSZ", "RSS", "TIME", "ELAPSED", "PID", "COMMAND"],
    ["NODE", "1:name=systemd:/init.scope,", "root", "226036", "9736", "00:00:09", "05:14:30", "1", "/sbin/init", "--ladida"],
]

EXPECTED_ATTR1 = {
    "cgroup": "1:name=systemd:/init.scope,",
    "user": "root",
    "virtual": "226036",
    "physical": "9736",
    "cputime": "00:00:09/05:14:30",
    "process_id": "1",
}

EXPECTED_CMD1 = ["/sbin/init", "--ladida"]

@pytest.mark.parametrize("info, attrs, cmd", [
    (INFO1, EXPECTED_ATTR1, EXPECTED_CMD1),
])
def test_parse_ps_lnx(check_manager, info, attrs, cmd):
    check = check_manager.get_check("ps")
    parse_ps_lnx = check.context["parse_ps_lnx"]

    parsed_line = parse_ps_lnx(info)[0]
    ps_info, parsed_cmd = parsed_line[1], parsed_line[2:]

    for key, value in attrs.items():
        assert getattr(ps_info, key) == value
    assert parsed_cmd == cmd
