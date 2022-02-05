#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Mapping, Sequence

import pytest

from tests.unit.conftest import FixRegister

from cmk.utils.type_defs import CheckPluginName, SectionName

import cmk.base.plugins.agent_based.netapp_api_qtree_quota as qtree_quota
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import CheckResult
from cmk.base.plugins.agent_based.netapp_api_qtree_quota import get_item_names, Qtree


@pytest.fixture(name="value_store_patch")
def value_store_fixture(monkeypatch) -> None:
    value_store_patched = {
        "QUOTA-10.user.delta": [0, 0],
    }
    monkeypatch.setattr(qtree_quota, "get_value_store", lambda: value_store_patched)


@pytest.mark.parametrize(
    "string_table, expected_parsed",
    [
        pytest.param(
            [
                [
                    "quota QUOTA-10",
                    "quota-type tree",
                    "disk-limit 5",
                    "volume quota_common_10",
                    "disk-used 0",
                ],
            ],
            {
                "QUOTA-10": Qtree(
                    quota="QUOTA-10",
                    quota_users="",
                    quota_type="tree",
                    volume="quota_common_10",
                    disk_limit="5",
                    disk_used="0",
                    files_used="",
                    file_limit="",
                ),
                "quota_common_10/QUOTA-10": Qtree(
                    quota="QUOTA-10",
                    quota_users="",
                    quota_type="tree",
                    volume="quota_common_10",
                    disk_limit="5",
                    disk_used="0",
                    files_used="",
                    file_limit="",
                ),
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
                "QUOTA-10.user": Qtree(
                    quota="QUOTA-10",
                    quota_users="user",
                    quota_type="tree",
                    volume="quota_common_10",
                    disk_limit="6",
                    disk_used="0",
                    files_used="",
                    file_limit="",
                ),
                "quota_common_10/QUOTA-10.user": Qtree(
                    quota="QUOTA-10",
                    quota_users="user",
                    quota_type="tree",
                    volume="quota_common_10",
                    disk_limit="6",
                    disk_used="0",
                    files_used="",
                    file_limit="",
                ),
            },
            id="qtree_with_quota_users",
        ),
        pytest.param(
            [
                [
                    "quota QUOTA-10",
                    "quota-type tree",
                    "disk-limit 5",
                    "volume quota_common_10",
                    "disk-used 0",
                ],
                [
                    "quota QUOTA-10",
                    "quota-type tree",
                    "disk-limit 5",
                    "volume quota_common_11",
                    "disk-used 0",
                ],
            ],
            {
                "quota_common_10/QUOTA-10": Qtree(
                    quota="QUOTA-10",
                    quota_users="",
                    quota_type="tree",
                    volume="quota_common_10",
                    disk_limit="5",
                    disk_used="0",
                    files_used="",
                    file_limit="",
                ),
                "QUOTA-10": Qtree(
                    quota="QUOTA-10",
                    quota_users="",
                    quota_type="tree",
                    volume="quota_common_11",
                    disk_limit="5",
                    disk_used="0",
                    files_used="",
                    file_limit="",
                ),
                "quota_common_11/QUOTA-10": Qtree(
                    quota="QUOTA-10",
                    quota_users="",
                    quota_type="tree",
                    volume="quota_common_11",
                    disk_limit="5",
                    disk_used="0",
                    files_used="",
                    file_limit="",
                ),
            },
            id="qtrees_with_same_quota",
        ),
    ],
)
def test_parse_netapp_api_qtree_quota(
    fix_register: FixRegister,
    string_table: Sequence[Sequence[str]],
    expected_parsed: Mapping[str, Qtree],
) -> None:
    section_plugin = fix_register.agent_sections[SectionName("netapp_api_qtree_quota")]
    result = section_plugin.parse_function(string_table)
    assert result == expected_parsed


@pytest.mark.parametrize(
    "parsed, params, expected_discovery",
    [
        pytest.param(
            {
                "QUOTA-10.user": Qtree(
                    quota="QUOTA-10",
                    quota_users="user",
                    quota_type="tree",
                    volume="quota_common_10",
                    disk_limit="6",
                    disk_used="0",
                    files_used="",
                    file_limit="",
                ),
                "quota_common_10/QUOTA-10.user": Qtree(
                    quota="QUOTA-10",
                    quota_users="user",
                    quota_type="tree",
                    volume="quota_common_10",
                    disk_limit="6",
                    disk_used="0",
                    files_used="",
                    file_limit="",
                ),
            },
            {"exclude_volume": False},
            [Service(item="quota_common_10/QUOTA-10.user")],
            id="qtree_with_volume",
        ),
        pytest.param(
            {
                "QUOTA-10.user": Qtree(
                    quota="QUOTA-10",
                    quota_users="user",
                    quota_type="tree",
                    volume="quota_common_10",
                    disk_limit="6",
                    disk_used="0",
                    files_used="",
                    file_limit="",
                ),
                "quota_common_10/QUOTA-10.user": Qtree(
                    quota="QUOTA-10",
                    quota_users="user",
                    quota_type="tree",
                    volume="quota_common_10",
                    disk_limit="6",
                    disk_used="0",
                    files_used="",
                    file_limit="",
                ),
            },
            {"exclude_volume": True},
            [Service(item="QUOTA-10.user")],
            id="qtree_without_volume",
        ),
    ],
)
def test_inventory_netapp_api_qtree_quota(
    fix_register: FixRegister,
    parsed: Mapping[str, Qtree],
    params: Mapping[str, bool],
    expected_discovery: Sequence[Service],
) -> None:
    check_plugin = fix_register.check_plugins[CheckPluginName("netapp_api_qtree_quota")]
    result = list(check_plugin.discovery_function(params, parsed))
    assert result == expected_discovery


