#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.plugins.collection.server_side_calls.httpv2 import (
    LevelsType,
    parse_http_params,
    TlsVersion,
)
from cmk.server_side_calls_backend.config_processing import process_configuration_to_parameters
from cmk.update_config.http.main import _classify, _migratable, _migrate, HostType, V1Value

EXAMPLE_1 = {
    "name": "My web page",
    "host": {"address": ("direct", "open-one.de")},
    "mode": (
        "url",
        {
            "ssl": "ssl_1_2",
            "response_time": (100.0, 200.0),
        },
    ),
}

EXAMPLE_2 = {
    "name": "Simple example 2",
    "host": {"address": ("direct", "checkmk.com"), "port": 443},
    "mode": (
        "url",
        {
            "uri": "/werks",
            "ssl": "auto",
            "response_time": ("fixed", (0.1, 0.2)),
            "timeout": 10.0,
            "user_agent": "my-user-agent/1.20.3",
            "add_headers": [],
            "onredirect": "follow",
            "method": "GET",
            "page_size": {"minimum": 42, "maximum": 73},
            "max_age": 86400.0,
        },
    ),
}

EXAMPLE_3: Mapping[str, object] = {
    "name": "service_name",
    "host": {},
    "mode": ("url", {}),
}

EXAMPLE_4 = {
    "name": "check_cert",
    "host": {},
    "mode": ("cert", {"cert_days": ("fixed", (0.0, 0.0))}),
}

EXAMPLE_5: Mapping[str, object] = {
    "name": "any_network",
    "host": {"address_family": "any"},
    "mode": ("url", {}),
}

EXAMPLE_6: Mapping[str, object] = {
    "name": "enforcev4",
    "host": {"address_family": "ipv4_enforced"},
    "mode": ("url", {}),
}

EXAMPLE_7: Mapping[str, object] = {
    "name": "enforcev6",
    "host": {"address_family": "ipv6_enforced"},
    "mode": ("url", {}),
}

EXAMPLE_8: Mapping[str, object] = {
    "name": "primary_address_family",
    "host": {"address_family": "primary_enforced"},
    "mode": ("url", {}),
}

EXAMPLE_9: Mapping[str, object] = {
    "name": "tcp_port",
    "host": {"port": 443},
    "mode": ("url", {}),
}

EXAMPLE_10: Mapping[str, object] = {
    "name": "two_addresses",
    "host": {"address": ("direct", "google.com"), "virthost": "facebook.de"},
    "mode": ("url", {}),
}

EXAMPLE_11: Mapping[str, object] = {
    "name": "virthost_only",
    "host": {"virthost": "facebook.de"},
    "mode": ("url", {}),
}

EXAMPLE_12: Mapping[str, object] = {
    # cert mode will ignore the address field
    "name": "cert_mode",
    "host": {"address": ("direct", "google.com")},
    "mode": ("cert", {"cert_days": ("fixed", (0.0, 0.0))}),
}

EXAMPLE_13: Mapping[str, object] = {
    # proxy will always set a virtual host, even if none is specified
    "name": "proxy_sets_virt",
    "host": {"address": ("proxy", {"address": "duckduckgo.com"})},
    "mode": ("url", {}),
}

EXAMPLE_14: Mapping[str, object] = {
    # proxy settings will pass the port multiple times to check_http
    "name": "proxy_specifies_port",
    "host": {"address": ("proxy", {"address": "duckduckgo.com"}), "port": 600},
    "mode": ("url", {}),
}

EXAMPLE_15: Mapping[str, object] = {
    "name": "hostname_only",
    "host": {"address": ("direct", "google.com")},
    "mode": ("url", {}),
}

EXAMPLE_16: Mapping[str, object] = {
    "name": "ipv4_only",
    "host": {"address": ("direct", "127.0.0.1")},
    "mode": ("url", {}),
}

EXAMPLE_17: Mapping[str, object] = {
    "name": "localhost",
    "host": {"address": ("direct", "localhost")},
    "mode": ("url", {}),
}

EXAMPLE_18: Mapping[str, object] = {
    "name": "ipv6_embedded",
    "host": {"address": ("direct", "[::1]")},
    "mode": ("url", {}),
}

EXAMPLE_19: Mapping[str, object] = {
    "name": "port_specified_twice",
    "host": {"address": ("direct", "[::1]:80"), "port": 80},
    "mode": ("url", {}),
}

