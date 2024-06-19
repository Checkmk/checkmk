#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.agent_based.v1.type_defs import StringTable

from .checktestlib import Check


@pytest.mark.parametrize(
    "info, expected_result",
    [
        (
            [
                ["[[PHT 00]]"],
                [
                    "Done",
                    "(unknown)",
                    "since",
                    "2016-02-11",
                    "09:14:16.2120000",
                    "local",
                    "time:2016-02-11",
                    "10:14:16.2120000",
                ],
            ],
            {
                "PHT 00": {
                    "log": "Done (unknown) since 2016-02-11 09:14:16.2120000 local time:2016-02-11 10:14:16.2120000",
                    "timestamp": "2016-02-11 09:14:16",
                }
            },
        ),
        ([["[[H11 11]]"]], {"H11 11": {"log": "", "timestamp": "not available"}}),
    ],
)
def test_parse_sap_hana_ess_migration(
    info: StringTable, expected_result: Mapping[str, Mapping[str, str]]
) -> None:
    result = Check("sap_hana_ess_migration").run_parse(info)
    assert result == expected_result
