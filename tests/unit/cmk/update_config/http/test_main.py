#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.plugins.collection.server_side_calls.httpv2 import (
    AddressFamily,
    BodyRegex,
    CertificateValidity,
    Document,
    DocumentBodyOption,
    HeaderSpec,
    HttpMethod,
    LevelsType,
    MatchType,
    PageSize,
    parse_http_params,
    SendData,
    SendDataInner,
    SendDataType,
    ServerResponse,
    ServiceDescription,
    ServicePrefix,
    TlsVersion,
)
from cmk.server_side_calls_backend.config_processing import process_configuration_to_parameters
from cmk.update_config.http.main import (
    _classify,
    _migratable,
    _migrate,
    _migrate_expect_response,
    HostType,
    V1Value,
)

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

EXAMPLE_44: Mapping[str, object] = {
    "name": "authorization",
    "host": {"address": ("direct", "[::1]")},
    "mode": ("url", {"expect_response": ["no"]}),
}

EXAMPLE_45: Mapping[str, object] = {
    "name": "authorization",
    "host": {"address": ("direct", "[::1]")},
    "mode": ("url", {"expect_response": []}),
}

EXAMPLE_46: Mapping[str, object] = {
    "name": "expect_string",
    "host": {"address": ("direct", "[::1]")},
    "mode": ("url", {"expect_string": "example"}),
}

EXAMPLE_47: Mapping[str, object] = {
    "name": "regex",
    "host": {"address": ("direct", "[::1]")},
    "mode": (
        "url",
        {
            "expect_regex": {
                "regex": "example",
                "case_insensitive": True,
                "crit_if_found": True,
                "multiline": True,
            }
        },
    ),
}

EXAMPLE_48: Mapping[str, object] = {
    "name": "regex",
    "host": {"address": ("direct", "[::1]")},
    "mode": (
        "url",
        {
            "expect_regex": {
                "regex": "",
                "case_insensitive": False,
                "crit_if_found": False,
                "multiline": False,
            }
        },
    ),
}

EXAMPLE_49: Mapping[str, object] = {
    "name": "regex",
    "host": {"address": ("direct", "[::1]")},
    "mode": (
        "url",
        {
            "expect_string": "example",
            "expect_regex": {
                "regex": "example",
                "case_insensitive": True,
                "crit_if_found": True,
                "multiline": True,
            },
        },
    ),
}

EXAMPLE_50: Mapping[str, object] = {
    "name": "post_data",
    "host": {"address": ("direct", "[::1]")},
    "mode": (
        "url",
        {
            "post_data": {"data": "da", "content_type": "text/html"},
        },
    ),
}

EXAMPLE_51: Mapping[str, object] = {
    "name": "post_data",
    "host": {"address": ("direct", "[::1]")},
    "mode": (
        "url",
        {
            "method": "GET",
            "post_data": {"data": "da", "content_type": "text/html"},
        },
    ),
}

EXAMPLE_52: Mapping[str, object] = {
    "name": "post_data",
    "host": {"address": ("direct", "[::1]")},
    "mode": (
        "url",
        {
            "method": "POST",
            "post_data": {"data": "da", "content_type": "video"},
        },
    ),
}

EXAMPLE_53: Mapping[str, object] = {
    "name": "post_data",
    "host": {"address": ("direct", "[::1]")},
    "mode": (
        "url",
        {
            "method": "PUT",
            "post_data": {"data": "", "content_type": "gif"},
        },
    ),
}

EXAMPLE_54: Mapping[str, object] = {
    "name": "method",
    "host": {"address": ("direct", "[::1]")},
    "mode": ("url", {"method": "GET"}),
}

EXAMPLE_55: Mapping[str, object] = {
    "name": "method",
    "host": {"address": ("direct", "[::1]")},
    "mode": ("url", {"method": "DELETE"}),
}

EXAMPLE_56: Mapping[str, object] = {
    "name": "method",
    "host": {"address": ("direct", "[::1]")},
    "mode": ("url", {"method": "HEAD"}),
}

