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
from cmk.update_config.https.conflict_options import (
    AdditionalHeaders,
    CantConstructURL,
    CantDisableSNIWithHTTPS,
    CantHaveRegexAndString,
    CantPostData,
    Config,
    ConflictType,
    ExpectResponseHeader,
    HTTP10NotSupported,
    MethodUnavailable,
    OnlyStatusCodesAllowed,
    SSLIncompatible,
    V1ChecksRedirectResponse,
)
from cmk.update_config.https.conflicts import _migrate_expect_response, Conflict, detect_conflicts
from cmk.update_config.https.migrate import migrate

DEFAULT = Config()

HOST_1 = {"address": ("direct", "[::1]"), "virthost": "[::1]"}

EXAMPLE_1 = {
    "name": "My web page",
    "host": {"address": ("direct", "open-one.de")},
    "mode": (
        "url",
        {
            "ssl": "ssl_1_2",
            "response_time": ("fixed", (0.1, 0.2)),
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
    "host": {"address": ("direct", "google.com"), "virthost": "google.com"},
    "mode": ("url", {}),
}

EXAMPLE_16: Mapping[str, object] = {
    "name": "ipv4_only",
    "host": {"address": ("direct", "127.0.0.1"), "virthost": "127.0.0.1"},
    "mode": ("url", {}),
}

EXAMPLE_17: Mapping[str, object] = {
    "name": "localhost",
    "host": {"address": ("direct", "localhost"), "virthost": "localhost"},
    "mode": ("url", {}),
}

EXAMPLE_18: Mapping[str, object] = {
    "name": "ipv6_embedded",
    "host": HOST_1,
    "mode": ("url", {}),
}

EXAMPLE_19: Mapping[str, object] = {
    "name": "port_specified_twice",
    "host": {"address": ("direct", "[::1]:80"), "virthost": "[::1]:80", "port": 80},
    "mode": ("url", {}),
}

EXAMPLE_20: Mapping[str, object] = {
    "name": "ipv6",
    "host": {"address": ("direct", "::1"), "virthost": "[::1]"},
    "mode": ("url", {}),
}

EXAMPLE_21: Mapping[str, object] = {
    "name": "ipv6",
    "host": HOST_1,
    "mode": (
        "url",
        {
            "uri": "/werks",
        },
    ),
}

EXAMPLE_22: Mapping[str, object] = {
    "name": "tls_1_0",
    "host": HOST_1,
    "mode": ("url", {"ssl": "ssl_1"}),
}

EXAMPLE_23: Mapping[str, object] = {
    "name": "ssl2",
    "host": HOST_1,
    "mode": ("url", {"ssl": "ssl_2"}),
}

EXAMPLE_24: Mapping[str, object] = {
    "name": "ssl3",
    "host": HOST_1,
    "mode": ("url", {"ssl": "ssl_3"}),
}

EXAMPLE_25: Mapping[str, object] = {
    "name": "tls_1_2",
    "host": HOST_1,
    "mode": ("url", {"ssl": "ssl_1_2"}),
}

EXAMPLE_26: Mapping[str, object] = {
    "name": "tls_1_2",
    "host": {"address": ("direct", "google.com")},
    "mode": ("url", {"ssl": "ssl_1_2"}),
}


EXAMPLE_27: Mapping[str, object] = {
    "name": "tls_auto_negotiation",
    "host": HOST_1,
    "mode": ("url", {"ssl": "auto"}),
}

EXAMPLE_28: Mapping[str, object] = {
    "name": "response_time",
    "host": HOST_1,
    "mode": ("url", {"response_time": ("fixed", (0.0, 0.0))}),
}

EXAMPLE_29: Mapping[str, object] = {
    "name": "timeout",
    "host": HOST_1,
    "mode": ("url", {"timeout": 10}),
}

EXAMPLE_30: Mapping[str, object] = {
    "name": "timeout",
    "host": HOST_1,
    "mode": ("url", {"timeout": 0}),
}

EXAMPLE_31: Mapping[str, object] = {
    "name": "user_agent",
    "host": HOST_1,
    "mode": ("url", {"user_agent": "agent"}),
}

EXAMPLE_32: Mapping[str, object] = {
    "name": "headers",
    "host": HOST_1,
    "mode": ("url", {"add_headers": ["head: tail", "mop: ", "a: b: c"]}),
}

EXAMPLE_33: Mapping[str, object] = {
    "name": "headers",
    "host": HOST_1,
    "mode": ("url", {"add_headers": ["head: tail", "mop"]}),
}

EXAMPLE_34: Mapping[str, object] = {
    "name": "headers",
    "host": HOST_1,
    "mode": ("url", {"add_headers": ["head:tail"]}),
}

EXAMPLE_35: Mapping[str, object] = {
    "name": "headers",
    "host": HOST_1,
    "mode": ("url", {"add_headers": ["head:"]}),
}

EXAMPLE_36: Mapping[str, object] = {
    "name": "authorization",
    "host": HOST_1,
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
    "host": HOST_1,
    "mode": ("url", {"onredirect": "ok"}),
}

EXAMPLE_38: Mapping[str, object] = {
    "name": "authorization",
    "host": HOST_1,
    "mode": ("url", {"onredirect": "warning"}),
}

EXAMPLE_39: Mapping[str, object] = {
    "name": "authorization",
    "host": HOST_1,
    "mode": ("url", {"onredirect": "critical"}),
}

EXAMPLE_40: Mapping[str, object] = {
    "name": "authorization",
    "host": HOST_1,
    "mode": ("url", {"onredirect": "follow"}),
}

EXAMPLE_41: Mapping[str, object] = {
    "name": "authorization",
    "host": HOST_1,
    "mode": ("url", {"onredirect": "sticky"}),
}

EXAMPLE_42: Mapping[str, object] = {
    "name": "authorization",
    "host": HOST_1,
    "mode": ("url", {"onredirect": "stickyport"}),
}

EXAMPLE_43: Mapping[str, object] = {
    "name": "authorization",
    "host": HOST_1,
    "mode": ("url", {"expect_response_header": "yes:no"}),
}

EXAMPLE_44: Mapping[str, object] = {
    "name": "authorization",
    "host": HOST_1,
    "mode": ("url", {"expect_response": ["no"]}),
}

EXAMPLE_45: Mapping[str, object] = {
    "name": "authorization",
    "host": HOST_1,
    "mode": ("url", {"expect_response": []}),
}

EXAMPLE_46: Mapping[str, object] = {
    "name": "expect_string",
    "host": HOST_1,
    "mode": ("url", {"expect_string": "example"}),
}

EXAMPLE_47: Mapping[str, object] = {
    "name": "regex",
    "host": HOST_1,
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
    "host": HOST_1,
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
    "host": HOST_1,
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
    "host": HOST_1,
    "mode": (
        "url",
        {
            "post_data": {"data": "da", "content_type": "text/html"},
        },
    ),
}

EXAMPLE_51: Mapping[str, object] = {
    "name": "post_data",
    "host": HOST_1,
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
    "host": HOST_1,
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
    "host": HOST_1,
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
    "host": HOST_1,
    "mode": ("url", {"method": "GET"}),
}

EXAMPLE_55: Mapping[str, object] = {
    "name": "method",
    "host": HOST_1,
    "mode": ("url", {"method": "DELETE"}),
}

EXAMPLE_56: Mapping[str, object] = {
    "name": "method",
    "host": HOST_1,
    "mode": ("url", {"method": "HEAD"}),
}

EXAMPLE_57: Mapping[str, object] = {
    "name": "method",
    "host": HOST_1,
    "mode": ("url", {"method": "PUT"}),
}

EXAMPLE_58: Mapping[str, object] = {
    "name": "method",
    "host": HOST_1,
    "mode": ("url", {"method": "POST"}),
}

EXAMPLE_59: Mapping[str, object] = {
    "name": "method",
    "host": HOST_1,
    "mode": ("url", {"method": "OPTIONS"}),
}

EXAMPLE_60: Mapping[str, object] = {
    "name": "method",
    "host": HOST_1,
    "mode": ("url", {"method": "TRACE"}),
}

EXAMPLE_61: Mapping[str, object] = {
    "name": "method",
    "host": HOST_1,
    "mode": ("url", {"method": "CONNECT"}),
}

EXAMPLE_62: Mapping[str, object] = {
    "name": "method",
    "host": HOST_1,
    "mode": ("url", {"method": "CONNECT_POST"}),
}

EXAMPLE_63: Mapping[str, object] = {
    "name": "method",
    "host": HOST_1,
    "mode": ("url", {"method": "PROPFIND"}),
}


EXAMPLE_64: Mapping[str, object] = {
    "name": "no_body",
    "host": HOST_1,
    "mode": ("url", {"no_body": True}),
}


EXAMPLE_65: Mapping[str, object] = {
    "name": "page_size",
    "host": HOST_1,
    "mode": ("url", {"page_size": {"minimum": 42, "maximum": 0}}),
}


EXAMPLE_66: Mapping[str, object] = {
    "name": "max_age",
    "host": HOST_1,
    "mode": ("url", {"max_age": 111}),
}

EXAMPLE_67: Mapping[str, object] = {
    "name": "max_age",
    "host": HOST_1,
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
    "host": HOST_1,
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
    "host": HOST_1,
    "mode": ("cert", {"cert_days": ("fixed", (0.0, 0.0))}),
}

EXAMPLE_70: Mapping[str, object] = {
    "name": "cert_no_levels",
    "host": HOST_1,
    "mode": ("cert", {"cert_days": ("no_levels", None)}),
}

EXAMPLE_71: Mapping[str, object] = {
    "name": "headers",
    "host": HOST_1,
    "mode": ("url", {"add_headers": [":tail"]}),
}

EXAMPLE_72: Mapping[str, object] = {
    "name": "headers",
    "host": HOST_1,
    "mode": ("url", {"add_headers": ["head:  tail  "]}),
}

EXAMPLE_73: Mapping[str, object] = {
    "name": "expect_response_header",
    "host": HOST_1,
    "mode": ("url", {"expect_response_header": "\r\nyes:no\r\n"}),
}

EXAMPLE_74: Mapping[str, object] = {
    "name": "expect_response_header",
    "host": HOST_1,
    "mode": ("url", {"expect_response_header": "a:b\r\nyes:no"}),
}

EXAMPLE_75: Mapping[str, object] = {
    "name": "cert_no_levels",
    "host": HOST_1,
    "mode": ("cert", {"cert_days": ("no_levels", None)}),
    "disable_sni": True,
}

EXAMPLE_76: Mapping[str, object] = {
    "name": "name",
    "host": HOST_1,
    "mode": ("url", {}),
}

EXAMPLE_77: Mapping[str, object] = {
    "name": "^name",
    "host": HOST_1,
    "mode": ("url", {}),
}

EXAMPLE_78: Mapping[str, object] = {
    "name": "name",
    "host": HOST_1,
    "mode": ("cert", {"cert_days": ("no_levels", None)}),
}

EXAMPLE_79: Mapping[str, object] = {
    "name": "name",
    "host": HOST_1,
    "mode": ("url", {"ssl": "ssl_1_2"}),
}

EXAMPLE_80: Mapping[str, object] = {
    "name": "address_family",
    "host": {
        **HOST_1,
        "address_family": "any",
    },
    "mode": ("url", {}),
}

EXAMPLE_81: Mapping[str, object] = {
    "name": "address_family",
    "host": {
        **HOST_1,
        "address_family": "ipv4_enforced",
    },
    "mode": ("url", {}),
}

EXAMPLE_82: Mapping[str, object] = {
    "name": "address_family",
    "host": {
        **HOST_1,
        "address_family": "primary_enforced",
    },
    "mode": ("url", {}),
}

EXAMPLE_83: Mapping[str, object] = {
    "name": "address_family",
    "host": {
        **HOST_1,
        "address_family": "ipv6_enforced",
    },
    "mode": ("url", {}),
}

EXAMPLE_84: Mapping[str, object] = {
    "name": "response_time",
    "host": HOST_1,
    "mode": ("url", {"response_time": ("no_levels", None)}),
}

EXAMPLE_85: Mapping[str, object] = {
    "name": "response_time",
    "host": {
        "address": (
            "proxy",
            {
                "address": "http://localhost",
                "port": 8081,
                "auth": {
                    "user": "user",
                    "password": (
                        "cmk_postprocessed",
                        "explicit_password",
                        ("uuid91b27eb6-f561-468c-b929-cef0491e71d8", "cmk"),
                    ),
                },
            },
        )
    },
    "mode": ("url", {}),
}

EXAMPLE_86: Mapping[str, object] = {
    "name": "response_time",
    "host": {
        "address": (
            "proxy",
            {
                "address": "http://localhost",
                "port": 8081,
            },
        )
    },
    "mode": ("url", {}),
}

EXAMPLE_87: Mapping[str, object] = {
    "name": "response_time",
    "host": {
        "address": (
            "proxy",
            {
                "address": "http://localhost",
            },
        )
    },
    "mode": ("url", {}),
}

EXAMPLE_88: Mapping[str, object] = {
    "name": "expect_response_header",
    "host": HOST_1,
    "mode": ("url", {"expect_response_header": "a"}),
}

EXAMPLE_89: Mapping[str, object] = {
    "name": "disable_sni",
    "host": HOST_1,
    "mode": ("url", {"ssl": "ssl_1_2"}),
    "disable_sni": True,
}

EXAMPLE_90: Mapping[str, object] = {}

EXAMPLE_91: Mapping[str, object] = {
    "name": "authorization",
    "host": HOST_1,
    "mode": (
        "url",
        {
            "expect_response": ["302"],
            "onredirect": "stickyport",
        },
    ),
}

EXAMPLE_92: Mapping[str, object] = {
    "name": "authorization",
    "host": {"address": ("direct", "[::1]"), "virthost": ""},
    "mode": ("url", {}),
}

EXAMPLE_93: Mapping[str, object] = {
    "name": "tls_1_1",
    "host": HOST_1,
    "mode": ("url", {"ssl": "ssl_1_1"}),
}

EXAMPLE_94: Mapping[str, object] = {
    "name": "tls_1_1",
    "host": {"address": ("direct", "[::1]")},
    "mode": ("url", {}),
}


EXAMPLE_95: Mapping[str, object] = {
    "name": "method",
    "host": HOST_1,
    "mode": (
        "url",
        {
            "method": "OPTIONS",
            "post_data": {"data": "", "content_type": "gif"},
        },
    ),
}

EXAMPLE_96: Mapping[str, object] = {
    "name": "method",
    "host": HOST_1,
    "mode": (
        "url",
        {
            "method": "TRACE",
            "post_data": {"data": "", "content_type": "gif"},
        },
    ),
}

EXAMPLE_97: Mapping[str, object] = {
    "name": "method",
    "host": HOST_1,
    "mode": (
        "url",
        {
            "method": "CONNECT",
            "post_data": {"data": "", "content_type": "gif"},
        },
    ),
}

EXAMPLE_98: Mapping[str, object] = {
    "name": "method",
    "host": HOST_1,
    "mode": (
        "url",
        {
            "method": "CONNECT_POST",
            "post_data": {"data": "", "content_type": "gif"},
        },
    ),
}

EXAMPLE_99: Mapping[str, object] = {
    "name": "method",
    "host": HOST_1,
    "mode": (
        "url",
        {
            "method": "PROPFIND",
            "post_data": {"data": "", "content_type": "gif"},
        },
    ),
}


@pytest.mark.parametrize(
    "rule_value, conflict",
    [
        (
            EXAMPLE_3,
            Conflict(
                type_=ConflictType.http_1_0_not_supported,
                host_fields=["virthost"],
            ),
        ),
        (
            EXAMPLE_5,
            Conflict(
                type_=ConflictType.http_1_0_not_supported,
                host_fields=["virthost"],
            ),
        ),
        (
            EXAMPLE_6,
            Conflict(
                type_=ConflictType.http_1_0_not_supported,
                host_fields=["virthost"],
            ),
        ),
        (
            EXAMPLE_7,
            Conflict(
                type_=ConflictType.http_1_0_not_supported,
                host_fields=["virthost"],
            ),
        ),
        (
            EXAMPLE_8,
            Conflict(
                type_=ConflictType.http_1_0_not_supported,
                host_fields=["virthost"],
            ),
        ),
        (
            EXAMPLE_9,
            Conflict(
                type_=ConflictType.http_1_0_not_supported,
                host_fields=["virthost"],
            ),
        ),
        (
            EXAMPLE_13,
            Conflict(
                type_=ConflictType.cant_migrate_proxy,
                host_fields=["address"],
            ),
        ),
        (
            EXAMPLE_14,
            Conflict(
                type_=ConflictType.cant_migrate_proxy,
                host_fields=["address"],
            ),
        ),
        (
            EXAMPLE_33,
            Conflict(
                type_=ConflictType.add_headers_incompatible,
                mode_fields=["add_headers"],
            ),
        ),
        (
            EXAMPLE_22,
            Conflict(
                type_=ConflictType.ssl_incompatible,
                mode_fields=["ssl"],
            ),
        ),
        (
            EXAMPLE_23,
            Conflict(
                type_=ConflictType.ssl_incompatible,
                mode_fields=["ssl"],
            ),
        ),
        (
            EXAMPLE_24,
            Conflict(
                type_=ConflictType.ssl_incompatible,
                mode_fields=["ssl"],
            ),
        ),
        (
            EXAMPLE_74,
            Conflict(
                type_=ConflictType.expect_response_header,
                mode_fields=["expect_response_header"],
            ),
        ),
        (
            EXAMPLE_88,
            Conflict(
                type_=ConflictType.expect_response_header,
                mode_fields=["expect_response_header"],
            ),
        ),
        (
            EXAMPLE_49,
            Conflict(
                type_=ConflictType.cant_have_regex_and_string,
                mode_fields=["expect_regex", "expect_string"],
            ),
        ),
        (
            EXAMPLE_59,
            Conflict(
                type_=ConflictType.method_unavailable,
                mode_fields=["method"],
            ),
        ),
        (
            EXAMPLE_60,
            Conflict(
                type_=ConflictType.method_unavailable,
                mode_fields=["method"],
            ),
        ),
        (
            EXAMPLE_61,
            Conflict(
                type_=ConflictType.method_unavailable,
                mode_fields=["method"],
            ),
        ),
        (
            EXAMPLE_62,
            Conflict(
                type_=ConflictType.method_unavailable,
                mode_fields=["method"],
            ),
        ),
        (
            EXAMPLE_63,
            Conflict(
                type_=ConflictType.method_unavailable,
                mode_fields=["method"],
            ),
        ),
        (
            EXAMPLE_51,
            Conflict(
                type_=ConflictType.cant_post_data,
                mode_fields=["method", "post_data"],
            ),
        ),
        (
            EXAMPLE_44,
            Conflict(
                type_=ConflictType.only_status_codes_allowed,
                mode_fields=["expect_response"],
            ),
        ),
        (
            EXAMPLE_85,
            Conflict(
                type_=ConflictType.cant_migrate_proxy,
                host_fields=["address"],
            ),
        ),
        (
            EXAMPLE_86,
            Conflict(
                type_=ConflictType.cant_migrate_proxy,
                host_fields=["address"],
            ),
        ),
        (
            EXAMPLE_86,
            Conflict(
                type_=ConflictType.cant_migrate_proxy,
                host_fields=["address"],
            ),
        ),
        (
            EXAMPLE_75,
            Conflict(
                type_=ConflictType.cant_disable_sni_with_https,
                disable_sni=True,
            ),
        ),
        (
            EXAMPLE_89,
            Conflict(
                type_=ConflictType.cant_disable_sni_with_https,
                mode_fields=["ssl"],
                disable_sni=True,
            ),
        ),
        (
            EXAMPLE_90,
            Conflict(
                type_=ConflictType.invalid_value,
                cant_load=True,
            ),
        ),
        (
            EXAMPLE_91,
            Conflict(
                type_=ConflictType.v1_checks_redirect_response,
                mode_fields=["onredirect", "expect_response"],
            ),
        ),
        (
            EXAMPLE_92,
            Conflict(
                type_=ConflictType.invalid_value,
                cant_load=True,
            ),
        ),
        (
            EXAMPLE_93,
            Conflict(
                type_=ConflictType.ssl_incompatible,
                mode_fields=["ssl"],
            ),
        ),
        (
            EXAMPLE_94,
            Conflict(
                type_=ConflictType.http_1_0_not_supported,
                host_fields=["virthost"],
            ),
        ),
        (
            EXAMPLE_19,
            Conflict(
                type_=ConflictType.cant_construct_url,
                host_fields=["address", "uri", "virthost"],
            ),
        ),
        (
            EXAMPLE_4,
            Conflict(
                type_=ConflictType.cant_construct_url,
                host_fields=["address", "uri", "virthost"],
            ),
        ),
    ],
)
def test_detect_conflicts(rule_value: Mapping[str, object], conflict: Conflict) -> None:
    assert detect_conflicts(DEFAULT, rule_value) == conflict


@pytest.mark.parametrize(
    "rule_value, config",
    [
        (
            EXAMPLE_12,
            DEFAULT,
        ),
        (
            EXAMPLE_68,
            DEFAULT,
        ),
        (
            EXAMPLE_75,
            Config(cant_disable_sni_with_https=CantDisableSNIWithHTTPS.ignore),
        ),
        (
            EXAMPLE_89,
            Config(cant_disable_sni_with_https=CantDisableSNIWithHTTPS.ignore),
        ),
    ],
)
def test_nothing_to_assert_rules(rule_value: Mapping[str, object], config: Config) -> None:
    # Assemble
    for_migration = detect_conflicts(config, rule_value)
    assert not isinstance(for_migration, Conflict)
    # Act
    migrated = migrate(for_migration)
    _ = parse_http_params(process_configuration_to_parameters(migrated).value)


@pytest.mark.parametrize(
    "rule_value, config, url, server",
    [
        (EXAMPLE_10, DEFAULT, "http://facebook.de", "google.com"),
        (EXAMPLE_15, DEFAULT, "http://google.com", "google.com"),
        (EXAMPLE_16, DEFAULT, "http://127.0.0.1", "127.0.0.1"),
        (EXAMPLE_17, DEFAULT, "http://localhost", "localhost"),
        (EXAMPLE_18, DEFAULT, "http://[::1]", "[::1]"),
        (
            EXAMPLE_20,  # TODO: check whether this would work in V1, or whether users typically use `[::1]` in their rule
            DEFAULT,
            "http://[::1]",
            "::1",
        ),
        (
            EXAMPLE_19,
            Config(cant_construct_url=CantConstructURL.force),
            "http://[::1]:80:80",
            "[::1]:80",
        ),
        (EXAMPLE_21, DEFAULT, "http://[::1]/werks", "[::1]"),
        (EXAMPLE_25, DEFAULT, "https://[::1]", "[::1]"),
        (EXAMPLE_26, DEFAULT, "https://google.com", "google.com"),
        (EXAMPLE_11, DEFAULT, "http://facebook.de", "$HOSTADDRESS$"),
    ],
)
def test_migrate_url(
    rule_value: Mapping[str, object], config: Config, url: str, server: str
) -> None:
    # Assemble
    for_migration = detect_conflicts(config, rule_value)
    assert not isinstance(for_migration, Conflict)
    # Act
    migrated = migrate(for_migration)
    # Assemble
    ssc_value = parse_http_params(process_configuration_to_parameters(migrated).value)
    # Assert
    assert ssc_value[0].url == url
    assert ssc_value[0].settings.server == server


@pytest.mark.parametrize(
    "rule_value, config, expected",
    [
        (
            EXAMPLE_27,
            DEFAULT,
            Document(
                document_body=DocumentBodyOption.FETCH,
                max_age=None,
                page_size=None,
            ),
        ),
        (
            EXAMPLE_64,
            DEFAULT,
            Document(
                document_body=DocumentBodyOption.IGNORE,
                max_age=None,
                page_size=None,
            ),
        ),
        (
            EXAMPLE_65,
            DEFAULT,
            Document(
                document_body=DocumentBodyOption.FETCH,
                max_age=None,
                page_size=PageSize(min=42, max=0),
            ),
        ),
        (
            EXAMPLE_66,
            DEFAULT,
            Document(
                document_body=DocumentBodyOption.FETCH,
                max_age=111.0,
                page_size=None,
            ),
        ),
        (
            EXAMPLE_67,
            DEFAULT,
            Document(
                document_body=DocumentBodyOption.IGNORE,
                max_age=111.0,
                page_size=None,
            ),
        ),
    ],
)
def test_migrate_document(
    rule_value: Mapping[str, object], config: Config, expected: object
) -> None:
    # Assemble
    for_migration = detect_conflicts(config, rule_value)
    assert not isinstance(for_migration, Conflict)
    # Act
    migrated = migrate(for_migration)
    # Assemble
    ssc_value = parse_http_params(process_configuration_to_parameters(migrated).value)
    # Assert
    assert ssc_value[0].settings.document == expected


@pytest.mark.parametrize(
    "rule_value, config, expected",
    [
        (
            EXAMPLE_27,
            DEFAULT,
            (HttpMethod.GET, None),
        ),
        (
            EXAMPLE_50,
            DEFAULT,
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
            DEFAULT,
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
            DEFAULT,
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
            DEFAULT,
            (HttpMethod.GET, None),
        ),
        (
            EXAMPLE_55,
            DEFAULT,
            (HttpMethod.DELETE, None),
        ),
        (
            EXAMPLE_56,
            DEFAULT,
            (HttpMethod.HEAD, None),
        ),
        (
            EXAMPLE_57,
            DEFAULT,
            (HttpMethod.PUT, SendData(send_data=None)),
        ),
        (
            EXAMPLE_58,
            DEFAULT,
            (HttpMethod.POST, SendData(send_data=None)),
        ),
        (
            EXAMPLE_51,
            Config(cant_post_data=CantPostData.post),
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
            EXAMPLE_51,
            Config(cant_post_data=CantPostData.prefermethod),
            (HttpMethod.GET, None),
        ),
        (
            EXAMPLE_59,
            Config(method_unavailable=MethodUnavailable.ignore),
            (HttpMethod.GET, None),
        ),
        (
            EXAMPLE_60,
            Config(method_unavailable=MethodUnavailable.ignore),
            (HttpMethod.GET, None),
        ),
        (
            EXAMPLE_61,
            Config(method_unavailable=MethodUnavailable.ignore),
            (HttpMethod.GET, None),
        ),
        (
            EXAMPLE_62,
            Config(method_unavailable=MethodUnavailable.ignore),
            (HttpMethod.GET, None),
        ),
        (
            EXAMPLE_63,
            Config(method_unavailable=MethodUnavailable.ignore),
            (HttpMethod.GET, None),
        ),
        (
            EXAMPLE_95,
            Config(method_unavailable=MethodUnavailable.ignore),
            (
                HttpMethod.POST,
                SendData(
                    send_data=SendDataInner(content="", content_type=(SendDataType.CUSTOM, "gif"))
                ),
            ),
        ),
        (
            EXAMPLE_96,
            Config(method_unavailable=MethodUnavailable.ignore),
            (
                HttpMethod.POST,
                SendData(
                    send_data=SendDataInner(content="", content_type=(SendDataType.CUSTOM, "gif"))
                ),
            ),
        ),
        (
            EXAMPLE_97,
            Config(method_unavailable=MethodUnavailable.ignore),
            (
                HttpMethod.POST,
                SendData(
                    send_data=SendDataInner(content="", content_type=(SendDataType.CUSTOM, "gif"))
                ),
            ),
        ),
        (
            EXAMPLE_98,
            Config(method_unavailable=MethodUnavailable.ignore),
            (
                HttpMethod.POST,
                SendData(
                    send_data=SendDataInner(content="", content_type=(SendDataType.CUSTOM, "gif"))
                ),
            ),
        ),
        (
            EXAMPLE_99,
            Config(method_unavailable=MethodUnavailable.ignore),
            (
                HttpMethod.POST,
                SendData(
                    send_data=SendDataInner(content="", content_type=(SendDataType.CUSTOM, "gif"))
                ),
            ),
        ),
    ],
)
def test_migrate_method(rule_value: Mapping[str, object], config: Config, expected: object) -> None:
    # Assemble
    for_migration = detect_conflicts(config, rule_value)
    assert not isinstance(for_migration, Conflict)
    # Act
    migrated = migrate(for_migration)
    # Assemble
    ssc_value = parse_http_params(process_configuration_to_parameters(migrated).value)
    # Assert
    assert ssc_value[0].settings.connection is not None
    assert ssc_value[0].settings.connection.method == expected


@pytest.mark.parametrize(
    "rule_value, config, expected",
    [
        (
            EXAMPLE_47,
            DEFAULT,
            (
                MatchType.REGEX,
                BodyRegex(regex="example", case_insensitive=True, multiline=True, invert=True),
            ),
        ),
        (
            EXAMPLE_48,
            DEFAULT,
            (
                MatchType.REGEX,
                BodyRegex(regex="", case_insensitive=False, multiline=False, invert=False),
            ),
        ),
        (
            EXAMPLE_49,
            Config(cant_have_regex_and_string=CantHaveRegexAndString.regex),
            (
                MatchType.REGEX,
                BodyRegex(regex="example", case_insensitive=True, multiline=True, invert=True),
            ),
        ),
    ],
)
def test_migrate_expect_regex(
    rule_value: Mapping[str, object], config: Config, expected: object
) -> None:
    # Assemble
    for_migration = detect_conflicts(config, rule_value)
    assert not isinstance(for_migration, Conflict)
    # Act
    migrated = migrate(for_migration)
    # Assemble
    ssc_value = parse_http_params(process_configuration_to_parameters(migrated).value)
    # Assert
    assert ssc_value[0].settings.content is not None
    assert ssc_value[0].settings.content.body == expected


@pytest.mark.parametrize(
    "rule_value, config",
    [
        (
            EXAMPLE_27,
            DEFAULT,
        ),
        (
            EXAMPLE_74,
            Config(expect_response_header=ExpectResponseHeader.ignore),
        ),
        (
            EXAMPLE_88,
            Config(expect_response_header=ExpectResponseHeader.ignore),
        ),
    ],
)
def test_migrate_content_is_none(rule_value: Mapping[str, object], config: Config) -> None:
    # Assemble
    for_migration = detect_conflicts(config, rule_value)
    assert not isinstance(for_migration, Conflict)
    # Act
    migrated = migrate(for_migration)
    # Assemble
    ssc_value = parse_http_params(process_configuration_to_parameters(migrated).value)
    # Assert
    assert ssc_value[0].settings.content is None


@pytest.mark.parametrize(
    "rule_value, config, expected",
    [
        (EXAMPLE_17, DEFAULT, None),
        (EXAMPLE_25, DEFAULT, {"min_version": TlsVersion.TLS_1_2, "allow_higher": False}),
        (EXAMPLE_27, DEFAULT, {"min_version": TlsVersion.AUTO, "allow_higher": True}),
        (
            EXAMPLE_22,
            Config(ssl_incompatible=SSLIncompatible.negotiate),
            {"min_version": TlsVersion.AUTO, "allow_higher": True},
        ),
        (
            EXAMPLE_23,
            Config(ssl_incompatible=SSLIncompatible.negotiate),
            {"min_version": TlsVersion.AUTO, "allow_higher": True},
        ),
        (
            EXAMPLE_24,
            Config(ssl_incompatible=SSLIncompatible.negotiate),
            {"min_version": TlsVersion.AUTO, "allow_higher": True},
        ),
        (
            EXAMPLE_93,
            Config(ssl_incompatible=SSLIncompatible.negotiate),
            {"min_version": TlsVersion.AUTO, "allow_higher": True},
        ),
    ],
)
def test_migrate_ssl(rule_value: Mapping[str, object], config: Config, expected: str) -> None:
    # Assemble
    for_migration = detect_conflicts(config, rule_value)
    assert not isinstance(for_migration, Conflict)
    # Act
    migrated = migrate(for_migration)
    # Assemble
    ssc_value = parse_http_params(process_configuration_to_parameters(migrated).value)
    # Assert
    assert ssc_value[0].settings.connection is not None
    assert ssc_value[0].settings.connection.model_dump().get("tls_versions") == expected


@pytest.mark.parametrize(
    "rule_value, config, expected",
    [
        (EXAMPLE_1, DEFAULT, (LevelsType.FIXED, (0.1, 0.2))),
        (EXAMPLE_2, DEFAULT, (LevelsType.FIXED, (0.1, 0.2))),
        (EXAMPLE_27, DEFAULT, None),
        (EXAMPLE_28, DEFAULT, (LevelsType.FIXED, (0.0, 0.0))),
        (EXAMPLE_84, DEFAULT, (LevelsType.NO_LEVELS, None)),
    ],
)
def test_migrate_response_time(
    rule_value: Mapping[str, object], config: Config, expected: object
) -> None:
    # Assemble
    for_migration = detect_conflicts(config, rule_value)
    assert not isinstance(for_migration, Conflict)
    # Act
    migrated = migrate(for_migration)
    # Assemble
    ssc_value = parse_http_params(process_configuration_to_parameters(migrated).value)
    # Assert
    assert ssc_value[0].settings.response_time == expected


@pytest.mark.parametrize(
    "rule_value, config, expected",
    [
        (EXAMPLE_46, DEFAULT, (MatchType.STRING, "example")),
        (
            EXAMPLE_49,
            Config(cant_have_regex_and_string=CantHaveRegexAndString.string),
            (MatchType.STRING, "example"),
        ),
    ],
)
def test_migrate_expect_string(
    rule_value: Mapping[str, object], config: Config, expected: object
) -> None:
    # Assemble
    for_migration = detect_conflicts(config, rule_value)
    assert not isinstance(for_migration, Conflict)
    # Act
    migrated = migrate(for_migration)
    # Assemble
    ssc_value = parse_http_params(process_configuration_to_parameters(migrated).value)
    # Assert
    assert ssc_value[0].settings.content is not None
    assert ssc_value[0].settings.content.body == expected


@pytest.mark.parametrize(
    "rule_value, config, expected",
    [
        (EXAMPLE_27, DEFAULT, None),
        (EXAMPLE_29, DEFAULT, 10.0),
        (EXAMPLE_30, DEFAULT, 0.0),
    ],
)
def test_migrate_timeout(
    rule_value: Mapping[str, object], config: Config, expected: object
) -> None:
    # Assemble
    for_migration = detect_conflicts(config, rule_value)
    assert not isinstance(for_migration, Conflict)
    # Act
    migrated = migrate(for_migration)
    # Assemble
    ssc_value = parse_http_params(process_configuration_to_parameters(migrated).value)
    # Assert
    assert ssc_value[0].settings.connection is not None
    assert ssc_value[0].settings.connection.model_dump()["timeout"] == expected


@pytest.mark.parametrize(
    "rule_value, config, expected",
    [
        (EXAMPLE_27, DEFAULT, None),
        (EXAMPLE_31, DEFAULT, "agent"),
    ],
)
def test_migrate_user_agent(
    rule_value: Mapping[str, object], config: Config, expected: object
) -> None:
    # Assemble
    for_migration = detect_conflicts(config, rule_value)
    assert not isinstance(for_migration, Conflict)
    # Act
    migrated = migrate(for_migration)
    # Assemble
    ssc_value = parse_http_params(process_configuration_to_parameters(migrated).value)
    # Assert
    assert ssc_value[0].settings.connection is not None
    assert ssc_value[0].settings.connection.model_dump()["user_agent"] == expected


@pytest.mark.parametrize(
    "rule_value, config, expected",
    [
        (
            EXAMPLE_27,
            DEFAULT,
            None,
        ),
        (
            EXAMPLE_32,
            DEFAULT,
            [
                {"header_name": "head", "header_value": "tail"},
                {"header_name": "mop", "header_value": ""},
                {"header_name": "a", "header_value": "b: c"},
            ],
        ),
        (
            EXAMPLE_34,
            DEFAULT,
            [{"header_name": "head", "header_value": "tail"}],
        ),
        (
            EXAMPLE_35,
            DEFAULT,
            [{"header_name": "head", "header_value": ""}],
        ),
        (
            EXAMPLE_71,
            DEFAULT,
            [{"header_name": "", "header_value": "tail"}],
        ),
        (
            EXAMPLE_72,
            DEFAULT,
            [{"header_name": "head", "header_value": "tail"}],
        ),
        (
            EXAMPLE_33,
            Config(add_headers_incompatible=AdditionalHeaders.ignore),
            [{"header_name": "head", "header_value": "tail"}],
        ),
    ],
)
def test_migrate_add_headers(
    rule_value: Mapping[str, object], config: Config, expected: object
) -> None:
    # Assemble
    for_migration = detect_conflicts(config, rule_value)
    assert not isinstance(for_migration, Conflict)
    # Act
    migrated = migrate(for_migration)
    # Assemble
    ssc_value = parse_http_params(process_configuration_to_parameters(migrated).value)
    # Assert
    assert ssc_value[0].settings.connection is not None
    assert ssc_value[0].settings.connection.model_dump()["add_headers"] == expected


def test_migrate_auth_user() -> None:
    # Assemble
    for_migration = detect_conflicts(DEFAULT, EXAMPLE_36)
    assert not isinstance(for_migration, Conflict)
    # Act
    migrated = migrate(for_migration)
    # Assemble
    ssc_value = parse_http_params(process_configuration_to_parameters(migrated).value)
    # Assert
    assert ssc_value[0].settings.connection is not None
    assert ssc_value[0].settings.connection.auth is not None
    assert ssc_value[0].settings.connection.auth[0].value == "user_auth"


def test_migrate_auth_no_auth() -> None:
    # Assemble
    for_migration = detect_conflicts(DEFAULT, EXAMPLE_27)
    assert not isinstance(for_migration, Conflict)
    # Act
    migrated = migrate(for_migration)
    # Assemble
    ssc_value = parse_http_params(process_configuration_to_parameters(migrated).value)
    # Assert
    assert ssc_value[0].settings.connection is not None
    assert ssc_value[0].settings.connection.auth is None


@pytest.mark.parametrize(
    "rule_value, config, redirects, expect_response",
    [
        (
            EXAMPLE_27,
            DEFAULT,
            "ok",
            None,
        ),  # TODO: discuss with PM
        (
            EXAMPLE_37,
            DEFAULT,
            "ok",
            None,
        ),
        (
            EXAMPLE_38,
            DEFAULT,
            "warning",
            None,
        ),
        (
            EXAMPLE_39,
            DEFAULT,
            "critical",
            None,
        ),
        (
            EXAMPLE_40,
            DEFAULT,
            "follow",
            None,
        ),
        (
            EXAMPLE_41,
            DEFAULT,
            "sticky",
            None,
        ),
        (
            EXAMPLE_42,
            DEFAULT,
            "stickyport",
            None,
        ),
        (
            EXAMPLE_91,
            Config(
                v1_checks_redirect_response=V1ChecksRedirectResponse.acknowledge,
            ),
            "stickyport",
            ServerResponse(expected=[302]),
        ),
    ],
)
def test_migrate_redirect(
    rule_value: Mapping[str, object],
    config: Config,
    redirects: object,
    expect_response: object,
) -> None:
    # Assemble
    for_migration = detect_conflicts(config, rule_value)
    assert not isinstance(for_migration, Conflict)
    # Act
    migrated = migrate(for_migration)
    # Assemble
    ssc_value = parse_http_params(process_configuration_to_parameters(migrated).value)
    # Assert
    assert ssc_value[0].settings.connection is not None
    assert ssc_value[0].settings.connection.model_dump()["redirects"] == redirects
    assert ssc_value[0].settings.server_response == expect_response


def test_helper_migrate_expect_response() -> None:
    assert _migrate_expect_response(["HTTP/1.1 200 OK", "302 REDIRECT", "404"]) == [200, 302, 404]


@pytest.mark.parametrize(
    "rule_value, config, expected",
    [
        (EXAMPLE_27, DEFAULT, None),
        (EXAMPLE_45, DEFAULT, ServerResponse(expected=[])),
        (
            EXAMPLE_44,
            Config(only_status_codes_allowed=OnlyStatusCodesAllowed.ignore),
            ServerResponse(expected=[]),
        ),
    ],
)
def test_migrate_expect_response(
    rule_value: Mapping[str, object], config: Config, expected: object
) -> None:
    # Assemble
    for_migration = detect_conflicts(config, rule_value)
    assert not isinstance(for_migration, Conflict)
    # Act
    migrated = migrate(for_migration)
    # Assemble
    ssc_value = parse_http_params(process_configuration_to_parameters(migrated).value)
    # Assert
    assert ssc_value[0].settings.server_response == expected


@pytest.mark.parametrize(
    "rule_value, config, expected",
    [
        (EXAMPLE_69, DEFAULT, (CertificateValidity.VALIDATE, (LevelsType.FIXED, (0.0, 0.0)))),
        (EXAMPLE_70, DEFAULT, (CertificateValidity.VALIDATE, (LevelsType.NO_LEVELS, None))),
    ],
)
def test_migrate_cert(rule_value: Mapping[str, object], config: Config, expected: object) -> None:
    # Assemble
    for_migration = detect_conflicts(config, rule_value)
    assert not isinstance(for_migration, Conflict)
    # Act
    migrated = migrate(for_migration)
    # Assemble
    ssc_value = parse_http_params(process_configuration_to_parameters(migrated).value)
    # Assert
    assert ssc_value[0].settings.cert == expected


@pytest.mark.parametrize(
    "rule_value, config, expected",
    [
        (EXAMPLE_43, DEFAULT, (MatchType.STRING, HeaderSpec(header_name="yes", header_value="no"))),
        (EXAMPLE_73, DEFAULT, (MatchType.STRING, HeaderSpec(header_name="yes", header_value="no"))),
    ],
)
def test_migrate_expect_response_header(
    rule_value: Mapping[str, object], config: Config, expected: object
) -> None:
    # Assemble
    for_migration = detect_conflicts(config, rule_value)
    assert not isinstance(for_migration, Conflict)
    # Act
    migrated = migrate(for_migration)
    # Assemble
    ssc_value = parse_http_params(process_configuration_to_parameters(migrated).value)
    # Assert
    assert ssc_value[0].settings.content is not None
    assert ssc_value[0].settings.content.header == expected


@pytest.mark.parametrize(
    "rule_value, config, expected",
    [
        (
            EXAMPLE_76,
            DEFAULT,
            ServiceDescription(prefix=ServicePrefix.AUTO, name="name (migrated)"),
        ),
        (
            EXAMPLE_77,
            DEFAULT,
            ServiceDescription(prefix=ServicePrefix.NONE, name="name (migrated)"),
        ),
        (
            EXAMPLE_78,
            DEFAULT,
            ServiceDescription(prefix=ServicePrefix.AUTO, name="name (migrated)"),
        ),
        (
            EXAMPLE_79,
            DEFAULT,
            ServiceDescription(prefix=ServicePrefix.AUTO, name="name (migrated)"),
        ),
    ],
)
def test_migrate_name(rule_value: Mapping[str, object], config: Config, expected: object) -> None:
    # Assemble
    for_migration = detect_conflicts(config, rule_value)
    assert not isinstance(for_migration, Conflict)
    # Act
    migrated = migrate(for_migration)
    # Assemble
    ssc_value = parse_http_params(process_configuration_to_parameters(migrated).value)
    # Assert
    assert ssc_value[0].service_name == expected


@pytest.mark.parametrize(
    "rule_value, config, expected",
    [
        (EXAMPLE_27, DEFAULT, AddressFamily.ANY),
        (EXAMPLE_80, DEFAULT, AddressFamily.ANY),
        (EXAMPLE_81, DEFAULT, AddressFamily.IPV4),
        (EXAMPLE_82, DEFAULT, AddressFamily.PRIMARY),
        (EXAMPLE_83, DEFAULT, AddressFamily.IPV6),
    ],
)
def test_migrate_address_family(
    rule_value: Mapping[str, object], config: Config, expected: object
) -> None:
    # Assemble
    for_migration = detect_conflicts(config, rule_value)
    assert not isinstance(for_migration, Conflict)
    # Act
    migrated = migrate(for_migration)
    # Assemble
    ssc_value = parse_http_params(process_configuration_to_parameters(migrated).value)
    # Assert
    assert ssc_value[0].settings.connection is not None
    assert ssc_value[0].settings.connection.address_family == expected


def test_preserve_http_version() -> None:
    # Assemble
    for_migration = detect_conflicts(DEFAULT, EXAMPLE_27)
    assert not isinstance(for_migration, Conflict)
    # Act
    migrated = migrate(for_migration)
    # Assemble
    ssc_value = parse_http_params(process_configuration_to_parameters(migrated).value)
    # Assert
    assert ssc_value[0].settings.connection is not None
    assert ssc_value[0].settings.connection.http_versions is None


@pytest.mark.parametrize(
    "rule_value, config, expected",
    [
        (
            EXAMPLE_94,
            Config(
                http_1_0_not_supported=HTTP10NotSupported.ignore,
            ),
            "http://[::1]",
        ),
    ],
)
def test_migrate_http_1_0(
    rule_value: Mapping[str, object], config: Config, expected: object
) -> None:
    # Assemble
    for_migration = detect_conflicts(config, rule_value)
    assert not isinstance(for_migration, Conflict)
    # Act
    migrated = migrate(for_migration)
    # Assemble
    ssc_value = parse_http_params(process_configuration_to_parameters(migrated).value)
    # Assert
    assert ssc_value[0].url == expected
