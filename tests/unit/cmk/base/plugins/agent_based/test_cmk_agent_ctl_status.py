#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from tests.testlib import on_time

from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import StringTable
from cmk.base.plugins.agent_based.cmk_agent_ctl_status import parse_cmk_agent_ctl_status
from cmk.base.plugins.agent_based.utils.checkmk import Connection, ControllerSection


@pytest.mark.parametrize(
    [
        "string_table",
        "expected_parse_result",
    ],
    [
        pytest.param(
            [
                [
                    '{"version":"2022.10.26","agent_socket_operational":true,"ip_allowlist":[],"allow_legacy_pull":false,"connections":[]}'
                ]
            ],
            ControllerSection(
                allow_legacy_pull=False,
                socket_ready=True,
                ip_allowlist=(),
                connections=[],
            ),
            id="No connections available",
        ),
        pytest.param(
            [
                [
                    '{"version":"2022.10.26","agent_socket_operational":true,"ip_allowlist":[],"allow_legacy_pull":false,"connections":[{"site_id":"localhost/heute","receiver_port":8001,"uuid":"846cd637-64e8-415c-9c57-568ab4488ad1","local":{"connection_type":"pull-agent","cert_info":{"issuer":"Site \'heute\' local CA","from":"Fri, 16 Dec 2022 14:50:40 +0000","to":"Wed, 18 Apr 3021 14:50:40 +0000"}},"remote":"remote_query_disabled"}]}'
                ]
            ],
            ControllerSection(
                allow_legacy_pull=False,
                socket_ready=True,
                ip_allowlist=(),
                connections=[
                    Connection(site_id="localhost/heute", valid_for_seconds=31529866158.49604)
                ],
            ),
            id="One connection available",
        ),
        pytest.param(
            [
                [
                    '{"version":"2022.10.26","agent_socket_operational":true,"ip_allowlist":[],"allow_legacy_pull":false,"connections":[{"site_id":"localhost/heute","receiver_port":8001,"uuid":"846cd637-64e8-415c-9c57-568ab4488ad1","local":{"connection_type":"pull-agent","cert_info":{"issuer":"Site \'heute\' local CA","from":"Fri, 16 Dec 2022 14:50:40 +0000","to":"Wed, 18 Apr 3021 14:50:40 +0000"}},"remote":"remote_query_disabled"}, {"site_id":"localhost/stable","receiver_port":8001,"uuid":"846cd637-64e8-415c-9c57-568ab4488ad1","local":{"connection_type":"pull-agent","cert_info":{"issuer":"Site \'stable\' local CA","from":"Fri, 16 Dec 2022 14:50:40 +0000","to":"Wed, 18 Apr 3023 14:50:40 +0000"}},"remote":"remote_query_disabled"}]}'
                ]
            ],
            ControllerSection(
                allow_legacy_pull=False,
                socket_ready=True,
                ip_allowlist=(),
                connections=[
                    Connection(site_id="localhost/heute", valid_for_seconds=31529866158.49604),
                    Connection(site_id="localhost/stable", valid_for_seconds=31592938158.49604),
                ],
            ),
            id="Multiple connections available",
        ),
    ],
)
def test_parse_cmk_agent_ctl_status(
    string_table: StringTable,
    expected_parse_result: ControllerSection,
) -> None:
    with on_time(1645800081.5039608, "UTC"):
        assert parse_cmk_agent_ctl_status(string_table) == expected_parse_result