EXAMPLE_57: Mapping[str, object] = {
    "name": "method",
    "host": {"address": ("direct", "[::1]")},
    "mode": ("url", {"method": "PUT"}),
}

EXAMPLE_58: Mapping[str, object] = {
    "name": "method",
    "host": {"address": ("direct", "[::1]")},
    "mode": ("url", {"method": "POST"}),
}

EXAMPLE_59: Mapping[str, object] = {
    "name": "method",
    "host": {"address": ("direct", "[::1]")},
    "mode": ("url", {"method": "OPTIONS"}),
}

EXAMPLE_60: Mapping[str, object] = {
    "name": "method",
    "host": {"address": ("direct", "[::1]")},
    "mode": ("url", {"method": "TRACE"}),
}

EXAMPLE_61: Mapping[str, object] = {
    "name": "method",
    "host": {"address": ("direct", "[::1]")},
    "mode": ("url", {"method": "CONNECT"}),
}

EXAMPLE_62: Mapping[str, object] = {
    "name": "method",
    "host": {"address": ("direct", "[::1]")},
    "mode": ("url", {"method": "CONNECT_POST"}),
}

EXAMPLE_63: Mapping[str, object] = {
    "name": "method",
    "host": {"address": ("direct", "[::1]")},
    "mode": ("url", {"method": "PROP_FIND"}),
}


EXAMPLE_64: Mapping[str, object] = {
    "name": "no_body",
    "host": {"address": ("direct", "[::1]")},
    "mode": ("url", {"no_body": True}),
}


EXAMPLE_65: Mapping[str, object] = {
    "name": "page_size",
    "host": {"address": ("direct", "[::1]")},
    "mode": ("url", {"page_size": {"minimum": 42, "maximum": 0}}),
}


EXAMPLE_66: Mapping[str, object] = {
    "name": "max_age",
    "host": {"address": ("direct", "[::1]")},
    "mode": ("url", {"max_age": 111}),
}

EXAMPLE_67: Mapping[str, object] = {
    "name": "max_age",
    "host": {"address": ("direct", "[::1]")},
    "mode": (
        "url",
        {
            "no_body": True,
            "max_age": 111,
        },
    ),
}

EXAMPLE_68: Mapping[str, object] = {
    "name": "max_age",
    "host": {"address": ("direct", "[::1]")},
    "mode": (
        "url",
        {
            "urlize": True,
            "extended_perfdata": True,
        },
    ),
}

EXAMPLE_69: Mapping[str, object] = {
    "name": "cert_fixed",
    "host": {"address": ("direct", "[::1]")},
    "mode": ("cert", {"cert_days": ("fixed", (0.0, 0.0))}),
}

EXAMPLE_70: Mapping[str, object] = {
    "name": "cert_no_levels",
    "host": {"address": ("direct", "[::1]")},
    "mode": ("cert", {"cert_days": ("no_levels", None)}),
}

EXAMPLE_71: Mapping[str, object] = {
    "name": "headers",
    "host": {"address": ("direct", "[::1]")},
    "mode": ("url", {"add_headers": [":tail"]}),
}

EXAMPLE_72: Mapping[str, object] = {
    "name": "headers",
    "host": {"address": ("direct", "[::1]")},
    "mode": ("url", {"add_headers": ["head:  tail  "]}),
}

EXAMPLE_73: Mapping[str, object] = {
    "name": "expect_response_header",
    "host": {"address": ("direct", "[::1]")},
    "mode": ("url", {"expect_response_header": "\r\nyes:no\r\n"}),
}

EXAMPLE_74: Mapping[str, object] = {
    "name": "expect_response_header",
    "host": {"address": ("direct", "[::1]")},
    "mode": ("url", {"expect_response_header": "a:b\r\nyes:no"}),
}

EXAMPLE_75: Mapping[str, object] = {
    "name": "cert_no_levels",
    "host": {"address": ("direct", "[::1]")},
    "mode": ("cert", {"cert_days": ("no_levels", None)}),
    "disable_sni": True,
}

