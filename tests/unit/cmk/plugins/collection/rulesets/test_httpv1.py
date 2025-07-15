#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.ccc.version import Edition

from cmk.gui.utils.rule_specs.legacy_converter import convert_to_legacy_rulespec

from cmk.plugins.collection.rulesets.httpv1 import rule_spec_http


@pytest.mark.parametrize(
    ["rule"],
    [
        pytest.param(
            {
                "name": "test.com",
                "host": {},
                "mode": ("url", {}),
            },
            id="minimal 2.3 rule",
        ),
        pytest.param(
            {
                "name": "test.com",
                "host": {"address": ("direct", "test"), "address_family": "ipv6"},
                "mode": ("url", {"timeout": 10}),
            },
            id="with host address 2.3 rule",
        ),
        pytest.param(
            {
                "name": "test.com",
                "host": {
                    "address": (
                        "proxy",
                        {
                            "address": "proxy.net",
                            "port": 80,
                            "auth": ("usr", ("password", "password")),
                        },
                    ),
                    "address_family": "ipv6",
                },
                "mode": ("url", {"timeout": 10}),
            },
            id="with proxy 2.3 rule",
        ),
        pytest.param(
            {
                "name": "old.com",
                "host": {"address": ("direct", "1.2.3.4"), "virthost": "virthost"},
                "mode": ("url", {}),
            },
            id="address and virtual host 2.3 rule",
        ),
        pytest.param(
            {
                "name": "old.com",
                "host": {"virthost": "virthost"},
                "mode": ("cert", {"cert_days": (10, 20)}),
                "disable_sni": True,
            },
            id="virtual host only 2.3 rule",
        ),
        pytest.param(
            {
                "name": "old.com",
                "host": {"address": ("proxy", {"address": "proxy", "port": 80}), "port": 443},
                "mode": ("cert", {"cert_days": (10, 20)}),
            },
            id="with proxy 2.3 rule",
        ),
        pytest.param(
            {
                "name": "old.com",
                "host": {
                    "address": (
                        "proxy",
                        {"address": "proxy", "auth": ("user", ("password", "pwd")), "port": 80},
                    ),
                    "address_family": "ipv6",
                    "virthost": "my-machine",
                },
                "mode": ("url", {"urlize": True}),
            },
            id="with address and proxy 2.3 rule",
        ),
        pytest.param(
            {
                "name": "old.com",
                "host": {
                    "address": (
                        "proxy",
                        {"address": "proxy", "auth": ("user", ("password", "pwd")), "port": 80},
                    ),
                    "address_family": "ipv6",
                },
                "mode": ("url", {"urlize": True}),
            },
            id="with virtual host and proxy 2.3 rule",
        ),
        pytest.param(
            {
                "host": {
                    "address": (
                        "proxy",
                        {"address": "proxy", "auth": ("user", ("password", "pwd")), "port": 80},
                    ),
                    "address_family": "ipv6",
                    "port": 443,
                    "virthost": "my-machine",
                },
                "mode": ("url", {"onredirect": "follow", "urlize": True}),
                "name": "old.com",
            },
            id="with address, virtual host and proxy 2.3 rule",
        ),
        pytest.param(
            {
                "name": "test-service",
                "host": {
                    "address": (
                        "proxy",
                        {
                            "address": "test-proxy",
                            "port": 80,
                            "auth": ("test-user", ("password", "test-password")),
                        },
                    ),
                    "port": 443,
                    "address_family": "ipv4",
                    "virthost": "test-hoost",
                },
                "mode": (
                    "url",
                    {
                        "uri": "/url.com",
                        "ssl": "1.1",
                        "response_time": (100.0, 200.0),
                        "timeout": 10,
                        "user_agent": "test-agent",
                        "add_headers": ["header", "lines"],
                        "auth": ("test-user-2", ("password", "test-password-2")),
                        "onredirect": "critical",
                        "expect_response_header": "test-response-header",
                        "expect_response": ["test-response"],
                        "expect_string": "test-content",
                        "expect_regex": ("test-regex", True, True, True),
                        "post_data": ("test-post", "text/html"),
                        "method": "POST",
                        "no_body": True,
                        "page_size": (1, 500),
                        "max_age": 604800,
                        "urlize": True,
                        "extended_perfdata": True,
                    },
                ),
                "disable_sni": True,
            },
            id="maximal 2.3 rule",
        ),
    ],
)
def test_rule_spec_http_migration_validation(rule: dict[str, object]) -> None:
    validating_rule_spec = convert_to_legacy_rulespec(rule_spec_http, Edition.CRE, lambda x: x)
    validating_rule_spec.valuespec.validate_datatype(rule, "")
    validating_rule_spec.valuespec.validate_value(rule, "")
