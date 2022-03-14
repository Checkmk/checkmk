#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from cmk.base.check_legacy_includes.mysql import mysql_parse_per_item

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
def test_mysql_parse_per_item(info, expected_items):
    @mysql_parse_per_item  # type: ignore[name-defined] # pylint: disable=undefined-variable
    def dummy_parse(info):
        return "Whoop"

    parsed = dummy_parse(info)

    assert parsed == {key: "Whoop" for key in expected_items}
