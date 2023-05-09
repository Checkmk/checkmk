#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Mapping, Sequence, Tuple

import pytest

from tests.testlib import Check

from cmk.base.plugins.agent_based.apt import parse_apt, Section

_SECTION_UPDATES_AV = [
    ["Remv default-java-plugin [2:1.8-58]"],
    ["Remv icedtea-8-plugin [1.6.2-3.1]"],
    ["Inst default-jre [2:1.8-58] (2:1.8-58+deb9u1 Debian:9.11/oldstable [amd64]) []"],
    ["Inst default-jre-headless [2:1.8-58] (2:1.8-58+deb9u1 Debian:9.11/oldstable [amd64])"],
    ["Inst icedtea-netx [1.6.2-3.1] (1.6.2-3.1+deb9u1 Debian:9.11/oldstable [amd64])"],
    ["Inst librsvg2-2 [2.40.16-1+b1] (2.40.21-0+deb9u1 Debian-Security:9/oldstable [amd64])"],
]
_SECTION_NO_UPDATES = [["No updates pending for installation"]]
_SECTION_NO_ESM_SUPPORT = [
    ["Enable UA Infra: ESM to receive additional future security updates."],
    ["See https://ubuntu.com/16-04 or run: sudo ua status"],
    ["Ubuntu comes with ABSOLUTELY NO WARRANTY, to the extent permitted by"],
    ["applicable law."],
    [
        "Inst ubuntu-advantage-tools [27.4.1~16.04.1] (27.4.2~16.04.1 Ubuntu:16.04/xenial-updates [amd64])"
    ],
]
DEFAULT_PARAMS = {
    "normal": 1,
    "removals": 1,
    "security": 2,
}


@pytest.mark.parametrize(
    "section",
    [
        pytest.param(
            parse_apt(_SECTION_UPDATES_AV),
            id="updates_available",
        ),
        pytest.param(
            parse_apt(_SECTION_NO_UPDATES),
            id="no_updates",
        ),
    ],
)
def test_inventory_apt(section: Section) -> None:
    assert list(Check("apt").run_discovery(section)) == [(None, {})]


@pytest.mark.parametrize(
    "params, section, expected_result",
    [
        pytest.param(
            DEFAULT_PARAMS,
            parse_apt(_SECTION_UPDATES_AV),
            [
                (1, "3 normal updates", [("normal_updates", 3)]),
                (1, "2 auto removals (default-java-plugin, icedtea-8-plugin)", [("removals", 2)]),
                (2, "1 security updates (librsvg2-2)", [("security_updates", 1)]),
            ],
            id="updates_available",
        ),
        pytest.param(
            DEFAULT_PARAMS,
            parse_apt(_SECTION_NO_UPDATES),
            [(0, "No updates pending for installation")],
            id="no_updates",
        ),
        pytest.param(
            DEFAULT_PARAMS,
            parse_apt(_SECTION_NO_ESM_SUPPORT),
            [(2, "System could receive security updates, but needs extended support license")],
            id="no_esm_support",
        ),
        pytest.param(
            {"normal": 0, "removals": 2, "security": 1},
            parse_apt(_SECTION_UPDATES_AV),
            [
                (0, "3 normal updates", [("normal_updates", 3)]),
                (2, "2 auto removals (default-java-plugin, icedtea-8-plugin)", [("removals", 2)]),
                (1, "1 security updates (librsvg2-2)", [("security_updates", 1)]),
            ],
            id="changed_severity",
        ),
    ],
)
def test_check_apt(
    params: Mapping[str, int],
    section: Section,
    expected_result: Sequence[Tuple[Any]],
) -> None:
    assert list(Check("apt").run_check(None, params, section)) == expected_result