EXAMPLE_20: Mapping[str, object] = {
    "name": "ipv6",
    "host": {"address": ("direct", "::1")},
    "mode": ("url", {}),
}

EXAMPLE_21: Mapping[str, object] = {
    "name": "ipv6",
    "host": {"address": ("direct", "[::1]")},
    "mode": (
        "url",
        {
            "uri": "/werks",
        },
    ),
}

EXAMPLE_22: Mapping[str, object] = {
    "name": "tls1",
    "host": {"address": ("direct", "[::1]")},
    "mode": ("url", {"ssl": "ssl_1"}),
}

EXAMPLE_23: Mapping[str, object] = {
    "name": "ssl2",
    "host": {"address": ("direct", "[::1]")},
    "mode": ("url", {"ssl": "ssl_2"}),
}

EXAMPLE_24: Mapping[str, object] = {
    "name": "ssl3",
    "host": {"address": ("direct", "[::1]")},
    "mode": ("url", {"ssl": "ssl_3"}),
}

EXAMPLE_25: Mapping[str, object] = {
    "name": "tls_1_2",
    "host": {"address": ("direct", "[::1]")},
    "mode": ("url", {"ssl": "ssl_1_2"}),
}

EXAMPLE_26: Mapping[str, object] = {
    "name": "tls_1_3",
    "host": {"address": ("direct", "google.com")},
    "mode": ("url", {"ssl": "ssl_1_3"}),
}


EXAMPLE_27: Mapping[str, object] = {
    "name": "tls_auto_negotiation",
    "host": {"address": ("direct", "[::1]")},
    "mode": ("url", {"ssl": "auto"}),
}

EXAMPLE_28: Mapping[str, object] = {
    "name": "response_time",
    "host": {"address": ("direct", "[::1]")},
    "mode": ("url", {"response_time": (0.0, 0.0)}),
}

EXAMPLE_29: Mapping[str, object] = {
    "name": "timeout",
    "host": {"address": ("direct", "[::1]")},
    "mode": ("url", {"timeout": 10}),
}

EXAMPLE_30: Mapping[str, object] = {
    "name": "timeout",
    "host": {"address": ("direct", "[::1]")},
    "mode": ("url", {"timeout": 0}),
}

EXAMPLE_31: Mapping[str, object] = {
    "name": "user_agent",
    "host": {"address": ("direct", "[::1]")},
    "mode": ("url", {"user_agent": "agent"}),
}

EXAMPLE_32: Mapping[str, object] = {
    "name": "headers",
    "host": {"address": ("direct", "[::1]")},
    "mode": ("url", {"add_headers": ["head: tail", "mop: ", "a: b: c"]}),
}

EXAMPLE_33: Mapping[str, object] = {
    "name": "headers",
    "host": {"address": ("direct", "[::1]")},
    "mode": ("url", {"add_headers": ["mop"]}),
}

EXAMPLE_34: Mapping[str, object] = {
    "name": "headers",
    "host": {"address": ("direct", "[::1]")},
    "mode": ("url", {"add_headers": ["head:tail"]}),
}

EXAMPLE_35: Mapping[str, object] = {
    "name": "headers",
    "host": {"address": ("direct", "[::1]")},
    "mode": ("url", {"add_headers": ["head:"]}),
}

EXAMPLE_36: Mapping[str, object] = {
    "name": "authorization",
    "host": {"address": ("direct", "[::1]")},
    "mode": (
        "url",
        {
            "auth": {
                "user": "user",
                "password": (
                    "cmk_postprocessed",
                    "explicit_password",
                    ("uuid60fd36ba-5de6-4aee-8d92-6cc6fb13bb05", "cmk"),
                ),
            }
        },
    ),
}

EXAMPLE_37: Mapping[str, object] = {
    "name": "authorization",
    "host": {"address": ("direct", "[::1]")},
    "mode": ("url", {"onredirect": "ok"}),
}

EXAMPLE_38: Mapping[str, object] = {
    "name": "authorization",
    "host": {"address": ("direct", "[::1]")},
    "mode": ("url", {"onredirect": "warning"}),
}

EXAMPLE_39: Mapping[str, object] = {
    "name": "authorization",
    "host": {"address": ("direct", "[::1]")},
    "mode": ("url", {"onredirect": "critical"}),
}

EXAMPLE_40: Mapping[str, object] = {
    "name": "authorization",
    "host": {"address": ("direct", "[::1]")},
    "mode": ("url", {"onredirect": "follow"}),
}

