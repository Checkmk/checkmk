#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.plugins.collection.server_side_calls.cert import (
    CertEndpoint,
    CertificateDetails,
    ConnectionType,
    generate_cert_services,
    Issuer,
    parse_cert_params,
    ServiceDescription,
    ServicePrefix,
    Settings,
    Subject,
)
from cmk.server_side_calls.v1 import ActiveCheckCommand, EnvProxy, HostConfig, IPv4Config, NoProxy

HOST_CONFIG = HostConfig(
    name="testhost",
    ipv4_config=IPv4Config(address="0.0.0.1"),
)


def test_env_proxy() -> None:
    result = list(
        generate_cert_services(
            [
                CertEndpoint(
                    service_name=ServiceDescription(prefix=ServicePrefix.AUTO, name="my_service"),
                    address="abc.xyz",
                    port=443,
                    individual_settings=Settings(proxy=EnvProxy()),
                )
            ],
            HOST_CONFIG,
        )
    )
    assert result == [
        ActiveCheckCommand(
            service_description="CERT my_service",
            command_arguments=["--hostname", "abc.xyz", "--port", "443"],
        )
    ]


def test_no_proxy() -> None:
    result = list(
        generate_cert_services(
            [
                CertEndpoint(
                    service_name=ServiceDescription(prefix=ServicePrefix.AUTO, name="my_service"),
                    address="abc.xyz",
                    port=443,
                    individual_settings=Settings(proxy=NoProxy()),
                )
            ],
            HOST_CONFIG,
        )
    )
    assert result == [
        ActiveCheckCommand(
            service_description="CERT my_service",
            command_arguments=["--hostname", "abc.xyz", "--port", "443", "--ignore-proxy-env"],
        )
    ]


@pytest.mark.parametrize("connection_type", list(ConnectionType))
def test_connection_type_reaches_command_line(connection_type: ConnectionType) -> None:
    # Every connection type (e.g. IMAP/LDAP STARTTLS) must be passed to
    # check_cert via --connection-type.
    result = list(
        generate_cert_services(
            [
                CertEndpoint(
                    service_name=ServiceDescription(prefix=ServicePrefix.AUTO, name="my_service"),
                    address="abc.xyz",
                    port=443,
                    individual_settings=Settings(connection=connection_type),
                )
            ],
            HOST_CONFIG,
        )
    )
    assert result == [
        ActiveCheckCommand(
            service_description="CERT my_service",
            command_arguments=[
                "--hostname",
                "abc.xyz",
                "--port",
                "443",
                "--connection-type",
                connection_type.value,
            ],
        )
    ]


def test_parse_ldap_starttls_connection_type() -> None:
    # The raw params mirror what the "Check certificates" ruleset produces
    # for "Connection type: LDAP STARTTLS" (CMK-32024).
    endpoints = parse_cert_params(
        {
            "connections": [
                {
                    "service_name": {"prefix": "auto", "name": "my_service"},
                    "address": "abc.xyz",
                    "port": 389,
                    "individual_settings": {"connection": "ldap_starttls"},
                }
            ],
            "standard_settings": {"port": 443},
        }
    )
    assert len(endpoints) == 1
    assert endpoints[0].port == 389
    assert endpoints[0].individual_settings is not None
    assert endpoints[0].individual_settings.connection is ConnectionType.LDAP_STARTTLS


def test_generate_cert_services() -> None:
    assert list(
        generate_cert_services(
            [
                CertEndpoint(
                    service_name=ServiceDescription(prefix=ServicePrefix.AUTO, name="my_service"),
                    address="abc.xyz",
                    individual_settings=Settings(
                        cert_details=CertificateDetails(
                            issuer=Issuer(common_name="issuer"),
                            subject=Subject(common_name="subject"),
                        )
                    ),
                )
            ],
            HOST_CONFIG,
        )
    ) == [
        ActiveCheckCommand(
            service_description="CERT my_service",
            command_arguments=[
                "--hostname",
                "abc.xyz",
                "--issuer-cn",
                "issuer",
                "--subject-cn",
                "subject",
            ],
        )
    ]
