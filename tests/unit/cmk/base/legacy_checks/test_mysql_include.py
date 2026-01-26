#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-untyped-def"


import pytest

from cmk.agent_based.v2 import StringTable
from cmk.plugins.mysql.agent_based.lib import mysql_parse_per_item

pytestmark = pytest.mark.checks


@pytest.mark.parametrize(
    "info,expected_items",
    [
        (
            [
                ["this is not a header line -> default item: mysql"],
                ["[[some/other/socket/name]]"],
                ["some", "info"],
                ["[[item/w/o/info]]"],
            ],
            ("mysql", "some/other/socket/name"),
        ),
    ],
)
def test_mysql_parse_per_item(info: StringTable, expected_items: tuple[str, str]) -> None:
    @mysql_parse_per_item
    def dummy_parse(info):
        return "Whoop"

    parsed = dummy_parse(info)

    assert parsed == {key: "Whoop" for key in expected_items}