EXAMPLE_76: Mapping[str, object] = {
    "name": "name",
    "host": {"address": ("direct", "[::1]")},
    "mode": ("url", {}),
}

EXAMPLE_77: Mapping[str, object] = {
    "name": "^name",
    "host": {"address": ("direct", "[::1]")},
    "mode": ("url", {}),
}

EXAMPLE_78: Mapping[str, object] = {
    "name": "name",
    "host": {"address": ("direct", "[::1]")},
    "mode": ("cert", {"cert_days": ("no_levels", None)}),
}

EXAMPLE_79: Mapping[str, object] = {
    "name": "name",
    "host": {"address": ("direct", "[::1]")},
    "mode": ("url", {"ssl": "ssl_1_3"}),
}

EXAMPLE_80: Mapping[str, object] = {
    "name": "address_family",
    "host": {
        "address": ("direct", "[::1]"),
        "address_family": "any",
    },
    "mode": ("url", {}),
}

EXAMPLE_81: Mapping[str, object] = {
    "name": "address_family",
    "host": {
        "address": ("direct", "[::1]"),
        "address_family": "ipv4_enforced",
    },
    "mode": ("url", {}),
}

EXAMPLE_82: Mapping[str, object] = {
    "name": "address_family",
    "host": {
        "address": ("direct", "[::1]"),
        "address_family": "primary_enforced",
    },
    "mode": ("url", {}),
}

EXAMPLE_83: Mapping[str, object] = {
    "name": "address_family",
    "host": {
        "address": ("direct", "[::1]"),
        "address_family": "ipv6_enforced",
    },
    "mode": ("url", {}),
}


@pytest.mark.parametrize(
    "rule_value",
    [
        EXAMPLE_1,
        EXAMPLE_12,
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
        EXAMPLE_34,
        EXAMPLE_35,
        EXAMPLE_36,
        EXAMPLE_37,
        EXAMPLE_43,
        EXAMPLE_45,
        EXAMPLE_46,
        EXAMPLE_47,
        EXAMPLE_48,
        EXAMPLE_50,
        EXAMPLE_52,
        EXAMPLE_53,
        EXAMPLE_54,
        EXAMPLE_55,
        EXAMPLE_56,
        EXAMPLE_57,
        EXAMPLE_58,
        EXAMPLE_64,
        EXAMPLE_65,
        EXAMPLE_66,
        EXAMPLE_67,
        EXAMPLE_68,
        EXAMPLE_69,
        EXAMPLE_70,
        EXAMPLE_71,
        EXAMPLE_72,
        EXAMPLE_76,
        EXAMPLE_77,
        EXAMPLE_78,
        EXAMPLE_79,
        EXAMPLE_80,
        EXAMPLE_81,
        EXAMPLE_82,
        EXAMPLE_83,
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
        (
            EXAMPLE_27,
            Document(
                document_body=DocumentBodyOption.FETCH,
                max_age=None,
                page_size=None,
            ),
        ),
        (
            EXAMPLE_64,
            Document(
                document_body=DocumentBodyOption.IGNORE,
                max_age=None,
                page_size=None,
            ),
        ),
        (
            EXAMPLE_65,
            Document(
                document_body=DocumentBodyOption.FETCH,
                max_age=None,
                page_size=PageSize(min=42, max=0),
            ),
        ),
        (
            EXAMPLE_66,
            Document(
                document_body=DocumentBodyOption.FETCH,
                max_age=111.0,
                page_size=None,
            ),
        ),
        (
            EXAMPLE_67,
            Document(
                document_body=DocumentBodyOption.IGNORE,
                max_age=111.0,
                page_size=None,
            ),
        ),
    ],
)
def test_migrate_document(rule_value: Mapping[str, object], expected: object) -> None:
    # Assemble
    value = V1Value.model_validate(rule_value)
    # Act
    migrated = _migrate(value)
    # Assemble
    ssc_value = parse_http_params(process_configuration_to_parameters(migrated).value)
    # Assert
    assert ssc_value[0].settings.document == expected


