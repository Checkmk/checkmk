#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Mapping, Sequence, Tuple

import pytest

from cmk.utils.type_defs import CheckPluginName, SectionName

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State

from tests.unit.conftest import FixRegister


@pytest.mark.parametrize(
    "info, expected_parsed",
    [
        pytest.param(
            [
                [
                    "quota QUOTA-10",
                    "quota-type tree",
                    "disk-limit 5",
                    "volume quota_common_10",
                    "disk-used 0",
                ]
            ],
            {
                "QUOTA-10": {
                    "quota": "QUOTA-10",
                    "quota-type": "tree",
                    "disk-limit": "5",
                    "volume": "quota_common_10",
                    "disk-used": "0",
                },
            },
            id="qtree_without_quota_users",
        ),
        pytest.param(
            [
                [
                    "quota QUOTA-10",
                    "quota-type tree",
                    "quota-users user",
                    "disk-limit 6",
                    "volume quota_common_10",
                    "disk-used 0",
                ]
            ],
            {
                "QUOTA-10.user": {
                    "quota": "QUOTA-10",
                    "quota-type": "tree",
                    "quota-users": "user",
                    "disk-limit": "6",
                    "volume": "quota_common_10",
                    "disk-used": "0",
                },
            },
            id="qtree_with_quota_users",
        ),
    ],
)
def test_parse_netapp_api_qtree_quota(
    fix_register: FixRegister, info: Sequence[Sequence[str]], expected_parsed: Mapping
) -> None:
    section_plugin = fix_register.agent_sections[SectionName("netapp_api_qtree_quota")]
    result = section_plugin.parse_function(info)
    assert result == expected_parsed


@pytest.mark.parametrize(
    "parsed, expected_discovery",
    [
        pytest.param(
            {
                "QUOTA-10.user": {
                    "quota": "QUOTA-10",
                    "quota-type": "tree",
                    "quota-users": "user",
                    "disk-limit": "6",
                    "volume": "quota_common_10",
                    "disk-used": "0",
                },
            },
            [Service(item="QUOTA-10.user")],
            id="qtree",
        ),
    ],
)
def test_inventory_netapp_api_qtree_quota(
    fix_register: FixRegister,
    parsed: Mapping,
    expected_discovery: Sequence[Tuple[str, Mapping]],
) -> None:
    check_plugin = fix_register.check_plugins[CheckPluginName("netapp_api_qtree_quota")]
    result = list(check_plugin.discovery_function(parsed))
    assert result == expected_discovery


@pytest.mark.parametrize(
    "parsed, item, expected_result",
    [
        pytest.param(
            {
                "QUOTA-10.user": {
                    "quota": "QUOTA-10",
                    "quota-type": "tree",
                    "quota-users": "user",
                    "disk-limit": "6",
                    "volume": "quota_common_10",
                    "disk-used": "0",
                },
            },
            "QUOTA-10.user",
            [
                Result(state=State.OK, summary="0% used (0.00 B of 6.00 kB)"),
                Metric(
                    "fs_used", 0.0, levels=(0.0046875, 0.0052734375), boundaries=(0.0, 0.005859375)
                ),
                Metric("fs_size", 0.005859375),
                Metric("fs_used_percent", 0.0),
            ],
            id="qtree_without_inodes",
        ),
        pytest.param(
            {
                "QUOTA-10.user": {
                    "quota": "QUOTA-10",
                    "quota-type": "tree",
                    "quota-users": "user",
                    "disk-limit": "",
                    "volume": "quota_common_10",
                    "disk-used": "0",
                },
            },
            "QUOTA-10.user",
            [
                Result(state=State.UNKNOWN, summary="Qtree has no disk limit set"),
            ],
            id="qtree_no_disk_limit",
        ),
        pytest.param(
            {
                "QUOTA-10.user": {
                    "quota": "QUOTA-10",
                    "quota-type": "tree",
                    "quota-users": "user",
                    "disk-limit": "6",
                    "volume": "quota_common_10",
                    "disk-used": "0",
                    "files-used": "99",
                    "file-limit": "100",
                },
            },
            "QUOTA-10.user",
            [
                Result(
                    state=State.OK,
                    summary="0% used (0.00 B of 6.00 kB), Inodes used: 99, Inodes available: 1 (1.00%)",
                ),
                Metric(
                    "fs_used", 0.0, levels=(0.0046875, 0.0052734375), boundaries=(0.0, 0.005859375)
                ),
                Metric("fs_size", 0.005859375),
                Metric("fs_used_percent", 0.0),
                Metric("inodes_used", 99.0, boundaries=(0.0, 100.0)),
            ],
            id="qtree_with_inodes",
        ),
    ],
)
def test_check_netapp_api_qtree_quota(
    fix_register: FixRegister,
    parsed: Mapping,
    item: str,
    expected_result: Sequence[Tuple[str, Mapping]],
) -> None:
    check_plugin = fix_register.check_plugins[CheckPluginName("netapp_api_qtree_quota")]
    result = list(check_plugin.check_function(item=item, params={}, section=parsed))
    assert result == expected_result