@pytest.mark.parametrize(
    "qtree, expected_result",
    [
        pytest.param(
            Qtree(
                quota="QUOTA-10",
                quota_users="user",
                quota_type="tree",
                volume="quota_common_10",
                disk_limit="6",
                disk_used="0",
                files_used="",
                file_limit="",
            ),
            ("QUOTA-10.user", "quota_common_10/QUOTA-10.user"),
            id="qtree_items",
        )
    ],
)
def test_get_item_names(qtree: Qtree, expected_result):
    result = get_item_names(qtree)
    assert result == expected_result


@pytest.mark.parametrize(
    "parsed, item, expected_result",
    [
        pytest.param(
            {
                "QUOTA-10.user": Qtree(
                    quota="QUOTA-10",
                    quota_users="user",
                    quota_type="tree",
                    volume="quota_common_10",
                    disk_limit="6",
                    disk_used="0",
                    files_used="",
                    file_limit="",
                ),
            },
            "QUOTA-10.user",
            [
                Metric(
                    "fs_used", 0.0, levels=(0.0046875, 0.0052734375), boundaries=(0.0, 0.005859375)
                ),
                Metric("fs_size", 0.005859375, boundaries=(0.0, None)),
                Metric("fs_used_percent", 0.0, levels=(80.0, 90.0), boundaries=(0.0, 100.0)),
                Result(state=State.OK, summary="0% used (0 B of 6.00 KiB)"),
                Metric("growth", 0.0),
                Result(state=State.OK, summary="trend per 1 day 0 hours: +0 B"),
                Result(state=State.OK, summary="trend per 1 day 0 hours: +0%"),
                Metric("trend", 0.0, boundaries=(0.0, 0.000244140625)),
            ],
            id="qtree_without_inodes",
        ),
        pytest.param(
            {
                "QUOTA-10.user": Qtree(
                    quota="QUOTA-10",
                    quota_users="user",
                    quota_type="tree",
                    volume="quota_common_10",
                    disk_limit="",
                    disk_used="0",
                    files_used="",
                    file_limit="",
                ),
            },
            "QUOTA-10.user",
            [
                Result(state=State.UNKNOWN, summary="Qtree has no disk limit set"),
            ],
            id="qtree_no_disk_limit",
        ),
        pytest.param(
            {
                "QUOTA-10.user": Qtree(
                    quota="QUOTA-10",
                    quota_users="user",
                    quota_type="tree",
                    volume="quota_common_10",
                    disk_limit="6",
                    disk_used="0",
                    files_used="99",
                    file_limit="100",
                ),
            },
            "QUOTA-10.user",
            [
                Metric(
                    "fs_used", 0.0, levels=(0.0046875, 0.0052734375), boundaries=(0.0, 0.005859375)
                ),
                Metric("fs_size", 0.005859375, boundaries=(0.0, None)),
                Metric("fs_used_percent", 0.0, levels=(80.0, 90.0), boundaries=(0.0, 100.0)),
                Result(state=State.OK, summary="0% used (0 B of 6.00 KiB)"),
                Metric("growth", 0.0),
                Result(state=State.OK, summary="trend per 1 day 0 hours: +0 B"),
                Result(state=State.OK, summary="trend per 1 day 0 hours: +0%"),
                Metric("trend", 0.0, boundaries=(0.0, 0.000244140625)),
                Metric("inodes_used", 99.0, boundaries=(0.0, 100.0)),
                Result(state=State.OK, summary="Inodes used: 99, Inodes available: 1 (1.00%)"),
            ],
            id="qtree_with_inodes",
        ),
        pytest.param(
            {
                "QUOTA-10.user": Qtree(
                    quota="QUOTA-10",
                    quota_users="user",
                    quota_type="tree",
                    volume="quota_common_10",
                    disk_limit="6",
                    disk_used="0",
                    files_used="99",
                    file_limit="100",
                ),
            },
            "QUOTA-10",
            [],
            id="qtree_not_exists",
        ),
    ],
)
def test_check_netapp_api_qtree_quota(
    fix_register: FixRegister,
    value_store_patch: None,
    parsed: Mapping[str, Qtree],
    item: str,
    expected_result: Sequence[CheckResult],
) -> None:
    check_plugin = fix_register.check_plugins[CheckPluginName("netapp_api_qtree_quota")]
    result = list(check_plugin.check_function(item=item, params={}, section=parsed))
    assert result == expected_result
