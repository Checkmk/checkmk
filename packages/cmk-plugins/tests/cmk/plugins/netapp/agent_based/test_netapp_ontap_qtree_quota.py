#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from unittest.mock import patch

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.plugins.lib.df import FILESYSTEM_DEFAULT_PARAMS
from cmk.plugins.netapp.agent_based.lib import Qtree
from cmk.plugins.netapp.agent_based.netapp_ontap_qtree_quota import (
    check_netapp_ontap_qtree_quota,
    discover_netapp_ontap_qtree_quota,
    parse_netapp_ontap_qtree_quota,
    Section,
)


@pytest.mark.parametrize(
    "input_string_table, expected_section",
    [
        pytest.param(
            [
                [
                    '{"hard_limit": 26388279066624,"name": "","type_": "tree","used_total": 0,"users": [""],"volume": "bs_data"}'
                ]
            ],
            {
                "": Qtree(
                    quota="",
                    quota_users="",
                    volume="bs_data",
                    disk_limit="26388279066624",
                    disk_used="0",
                    files_used="",
                    file_limit="",
                ),
                "bs_data/": Qtree(
                    quota="",
                    quota_users="",
                    volume="bs_data",
                    disk_limit="26388279066624",
                    disk_used="0",
                    files_used="",
                    file_limit="",
                ),
            },
            id="qtree without name",
        ),
        pytest.param(
            [
                [
                    '{"hard_limit": null,"name": "vr_data","type_": "user","used_total": 1252536320,"users": ["S-1-5-21-1156737867-681972312-1097073633-359373"],"volume": "bs_data"}'
                ],
                [
                    '{"hard_limit": null,"name": "vr_data","type_": "user","used_total": 0,"users": ["*"],"volume": "bs_data"}'
                ],
            ],
            {
                "bs_data/vr_data": Qtree(
                    quota="vr_data",
                    quota_users="*",
                    volume="bs_data",
                    disk_limit="",
                    disk_used="0",
                    files_used="",
                    file_limit="",
                ),
                "vr_data": Qtree(
                    quota="vr_data",
                    quota_users="*",
                    volume="bs_data",
                    disk_limit="",
                    disk_used="0",
                    files_used="",
                    file_limit="",
                ),
            },
            id="qtree without disk limit",
        ),
        pytest.param(
            [
                [
                    '{"hard_limit": 26388279066624,"name": "vr_data","type_": "tree","used_total": 26127656828928,"users": [""],"volume": "bs_data"}'
                ],
                [
                    '{"hard_limit": 2199023255552,"name": "tools","type_": "tree","used_total": 929024028672,"users": ["user1", "user2"],"volume": "bs_group"}'
                ],
            ],
            {
                "bs_group/tools": Qtree(
                    quota="tools",
                    quota_users="user1,user2",
                    volume="bs_group",
                    disk_limit="2199023255552",
                    disk_used="929024028672",
                    files_used="",
                    file_limit="",
                ),
                "bs_data/vr_data": Qtree(
                    quota="vr_data",
                    quota_users="",
                    volume="bs_data",
                    disk_limit="26388279066624",
                    disk_used="26127656828928",
                    files_used="",
                    file_limit="",
                ),
                "tools": Qtree(
                    quota="tools",
                    quota_users="user1,user2",
                    volume="bs_group",
                    disk_limit="2199023255552",
                    disk_used="929024028672",
                    files_used="",
                    file_limit="",
                ),
                "vr_data": Qtree(
                    quota="vr_data",
                    quota_users="",
                    volume="bs_data",
                    disk_limit="26388279066624",
                    disk_used="26127656828928",
                    files_used="",
                    file_limit="",
                ),
            },
            id="qtree normal",
        ),
    ],
)
def test_parse_netapp_ontap_qtree_quota(
    input_string_table: StringTable, expected_section: Section
) -> None:
    result = parse_netapp_ontap_qtree_quota(input_string_table)

    assert result == expected_section


_QTREE_SECTION: Section = {
    "vol1/qt1": Qtree(
        quota="qt1",
        quota_users="",
        volume="vol1",
        disk_limit="107374182400",
        disk_used="10737418240",
    ),
    "qt1": Qtree(
        quota="qt1",
        quota_users="",
        volume="vol1",
        disk_limit="107374182400",
        disk_used="10737418240",
    ),
}

_S3_SECTION: Section = {
    "fg_oss_1/bucket-1": Qtree(
        quota="bucket-1",
        quota_users="",
        volume="fg_oss_1",
        disk_limit="107374182400",
        disk_used="96636764160",
    ),
    "bucket-1": Qtree(
        quota="bucket-1",
        quota_users="",
        volume="fg_oss_1",
        disk_limit="107374182400",
        disk_used="96636764160",
    ),
}


def test_discover_merges_qtree_and_s3_sections() -> None:
    services = list(
        discover_netapp_ontap_qtree_quota({"exclude_volume": False}, _QTREE_SECTION, _S3_SECTION)
    )
    assert services == [Service(item="vol1/qt1"), Service(item="fg_oss_1/bucket-1")]


def test_discover_with_only_the_s3_section() -> None:
    services = list(discover_netapp_ontap_qtree_quota({"exclude_volume": False}, None, _S3_SECTION))
    assert services == [Service(item="fg_oss_1/bucket-1")]


def test_check_s3_bucket_through_qtree_plugin() -> None:
    with patch(
        "cmk.plugins.netapp.agent_based.netapp_ontap_qtree_quota.get_value_store",
        return_value={
            "fg_oss_1/bucket-1.delta": (1000.0, 100.0),
            "fg_oss_1/bucket-1.trend": (1000.0 - 86400, 1000.0, 0.0),
        },
    ):
        results = list(
            check_netapp_ontap_qtree_quota(
                "fg_oss_1/bucket-1", FILESYSTEM_DEFAULT_PARAMS, None, _S3_SECTION
            )
        )

    assert any(isinstance(r, Metric) and r.name == "fs_used_percent" for r in results)
    assert any(isinstance(r, Result) and r.state is State.CRIT for r in results)
