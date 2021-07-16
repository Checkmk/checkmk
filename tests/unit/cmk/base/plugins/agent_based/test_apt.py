#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Optional
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import StringTable
from cmk.base.plugins.agent_based.apt import _data_is_valid, parse_apt, Section

import pytest

_SECTION_UPDATES_AV = [
    ["Remv default-java-plugin [2:1.8-58]"],
    ["Remv icedtea-8-plugin [1.6.2-3.1]"],
    ["Inst default-jre [2:1.8-58] (2:1.8-58+deb9u1 Debian:9.11/oldstable [amd64]) []"],
    ["Inst default-jre-headless [2:1.8-58] (2:1.8-58+deb9u1 Debian:9.11/oldstable [amd64])"],
    ["Inst icedtea-netx [1.6.2-3.1] (1.6.2-3.1+deb9u1 Debian:9.11/oldstable [amd64])"],
    ["Inst librsvg2-2 [2.40.16-1+b1] (2.40.21-0+deb9u1 Debian-Security:9/oldstable [amd64])"],
]
_SECTION_NO_UPDATES = [["No updates pending for installation"]]
_SECTION_BROKEN = [["not found"]]


@pytest.mark.parametrize(
    "string_table, expected_result",
    [
        pytest.param(
            _SECTION_UPDATES_AV,
            True,
            id="updates_available",
        ),
        pytest.param(
            _SECTION_NO_UPDATES,
            True,
            id="no_updates",
        ),
        pytest.param(
            _SECTION_BROKEN,
            False,
            id="broken_section",
        ),
    ],
)
def test_data_is_valid(
    string_table: StringTable,
    expected_result: bool,
) -> None:
    assert _data_is_valid(string_table) is expected_result


@pytest.mark.parametrize(
    "string_table, expected_result",
    [
        pytest.param(
            _SECTION_UPDATES_AV,
            Section(
                ["default-jre", "default-jre-headless", "icedtea-netx"],
                ["default-java-plugin", "icedtea-8-plugin"],
                ["librsvg2-2"],
            ),
            id="updates_available",
        ),
        pytest.param(
            _SECTION_NO_UPDATES,
            Section([], [], []),
            id="no_updates",
        ),
        pytest.param(
            _SECTION_BROKEN,
            None,
            id="broken_section",
        ),
    ],
)
def test_parse_apt(
    string_table: StringTable,
    expected_result: Optional[Section],
) -> None:
    assert parse_apt(string_table) == expected_result
