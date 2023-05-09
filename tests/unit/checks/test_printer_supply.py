#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code packageii

import pytest

from testlib import Check

pytestmark = pytest.mark.checks


@pytest.mark.parametrize(
    "string_table, expected_result",
    [
        pytest.param(
            [
                [['1.1', 'black\x00']],
                [['Patrone Schwarz 508A HP CF360A\x00', '19', '100', '9', '3', '1']],
            ],
            [
                [
                    'Patrone Schwarz 508A HP CF360A\x00',
                    '19',
                    '100',
                    '9',
                    '3',
                    '1',
                    'black',
                ],
            ],
            id="with null bytes",
        ),
    ],
)
@pytest.mark.usefixtures("config_load_all_checks")
def test_parse_printer_supply(string_table, expected_result):
    assert Check("printer_supply").run_parse(string_table) == expected_result