EXAMPLE_41: Mapping[str, object] = {
    "name": "authorization",
    "host": {"address": ("direct", "[::1]")},
    "mode": ("url", {"onredirect": "sticky"}),
}

EXAMPLE_42: Mapping[str, object] = {
    "name": "authorization",
    "host": {"address": ("direct", "[::1]")},
    "mode": ("url", {"onredirect": "stickyport"}),
}

EXAMPLE_43: Mapping[str, object] = {
    "name": "authorization",
    "host": {"address": ("direct", "[::1]")},
    "mode": ("url", {"expect_response_header": "yes:no"}),
}


@pytest.mark.parametrize(
    "rule_value",
    [
        EXAMPLE_1,
        EXAMPLE_15,
        EXAMPLE_16,
        EXAMPLE_17,
        EXAMPLE_18,
        EXAMPLE_19,
        EXAMPLE_21,
        EXAMPLE_25,
        EXAMPLE_26,
        EXAMPLE_27,
        EXAMPLE_28,
        EXAMPLE_29,
        EXAMPLE_30,
        EXAMPLE_31,
        EXAMPLE_32,
        EXAMPLE_36,
        EXAMPLE_37,
    ],
)
def test_migrateable_rules(rule_value: Mapping[str, object]) -> None:
    assert _migratable(rule_value)


@pytest.mark.parametrize(
    "rule_value, expected",
    [
        (EXAMPLE_15, "http://google.com"),
        (EXAMPLE_16, "http://127.0.0.1"),
        (EXAMPLE_17, "http://localhost"),
        (EXAMPLE_18, "http://[::1]"),
        (EXAMPLE_19, "http://[::1]:80:80"),  # TODO: This may or may not be acceptable.
        (EXAMPLE_21, "http://[::1]/werks"),
        (EXAMPLE_25, "https://[::1]"),
        (EXAMPLE_26, "https://google.com"),
    ],
)
def test_migrate_url(rule_value: Mapping[str, object], expected: str) -> None:
    # Assemble
    value = V1Value.model_validate(rule_value)
    # Act
    migrated = _migrate(value)
    # Assemble
    ssc_value = parse_http_params(process_configuration_to_parameters(migrated).value)
    # Assert
    assert ssc_value[0].url == expected


@pytest.mark.parametrize(
    "rule_value, expected",
    [
        (EXAMPLE_17, None),
        (EXAMPLE_25, {"min_version": TlsVersion.TLS_1_2, "allow_higher": False}),
        (EXAMPLE_26, {"min_version": TlsVersion.TLS_1_3, "allow_higher": False}),
        (EXAMPLE_27, {"min_version": TlsVersion.AUTO, "allow_higher": True}),
    ],
)
def test_migrate_ssl(rule_value: Mapping[str, object], expected: str) -> None:
    # Assemble
    value = V1Value.model_validate(rule_value)
    # Act
    migrated = _migrate(value)
    # Assemble
    ssc_value = parse_http_params(process_configuration_to_parameters(migrated).value)
    # Assert
    assert ssc_value[0].settings.connection is not None
    assert ssc_value[0].settings.connection.model_dump().get("tls_versions") == expected


@pytest.mark.parametrize(
    "rule_value",
    [
        EXAMPLE_2,
        EXAMPLE_3,
        EXAMPLE_4,
        EXAMPLE_5,
        EXAMPLE_6,
        EXAMPLE_7,
        EXAMPLE_8,
        EXAMPLE_9,
        EXAMPLE_10,
        EXAMPLE_11,
        EXAMPLE_12,
        EXAMPLE_13,
        EXAMPLE_14,
        EXAMPLE_20,
        EXAMPLE_22,
        EXAMPLE_23,
        EXAMPLE_24,
        EXAMPLE_33,
        EXAMPLE_34,
        EXAMPLE_35,
        EXAMPLE_43,
    ],
)
def test_non_migrateable_rules(rule_value: Mapping[str, object]) -> None:
    assert not _migratable(rule_value)


@pytest.mark.parametrize(
    "rule_value, expected",
    [
        (EXAMPLE_1, (LevelsType.FIXED, (0.1, 0.2))),
        (EXAMPLE_27, None),
        (EXAMPLE_28, (LevelsType.FIXED, (0.0, 0.0))),
    ],
)
def test_migrate_response_time(rule_value: Mapping[str, object], expected: object) -> None:
    # Assemble
    value = V1Value.model_validate(rule_value)
    # Act
    migrated = _migrate(value)
    # Assemble
    ssc_value = parse_http_params(process_configuration_to_parameters(migrated).value)
    # Assert
    assert ssc_value[0].settings.response_time == expected


