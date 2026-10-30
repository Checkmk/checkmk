#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime

import pytest
from pydantic import ValidationError

from cmk.agent_based.v2 import StringTable
from cmk.plugins.checkmk.agent_based.cmk_agent_ctl_status import parse_cmk_agent_ctl_status
from cmk.plugins.checkmk.agent_based.lib import (
    CertInfo,
    CertInfoController,
    CMKAgentUpdateSection,
    Connection,
    ControllerSection,
    LocalConnectionStatus,
    TrustedCa,
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
        pytest.param(
            [
                [
                    """{"version":"2026.08.03","agent_socket_operational":true,"ip_allowlist":[],"allow_legacy_pull":false,"connections":[{"site_id":"localhost/heute","receiver_port":8001,"uuid":"44d137be-179c-4879-9fd1-1dbb295db0e2","local":{"connection_mode":"pull-agent","cert_info":{"issuer":"Site 'heute' local CA","from":"Tue, 24 Jan 2023 15:20:54 +0000","to":"Mon, 24 Jan 2028 15:20:54 +0000"},"trusted_cas":[{"common_name":"Site 'heute' local CA","fingerprint":"AB:CD:EF","from":"Tue, 24 Jan 2023 15:20:54 +0000","to":"Mon, 24 Jan 2028 15:20:54 +0000"}]},"remote":"remote_query_disabled"}]}"""
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
                            ),
                            trusted_cas=[
                                TrustedCa(
                                    common_name="Site 'heute' local CA",
                                    fingerprint="AB:CD:EF",
                                )
                            ],
                        ),
                    ),
                ],
            ),
            id="trusted CAs",
        ),
    ],
)
def test_parse_cmk_agent_ctl_status(
    string_table: StringTable,
    expected_parse_result: ControllerSection,
) -> None:
    assert parse_cmk_agent_ctl_status(string_table) == expected_parse_result


def test_parse_cmk_agent_ctl_status_unparsable_trusted_ca() -> None:
    """The controller reports CAs it could not parse as a plain error string."""
    with pytest.raises(ValidationError):
        parse_cmk_agent_ctl_status(
            [
                [
                    """{"version":"2026.08.03","agent_socket_operational":true,"ip_allowlist":[],"allow_legacy_pull":false,"connections":[{"site_id":"localhost/heute","receiver_port":8001,"uuid":"44d137be-179c-4879-9fd1-1dbb295db0e2","local":{"connection_mode":"pull-agent","cert_info":{"issuer":"Site 'heute' local CA","from":"Tue, 24 Jan 2023 15:20:54 +0000","to":"Mon, 24 Jan 2028 15:20:54 +0000"},"trusted_cas":[{"common_name":"Site 'heute' local CA","fingerprint":"AB:CD:EF","from":"Tue, 24 Jan 2023 15:20:54 +0000","to":"Mon, 24 Jan 2028 15:20:54 +0000"},"parsing_error"]},"remote":"remote_query_disabled"}]}"""
                ]
            ]
        )


def test_parse_the_agent_updates_of_the_integrated_updater() -> None:
    """CMK-39594 AC1"""
    section = parse_cmk_agent_ctl_status(
        [
            [
                """{"version":"2026.10.30","agent_socket_operational":true,"ip_allowlist":[],"allow_legacy_pull":false,"connections":[],"agent_updates":{"last_check":1793358000,"last_update":null,"aghash":"0123456789abcdef","pending_hash":null,"update_url":"https://server:8000/site","trusted_certs":{"0":{"corrupt":false,"not_after":"20310101000000Z","signature_algorithm":"ecdsa-with-SHA256","common_name":"Signing key"},"1":{"corrupt":true,"not_after":null,"signature_algorithm":null,"common_name":null}},"error":null}}"""
            ]
        ]
    )

    assert section is not None
    assert section.agent_updates == CMKAgentUpdateSection(
        last_check=1793358000,
        aghash="0123456789abcdef",
        update_url="https://server:8000/site",
        trusted_certs={
            0: CertInfo(
                corrupt=False,
                not_after=datetime.datetime(2031, 1, 1, tzinfo=datetime.UTC),
                signature_algorithm="ecdsa-with-SHA256",
                common_name="Signing key",
            ),
            1: CertInfo(corrupt=True),
        },
    )
