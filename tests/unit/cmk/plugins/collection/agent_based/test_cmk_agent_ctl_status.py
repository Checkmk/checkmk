#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime

import pytest

from cmk.agent_based.v2 import StringTable
from cmk.plugins.collection.agent_based.cmk_agent_ctl_status import parse_cmk_agent_ctl_status
from cmk.plugins.lib.checkmk import (
    CertInfoController,
    Connection,
    ControllerSection,
    LocalConnectionStatus,
)


@pytest.mark.parametrize(
    [
        "string_table",
        "expected_parse_result",
    ],
    [
        pytest.param(
            [
                [
                    """{"version":"2.1.0-2023.01.24","agent_socket_operational":true,"ip_allowlist":[],"allow_legacy_pull":false,"connections":[{"coordinates":"localhost:8001/heute","uuid":"44d137be-179c-4879-9fd1-1dbb295db0e2","local":{"connection_mode":"pull-agent","cert_info":{"issuer":"Site 'heute' local CA","from":"Tue, 24 Jan 2023 15:20:54 +0000","to":"Mon, 24 Jan 2028 15:20:54 +0000"}},"remote":{"connection_mode":"pull-agent","registration_state":null,"host_name":"heute"}},{"coordinates":"localhost:8000/stable","uuid":"8c3a0bcc-ad63-4003-ac1f-bff9a5bb5fff","local":{"connection_mode":"pull-agent","cert_info":{"issuer":"Site 'stable' local CA","from":"Tue, 24 Jan 2023 15:20:40 +0000","to":"Sun, 27 May 3021 15:20:40 +0000"}},"remote":{"connection_mode":"pull-agent","registration_state":null,"host_name":"stable"}}]}"""
                ]
            ],
            ControllerSection(
                allow_legacy_pull=False,
                agent_socket_operational=True,
                ip_allowlist=[],
                connections=[
                    Connection(
                        site_id=None,
                        coordinates="localhost:8001/heute",
                        local=LocalConnectionStatus(
                            cert_info=CertInfoController(
                                to=datetime.datetime(2028, 1, 24, 15, 20, 54, tzinfo=datetime.UTC),
                                issuer="Site 'heute' local CA",
                            )
                        ),
                    ),
                    Connection(
                        site_id=None,
                        coordinates="localhost:8000/stable",
                        local=LocalConnectionStatus(
                            cert_info=CertInfoController(
                                to=datetime.datetime(3021, 5, 27, 15, 20, 40, tzinfo=datetime.UTC),
                                issuer="Site 'stable' local CA",
                            )
                        ),
                    ),
                ],
            ),
            id="legacy data (2.1)",
        ),
        pytest.param(
            [
                [
                    """{"version":"2023.01.24","agent_socket_operational":true,"ip_allowlist":[],"allow_legacy_pull":false,"connections":[{"site_id":"localhost/heute","receiver_port":8001,"uuid":"44d137be-179c-4879-9fd1-1dbb295db0e2","local":{"connection_mode":"pull-agent","cert_info":{"issuer":"Site \'heute\' local CA","from":"Tue, 24 Jan 2023 15:20:54 +0000","to":"Mon, 24 Jan 2028 15:20:54 +0000"}},"remote":"remote_query_disabled"},{"site_id":"localhost/stable","receiver_port":8000,"uuid":"8c3a0bcc-ad63-4003-ac1f-bff9a5bb5fff","local":{"connection_mode":"pull-agent","cert_info":{"issuer":"Site \'stable\' local CA","from":"Tue, 24 Jan 2023 15:20:40 +0000","to":"Sun, 27 May 3021 15:20:40 +0000"}},"remote":"remote_query_disabled"}]}"""
                ]
            ],
            ControllerSection(
                allow_legacy_pull=False,
                agent_socket_operational=True,
                ip_allowlist=[],
                connections=[
                    Connection(
                        site_id="localhost/heute",
                        coordinates=None,
                        local=LocalConnectionStatus(
                            cert_info=CertInfoController(
                                to=datetime.datetime(2028, 1, 24, 15, 20, 54, tzinfo=datetime.UTC),
                                issuer="Site 'heute' local CA",
                            )
                        ),
                    ),
                    Connection(
                        site_id="localhost/stable",
                        coordinates=None,
                        local=LocalConnectionStatus(
                            cert_info=CertInfoController(
                                to=datetime.datetime(3021, 5, 27, 15, 20, 40, tzinfo=datetime.UTC),
                                issuer="Site 'stable' local CA",
                            )
                        ),
                    ),
                ],
            ),
            id="up to date",
        ),
        pytest.param(
            [
                [
                    """{"version":"2023.01.24","agent_socket_operational":true,"ip_allowlist":[],"allow_legacy_pull":false,"connections":[{"uuid":"bc834538-64f1-4231-9cfa-0dcd3899f780","local":{"connection_mode":"pull-agent","cert_info":{"issuer":"Site 'heute' local CA","from":"Tue, 24 Jan 2023 16:55:14 +0000","to":"Mon, 24 Jan 2028 16:55:14 +0000"}},"remote":"imported_connection"}]}"""
                ]
            ],
            ControllerSection(
                allow_legacy_pull=False,
                agent_socket_operational=True,
                ip_allowlist=[],
                connections=[
                    Connection(
                        site_id=None,
                        coordinates=None,
                        local=LocalConnectionStatus(
                            cert_info=CertInfoController(
                                to=datetime.datetime(2028, 1, 24, 16, 55, 14, tzinfo=datetime.UTC),
                                issuer="Site 'heute' local CA",
                            )
                        ),
                    )
                ],
            ),
            id="imported connection",
        ),
    ],
)
def test_parse_cmk_agent_ctl_status(
    string_table: StringTable,
    expected_parse_result: ControllerSection,
) -> None:
    assert parse_cmk_agent_ctl_status(string_table) == expected_parse_result