@pytest.mark.parametrize(
    "rule_value, expected",
    [
        (
            EXAMPLE_27,
            (HttpMethod.GET, None),
        ),
        (
            EXAMPLE_50,
            (
                HttpMethod.POST,
                SendData(
                    send_data=SendDataInner(
                        content="da",
                        content_type=(SendDataType.CUSTOM, "text/html"),
                    )
                ),
            ),
        ),
        (
            EXAMPLE_52,
            (
                HttpMethod.POST,
                SendData(
                    send_data=SendDataInner(
                        content="da",
                        content_type=(SendDataType.CUSTOM, "video"),
                    )
                ),
            ),
        ),
        (
            EXAMPLE_53,
            (
                HttpMethod.PUT,
                SendData(
                    send_data=SendDataInner(
                        content="",
                        content_type=(SendDataType.CUSTOM, "gif"),
                    )
                ),
            ),
        ),
        (
            EXAMPLE_54,
            (HttpMethod.GET, None),
        ),
        (
            EXAMPLE_55,
            (HttpMethod.DELETE, None),
        ),
        (
            EXAMPLE_56,
            (HttpMethod.HEAD, None),
        ),
        (
            EXAMPLE_57,
            (HttpMethod.PUT, SendData(send_data=None)),
        ),
        (
            EXAMPLE_58,
            (HttpMethod.POST, SendData(send_data=None)),
        ),
    ],
)
def test_migrate_method(rule_value: Mapping[str, object], expected: object) -> None:
    # Assemble
    value = V1Value.model_validate(rule_value)
    # Act
    migrated = _migrate(value)
    # Assemble
    ssc_value = parse_http_params(process_configuration_to_parameters(migrated).value)
    # Assert
    assert ssc_value[0].settings.connection is not None
    assert ssc_value[0].settings.connection.method == expected


