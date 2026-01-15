#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

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


@pytest.mark.parametrize(
    "entered_url,host_address,expected_url",
    [
        (
            "https://$HOST_ADDRESS$.domain.tld:123",
            "1.2.3.4",
            "https://1.2.3.4.domain.tld:123",
        ),
        (
            "https://$HOST_ADDRESS$.domain.tld:123",
            "2001:db8:3333:4444:5555:6666:7777:8888",
            "https://[2001:db8:3333:4444:5555:6666:7777:8888].domain.tld:123",
        ),
        (
            "https://[2001:db8:3333:4444:5555:6666:7777:8888].domain.tld:123",
            "_",
            "https://[2001:db8:3333:4444:5555:6666:7777:8888].domain.tld:123",
        ),
        (
            "https://2001:db8:3333:4444:5555:6666:7777:8888.domain.tld:123",
            "_",
            "https://[2001:db8:3333:4444:5555:6666:7777:8888].domain.tld:123",
        ),
    ],
    ids=[
        "ipv4_with_macro",
        "ipv6_with_macro_add_brackets",
        "ipv6_url_with_brackets",
        "ipv6_url_without_brackets",
    ],
)
def test_active_check_httpv2_ipv6_macro(
    entered_url: str,
    host_address: str,
    expected_url: str,
) -> None:
    active_check = list(
        active_check_httpv2(
            {
                "endpoints": [
                    {
                        "service_name": {"prefix": "auto", "name": "My service name"},
                        "url": entered_url,
                    }
                ],
                "standard_settings": {},
            },
            HostConfig(
                name="testhost",
                macros={"$HOST_ADDRESS$": host_address},
            ),
        )
    )

    assert active_check == [
        ActiveCheckCommand(
            service_description="HTTPS My service name",
            command_arguments=["--url", expected_url],
        ),
    ]


def test_active_check_httpv2_macros_in_body_fixed_string() -> None:
    assert list(
        active_check_httpv2(
            {
                "endpoints": [
                    {
                        "service_name": {"prefix": "auto", "name": "My service"},
                        "url": "https://checkmk.com",
                    }
                ],
                "standard_settings": {"content": {"body": ("string", "$HOSTNAME$")}},
            },
            HostConfig(
                name="testhost",
                ipv4_config=IPv4Config(address="1.2.3.4"),
                macros={"$HOSTNAME$": "testhost"},
            ),
        )
    ) == [
        ActiveCheckCommand(
            service_description="HTTPS My service",
            command_arguments=["--url", "https://checkmk.com", "--body-string", "testhost"],
        ),
    ]
