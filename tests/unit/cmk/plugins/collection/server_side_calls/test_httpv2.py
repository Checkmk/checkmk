#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.plugins.collection.server_side_calls.httpv2 import active_check_httpv2
from cmk.server_side_calls.v1 import ActiveCheckCommand, HostConfig, IPv4Config


def test_active_check_httpv2_minimal() -> None:
    assert list(
        active_check_httpv2(
            {
                "endpoints": [
                    {
                        "service_name": {"prefix": "auto", "name": "My service name"},
                        "url": "https://subomain.domain.tld:123",
                    }
                ],
                "standard_settings": {},
            },
            HostConfig(
                name="testhost",
                ipv4_config=IPv4Config(address="1.2.3.4"),
            ),
        )
    ) == [
        ActiveCheckCommand(
            service_description="HTTPS My service name",
            command_arguments=["--url", "https://subomain.domain.tld:123"],
        ),
    ]


def test_active_check_httpv2_cert_validity_individually() -> None:
    assert list(
        active_check_httpv2(
            {
                "endpoints": [
                    {
                        "service_name": {"prefix": "auto", "name": "My service name"},
                        "url": "https://subomain.domain.tld:123",
                        "individual_settings": {
                            "cert": ("validate", ("fixed", (3456000.0, 1728000.0)))
                        },
                    },
                ],
                "standard_settings": {},
            },
            HostConfig(
                name="testhost",
                ipv4_config=IPv4Config(address="1.2.3.4"),
            ),
        )
    ) == [
        ActiveCheckCommand(
            service_description="HTTPS My service name",
            command_arguments=[
                "--url",
                "https://subomain.domain.tld:123",
                "--certificate-levels",
                "40,20",
            ],
        ),
    ]


def test_active_check_httpv2_cert_validity_globally() -> None:
    assert list(
        active_check_httpv2(
            {
                "endpoints": [
                    {
                        "service_name": {"prefix": "auto", "name": "My service name"},
                        "url": "https://subomain.domain.tld:123",
                        "individual_settings": {
                            "cert": ("validate", ("fixed", (345600.0, 172800.0)))
                        },
                    },
                    {
                        "service_name": {
                            "prefix": "auto",
                            "name": "My other service name",
                        },
                        "url": "https://subomain.domain.tld:123",
                    },
                ],
                "standard_settings": {"cert": ("validate", ("fixed", (3456000.0, 1728000.0)))},
            },
            HostConfig(
                name="testhost",
                ipv4_config=IPv4Config(address="1.2.3.4"),
            ),
        )
    ) == [
        ActiveCheckCommand(
            service_description="HTTPS My service name",
            command_arguments=[
                "--url",
                "https://subomain.domain.tld:123",
                "--certificate-levels",
                "4,2",
            ],
        ),
        ActiveCheckCommand(
            service_description="HTTPS My other service name",
            command_arguments=[
                "--url",
                "https://subomain.domain.tld:123",
                "--certificate-levels",
                "40,20",
            ],
        ),
    ]


def test_active_check_httpv2_options_dont_merge() -> None:
    # individual settings are not merged with the global ones.
    assert list(
        active_check_httpv2(
            {
                "endpoints": [
                    {
                        "individual_settings": {
                            "content": {"body": ("string", "Needle")},
                        },
                        "service_name": {
                            "name": "service",
                            "prefix": "auto",
                        },
                        "url": "https://haystack.huge",
                    },
                ],
                "standard_settings": {
                    "cert": ("validate", ("fixed", (3456000.0, 1728000.0))),
                },
            },
            HostConfig(
                name="testhost",
                ipv4_config=IPv4Config(address="1.2.3.4"),
            ),
        )
    ) == [
        ActiveCheckCommand(
            service_description="HTTPS service",
            command_arguments=[
                "--url",
                "https://haystack.huge",
                "--certificate-levels",
                "40,20",
                "--body-string",
                "Needle",
            ],
        ),
    ]