@pytest.mark.parametrize(
    "rule_value, expected",
    [
        (EXAMPLE_27, None),
        (
            EXAMPLE_47,
            (
                MatchType.REGEX,
                BodyRegex(regex="example", case_insensitive=True, multiline=True, invert=True),
            ),
        ),
        (
            EXAMPLE_48,
            (
                MatchType.REGEX,
                BodyRegex(regex="", case_insensitive=False, multiline=False, invert=False),
            ),
        ),
    ],
)
def test_migrate_expect_regex(rule_value: Mapping[str, object], expected: object) -> None:
    # Assemble
    value = V1Value.model_validate(rule_value)
    # Act
    migrated = _migrate(value)
    # Assemble
    ssc_value = parse_http_params(process_configuration_to_parameters(migrated).value)
    # Assert
    assert ssc_value[0].settings.content is not None
    assert ssc_value[0].settings.content.body == expected


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
        EXAMPLE_13,
        EXAMPLE_14,
        EXAMPLE_20,
        EXAMPLE_22,
        EXAMPLE_23,
        EXAMPLE_24,
        EXAMPLE_33,
        EXAMPLE_44,
        EXAMPLE_49,
        EXAMPLE_51,
        EXAMPLE_59,
        EXAMPLE_60,
        EXAMPLE_61,
        EXAMPLE_62,
        EXAMPLE_63,
        EXAMPLE_74,
        EXAMPLE_75,
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
        (EXAMPLE_46, (MatchType.STRING, "example")),
    ],
)
def test_migrate_expect_string(rule_value: Mapping[str, object], expected: object) -> None:
    # Assemble
    value = V1Value.model_validate(rule_value)
    # Act
    migrated = _migrate(value)
    # Assemble
    ssc_value = parse_http_params(process_configuration_to_parameters(migrated).value)
    # Assert
    assert ssc_value[0].settings.content is not None
    assert ssc_value[0].settings.content.body == expected


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
        (
            EXAMPLE_34,
            [{"header_name": "head", "header_value": "tail"}],
        ),
        (
            EXAMPLE_35,
            [{"header_name": "head", "header_value": ""}],
        ),
        (
            EXAMPLE_71,
            [{"header_name": "", "header_value": "tail"}],
        ),
        (
            EXAMPLE_72,
            [{"header_name": "head", "header_value": "tail"}],
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


def test_helper_migrate_expect_response() -> None:
    assert _migrate_expect_response(["HTTP/1.1 200 OK", "302 REDIRECT", "404"]) == [200, 302, 404]


@pytest.mark.parametrize(
    "rule_value, expected",
    [
        (EXAMPLE_27, None),
        (EXAMPLE_45, ServerResponse(expected=[])),
    ],
)
def test_migrate_expect_response(rule_value: Mapping[str, object], expected: object) -> None:
    # Assemble
    value = V1Value.model_validate(rule_value)
    # Act
    migrated = _migrate(value)
    # Assemble
    ssc_value = parse_http_params(process_configuration_to_parameters(migrated).value)
    # Assert
    assert ssc_value[0].settings.server_response == expected


@pytest.mark.parametrize(
    "rule_value, expected",
    [
        (EXAMPLE_69, (CertificateValidity.VALIDATE, (LevelsType.FIXED, (0.0, 0.0)))),
        (EXAMPLE_70, (CertificateValidity.VALIDATE, (LevelsType.NO_LEVELS, None))),
    ],
)
def test_migrate_cert(rule_value: Mapping[str, object], expected: object) -> None:
    # Assemble
    value = V1Value.model_validate(rule_value)
    # Act
    migrated = _migrate(value)
    # Assemble
    ssc_value = parse_http_params(process_configuration_to_parameters(migrated).value)
    # Assert
    assert ssc_value[0].settings.cert == expected


@pytest.mark.parametrize(
    "rule_value, expected",
    [
        (EXAMPLE_27, None),
        (EXAMPLE_43, (MatchType.STRING, HeaderSpec(header_name="yes", header_value="no"))),
        (EXAMPLE_73, (MatchType.STRING, HeaderSpec(header_name="yes", header_value="no"))),
    ],
)
def test_migrate_expect_response_header(rule_value: Mapping[str, object], expected: object) -> None:
    # Assemble
    value = V1Value.model_validate(rule_value)
    # Act
    migrated = _migrate(value)
    # Assemble
    ssc_value = parse_http_params(process_configuration_to_parameters(migrated).value)
    # Assert
    assert ssc_value[0].settings.content is not None
    assert ssc_value[0].settings.content.header == expected


@pytest.mark.parametrize(
    "rule_value, expected",
    [
        (EXAMPLE_76, ServiceDescription(prefix=ServicePrefix.AUTO, name="name")),
        (EXAMPLE_77, ServiceDescription(prefix=ServicePrefix.NONE, name="name")),
        (EXAMPLE_78, ServiceDescription(prefix=ServicePrefix.AUTO, name="name")),
        (EXAMPLE_79, ServiceDescription(prefix=ServicePrefix.AUTO, name="name")),
    ],
)
def test_migrate_name(rule_value: Mapping[str, object], expected: object) -> None:
    # Assemble
    value = V1Value.model_validate(rule_value)
    # Act
    migrated = _migrate(value)
    # Assemble
    ssc_value = parse_http_params(process_configuration_to_parameters(migrated).value)
    # Assert
    assert ssc_value[0].service_name == expected


@pytest.mark.parametrize(
    "rule_value, expected",
    [
        (EXAMPLE_27, AddressFamily.ANY),
        (EXAMPLE_80, AddressFamily.ANY),
        (EXAMPLE_81, AddressFamily.IPV4),
        (EXAMPLE_82, AddressFamily.PRIMARY),
        (EXAMPLE_83, AddressFamily.IPV6),
    ],
)
def test_migrate_address_family(rule_value: Mapping[str, object], expected: object) -> None:
    # Assemble
    value = V1Value.model_validate(rule_value)
    # Act
    migrated = _migrate(value)
    # Assemble
    ssc_value = parse_http_params(process_configuration_to_parameters(migrated).value)
    # Assert
    assert ssc_value[0].settings.connection is not None
    assert ssc_value[0].settings.connection.address_family == expected