@pytest.mark.parametrize(
    "rule_value, expected",
    [
        (EXAMPLE_27, None),
        (EXAMPLE_29, 10.0),
        (EXAMPLE_30, 0.0),
    ],
)
def test_migrate_timeout(rule_value: Mapping[str, object], expected: object) -> None:
    # Assemble
    value = V1Value.model_validate(rule_value)
    # Act
    migrated = _migrate(value)
    # Assemble
    ssc_value = parse_http_params(process_configuration_to_parameters(migrated).value)
    # Assert
    assert ssc_value[0].settings.connection is not None
    assert ssc_value[0].settings.connection.model_dump()["timeout"] == expected


@pytest.mark.parametrize(
    "rule_value, expected",
    [
        (EXAMPLE_27, None),
        (EXAMPLE_31, "agent"),
    ],
)
def test_migrate_user_agent(rule_value: Mapping[str, object], expected: object) -> None:
    # Assemble
    value = V1Value.model_validate(rule_value)
    # Act
    migrated = _migrate(value)
    # Assemble
    ssc_value = parse_http_params(process_configuration_to_parameters(migrated).value)
    # Assert
    assert ssc_value[0].settings.connection is not None
    assert ssc_value[0].settings.connection.model_dump()["user_agent"] == expected


@pytest.mark.parametrize(
    "rule_value, expected",
    [
        (EXAMPLE_27, None),
        (
            EXAMPLE_32,
            [
                {"header_name": "head", "header_value": "tail"},
                {"header_name": "mop", "header_value": ""},
                {"header_name": "a", "header_value": "b: c"},
            ],
        ),
    ],
)
def test_migrate_add_headers(rule_value: Mapping[str, object], expected: object) -> None:
    # Assemble
    value = V1Value.model_validate(rule_value)
    # Act
    migrated = _migrate(value)
    # Assemble
    ssc_value = parse_http_params(process_configuration_to_parameters(migrated).value)
    # Assert
    assert ssc_value[0].settings.connection is not None
    assert ssc_value[0].settings.connection.model_dump()["add_headers"] == expected


def test_migrate_auth_user() -> None:
    # Assemble
    value = V1Value.model_validate(EXAMPLE_36)
    # Act
    migrated = _migrate(value)
    # Assemble
    ssc_value = parse_http_params(process_configuration_to_parameters(migrated).value)
    # Assert
    assert ssc_value[0].settings.connection is not None
    assert ssc_value[0].settings.connection.auth is not None
    assert ssc_value[0].settings.connection.auth[0].value == "user_auth"


def test_migrate_auth_no_auth() -> None:
    # Assemble
    value = V1Value.model_validate(EXAMPLE_27)
    # Act
    migrated = _migrate(value)
    # Assemble
    ssc_value = parse_http_params(process_configuration_to_parameters(migrated).value)
    # Assert
    assert ssc_value[0].settings.connection is not None
    assert ssc_value[0].settings.connection.auth is None


@pytest.mark.parametrize(
    "rule_value, expected",
    [
        (EXAMPLE_27, None),
        (EXAMPLE_37, "ok"),
        (EXAMPLE_38, "warning"),
        (EXAMPLE_39, "critical"),
        (EXAMPLE_40, "follow"),
        (EXAMPLE_41, "sticky"),
        (EXAMPLE_42, "stickyport"),
    ],
)
def test_migrate_redirect(rule_value: Mapping[str, object], expected: object) -> None:
    # Assemble
    value = V1Value.model_validate(rule_value)
    # Act
    migrated = _migrate(value)
    # Assemble
    ssc_value = parse_http_params(process_configuration_to_parameters(migrated).value)
    # Assert
    assert ssc_value[0].settings.connection is not None
    assert ssc_value[0].settings.connection.model_dump()["redirects"] == expected


@pytest.mark.parametrize(
    "host,type_",
    [
        ("google.com", HostType.EMBEDDABLE),
        ("localhost", HostType.EMBEDDABLE),
        ("127.0.0.1", HostType.EMBEDDABLE),
        ("::1", HostType.IPV6),
        ("[::1]", HostType.EMBEDDABLE),
        ("::1127.0.0.1", HostType.INVALID),
    ],
)
def test_classify(host: str, type_: HostType) -> None:
    assert _classify(host) == type_
