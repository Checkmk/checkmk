#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.plugins.collection.server_side_calls.cert import (
    CertEndpoint,
    CertificateDetails,
    generate_cert_services,
    Issuer,
    ServiceDescription,
    ServicePrefix,
    Settings,
    Subject,
)
from cmk.server_side_calls.v1 import ActiveCheckCommand, HostConfig, IPv4Config


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
            HostConfig(
                name="testhost",
                ipv4_config=IPv4Config(address="0.0.0.1"),
            ),
        )
    ) == [
        ActiveCheckCommand(
            service_description="CERT my_service",
            command_arguments=[
                "--url",
                "abc.xyz",
                "--issuer-cn",
                "issuer",
                "--subject-cn",
                "subject",
            ],
        )
    ]
