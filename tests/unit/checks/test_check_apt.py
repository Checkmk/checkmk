#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Mapping, Sequence, Tuple

import pytest

from testlib import Check

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
_PARAMS = {
    "normal": 1,
    "removals": 1,
    "security": 2,
}


@pytest.mark.parametrize(
    "info, expected_result",
    [
        pytest.param(
            _SECTION_UPDATES_AV,
            [(None, {})],
            id="updates_available",
        ),
        pytest.param(
            _SECTION_NO_UPDATES,
            [(None, {})],
            id="no_updates",
        ),
        pytest.param(
            _SECTION_BROKEN,
            [],
            id="broken_section",
        ),
    ],
)
def test_inventory_apt(
    info: Sequence[Sequence[str]],
    expected_result: Sequence[Tuple[None, Mapping[str, Any]]],
) -> None:
    assert list(Check("apt").run_discovery(info)) == expected_result


@pytest.mark.parametrize(
    "info, expected_result",
    [
        pytest.param(
            _SECTION_UPDATES_AV,
            [
                (1, '3 normal updates', [('normal_updates', 3)]),
                (1, '2 auto removals (default-java-plugin, icedtea-8-plugin)', [('removals', 2)]),
                (2, '1 security updates (librsvg2-2)', [('security_updates', 1)]),
            ],
            id="updates_available",
        ),
        pytest.param(
            _SECTION_NO_UPDATES,
            [(0, 'No updates pending for installation')],
            id="no_updates",
        ),
    ],
)
def test_check_apt(
    info: Sequence[Sequence[str]],
    expected_result: Sequence[Tuple[Any]],
) -> None:
    assert list(Check("apt").run_check(None, _PARAMS, info)) == expected_result
