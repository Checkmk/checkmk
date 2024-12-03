#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.update_config.http.main import _migratable

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


@pytest.mark.parametrize(
    "rule_value",
    [
        EXAMPLE_3,
    ],
)
def test_migrateable_rules(rule_value: Mapping[str, object]) -> None:
    assert _migratable(rule_value)


@pytest.mark.parametrize(
    "rule_value",
    [
        EXAMPLE_1,
        EXAMPLE_2,
        EXAMPLE_4,
    ],
)
def test_non_migrateable_rules(rule_value: Mapping[str, object]) -> None:
    assert not _migratable(rule_value)
