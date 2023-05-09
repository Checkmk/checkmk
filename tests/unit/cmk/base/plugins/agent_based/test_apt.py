#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Optional

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import StringTable
from cmk.base.plugins.agent_based.apt import _data_is_valid, parse_apt, Section

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
_SECTION_SEC_UPDATES = [
    ["Inst linux-libc-dev [4.9.130-2] (4.9.228-1 Debian:9.13/oldstable [amd64]) []"],
    [
        "Inst libapt-pkg5.0 [1.4.8] (1.4.10 Debian:9.13/oldstable, Debian-Security:9/oldstable [amd64])"
    ],
    [
        "Inst libexpat1 [2.2.0-2+deb9u1] (2.2.0-2+deb9u3 Debian:9.13/oldstable, Debian-Security:9/oldstable [amd64])"
    ],
    [
        "Inst tzdata [2021a-0ubuntu0.16.04] (2021e-0ubuntu0.16.04+esm1 UbuntuESM:16.04/xenial-infra-security [all])"
    ],
    [
        "Inst bind9-host [1:9.10.3.dfsg.P4-8ubuntu1.19] (1:9.10.3.dfsg.P4-8ubuntu1.19+esm1 UbuntuESM:16.04/xenial-infra-security [amd64]) []"
    ],
]
_SECTION_KERNEL_UPDATES = [
    ["Inst linux-image-4.19.0-19-amd64 (4.19.232-1 Debian-Security:10/oldstable [amd64])"],
    [
        "Inst linux-image-amd64 [4.19+105+deb10u13] (4.19+105+deb10u14 Debian-Security:10/oldstable [amd64])"
    ],
]
_SECTION_NO_ESM_SUPPORT = [
    ["Enable UA Infra: ESM to receive additional future security updates."],
    ["See https://ubuntu.com/16-04 or run: sudo ua status"],
    ["Ubuntu comes with ABSOLUTELY NO WARRANTY, to the extent permitted by"],
    ["applicable law."],
    [
        "Inst ubuntu-advantage-tools [27.4.1~16.04.1] (27.4.2~16.04.1 Ubuntu:16.04/xenial-updates [amd64])"
    ],
]
_SECTION_ESM_SUPPORT = [
    ["*The following packages could receive security updates with UA Infra: ESM service enabled:"],
    ["libglib2.0-data libglib2.0-0"],
    ["Learn more about UA Infra: ESM service for Ubuntu 16.04 at https://ubuntu.com/16-04"],
    ["Ubuntu comes with ABSOLUTELY NO WARRANTY, to the extent permitted by"],
    ["applicable law."],
    [
        "Inst ubuntu-advantage-tools [27.4.1~16.04.1] (27.4.2~16.04.1 Ubuntu:16.04/xenial-updates [amd64])"
    ],
]
_SECTION_UBUNTU_PRO_ADVERTISEMENT = [
    ["Receive additional future security updates with Ubuntu Pro."],
    ["Learn more about Ubuntu Pro at https://ubuntu.com/pro"],
    ["Inst base-files [9.9+deb9u9] (9.9+deb9u11 Debian:9.11/oldstable [amd64])"],
]
_SECTION_UBUNTU_PRO_ADVERTISEMENT_TWO = [
    ["Try Ubuntu Pro beta with a free personal subscription on up to 5 machines"],
    ["Learn more at https://ubuntu.com/pro"],
    ["Inst base-files [9.9+deb9u9] (9.9+deb9u11 Debian:9.11/oldstable [amd64])"],
]
_SECTION_UBUNTU_PRO_ADVERTISEMENT_ONLY = [
    ["Try Ubuntu Pro beta with a free personal subscription on up to 5 machines"],
    ["Learn more at https://ubuntu.com/pro"],
]


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
        pytest.param(
            _SECTION_SEC_UPDATES,
            True,
            id="security_upates_line",
        ),
        pytest.param(
            _SECTION_KERNEL_UPDATES,
            True,
        ),
        pytest.param(
            _SECTION_UBUNTU_PRO_ADVERTISEMENT,
            False,
        ),
        pytest.param(
            _SECTION_UBUNTU_PRO_ADVERTISEMENT_TWO,
            False,
        ),
        pytest.param(
            _SECTION_UBUNTU_PRO_ADVERTISEMENT_ONLY,
            False,
        ),
        pytest.param(
            _SECTION_UBUNTU_PRO_ADVERTISEMENT + _SECTION_NO_ESM_SUPPORT,
            False,
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
        pytest.param(
            _SECTION_SEC_UPDATES,
            Section(
                ["linux-libc-dev"],
                [],
                ["libapt-pkg5.0", "libexpat1", "tzdata", "bind9-host"],
            ),
            id="security_upates_line",
        ),
        pytest.param(
            _SECTION_NO_ESM_SUPPORT,
            Section([], [], [], no_esm_support=True),
            id="no_esm_support",
        ),
        pytest.param(
            _SECTION_ESM_SUPPORT,
            Section(["ubuntu-advantage-tools"], [], []),
            id="esm_support",
        ),
        pytest.param(
            _SECTION_KERNEL_UPDATES,
            Section(
                updates=[],
                removals=[],
                sec_updates=["linux-image-4.19.0-19-amd64", "linux-image-amd64"],
            ),
            id="security_kernel_debian_line",
        ),
        pytest.param(
            _SECTION_UBUNTU_PRO_ADVERTISEMENT,
            Section(
                updates=["base-files"],
                removals=[],
                sec_updates=[],
            ),
            id="ubuntu_pro_advertisement",
        ),
        pytest.param(
            _SECTION_UBUNTU_PRO_ADVERTISEMENT_TWO,
            Section(
                updates=["base-files"],
                removals=[],
                sec_updates=[],
            ),
            id="ubuntu_pro_advertisement 2",
        ),
        pytest.param(
            _SECTION_UBUNTU_PRO_ADVERTISEMENT_ONLY,
            Section(updates=[], removals=[], sec_updates=[]),
            id="ubuntu_pro_advertisement only",
        ),
        pytest.param(
            _SECTION_UBUNTU_PRO_ADVERTISEMENT + _SECTION_ESM_SUPPORT,
            Section(
                updates=[
                    "base-files",
                    "ubuntu-advantage-tools",
                ],
                removals=[],
                sec_updates=[],
            ),
            id="ubuntu_pro_advertisement_first_esm_enabled_second",
        ),
        pytest.param(
            _SECTION_ESM_SUPPORT + _SECTION_UBUNTU_PRO_ADVERTISEMENT,
            Section(
                updates=[
                    "ubuntu-advantage-tools",
                    "base-files",
                ],
                removals=[],
                sec_updates=[],
            ),
            id="esm_enabled_first_ubuntu_pro_advertisement_second",
        ),
    ],
)
def test_parse_apt(
    string_table: StringTable,
    expected_result: Optional[Section],
) -> None:
    assert parse_apt(string_table) == expected_result
