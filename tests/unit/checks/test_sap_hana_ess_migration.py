#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from testlib import Check

pytestmark = pytest.mark.checks


@pytest.mark.parametrize("info, expected_result", [
    ([
        ['[[PHT 00]]'],
        [
            'Done', '(unknown)', 'since', '2016-02-11', '09:14:16.2120000', 'local',
            'time:2016-02-11', '10:14:16.2120000'
        ]
    ], {
        "PHT 00": {
            "log": "Done (unknown) since 2016-02-11 09:14:16.2120000 local time:2016-02-11 10:14:16.2120000",
            "timestamp": "2016-02-11 09:14:16"
        }
    }),
    ([['[[H11 11]]']], {
        "H11 11": {
            "log": "",
            "timestamp": "not available"
        }
    }),
])
@pytest.mark.usefixtures("config_load_all_checks")
def test_parse_sap_hana_ess_migration(info, expected_result):
    result = Check("sap_hana_ess_migration").run_parse(info)
    assert result == expected_result