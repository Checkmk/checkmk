#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.oauth.resource_names import resource_display_name


def test_resource_display_name_returns_empty_string_for_none() -> None:
    assert resource_display_name(None) == ""


@pytest.mark.parametrize(
    "resource",
    [
        "http://localhost/mysite/check_mk/mcp",
        "https://host.example/othersite/check_mk/mcp",
    ],
)
def test_resource_display_name_recognizes_the_mcp_server(resource: str) -> None:
    assert resource_display_name(resource) == "MCP"


def test_resource_display_name_falls_back_to_the_raw_value_for_unknown_resources() -> None:
    assert resource_display_name("https://host.example/something-else") == (
        "https://host.example/something-else"
    )
