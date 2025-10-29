#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import StringTable
from cmk.plugins.netapp.agent_based.lib import Qtree
from cmk.plugins.netapp.agent_based.netapp_ontap_qtree_quota import (
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
