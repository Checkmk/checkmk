#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from testlib import Check

pytestmark = pytest.mark.checks


@pytest.mark.usefixtures("config_load_all_checks")
def test_check_3par_system_no_online_and_cluster_nodes() -> None:
    check_plugin = Check("3par_system")

    string_table = [[
        '{"id":168676,"name":"test-name","systemVersion":"9.5.3.12","IPv4Addr":"172.17.37.20","model":"HPEAlletra9060","serialNumber":"CZ222908M6","totalNodes":2,"masterNode":0}'
    ]]

    assert list(check_plugin.run_check("", {}, check_plugin.run_parse(string_table))) == [
        (0, 'Model: HPEAlletra9060, Version: 9.5.3.12, Serial number: CZ222908M6, Online '
         'nodes: 0/0')
    ]
