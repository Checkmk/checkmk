#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from cmk.agent_based.v1.type_defs import StringTable
from cmk.plugins.collection.agent_based.checkmk_cached_plugins import parse_checkmk_cached_plugins
from cmk.plugins.lib.checkmk import CachedPlugin, CachedPluginsSection, CachedPluginType


@pytest.mark.parametrize(
    [
        "string_table",
        "expected_result",
    ],
    [
        pytest.param(
            [["timeout", "plugins_some_plugin", "123", "4711"]],
            CachedPluginsSection(
                timeout=[
                    CachedPlugin(
                        plugin_type=CachedPluginType.PLUGIN,
                        plugin_name="some_plugin",
                        timeout=123,
                        pid=4711,
                    ),
                ],
                killfailed=None,
            ),
            id="timeout_agent_plugin",
        ),
        pytest.param(
            [["killfailed", "local_my_local_check", "7200", "1234"]],
            CachedPluginsSection(
                timeout=None,
                killfailed=[
                    CachedPlugin(
                        plugin_type=CachedPluginType.LOCAL,
                        plugin_name="my_local_check",
                        timeout=7200,
                        pid=1234,
                    ),
                ],
            ),
            id="killfailed_local_check",
        ),
        pytest.param(
            [
                ["timeout", "plugins_some_plugin", "7200", "1234"],
                ["timeout", "other_process", "7200", "1234"],
                ["killfailed", "local_my_local_check", "7200", "1234"],
                ["killfailed", "oracle_destroy_db", "123", "4711"],
            ],
            CachedPluginsSection(
                timeout=[
                    CachedPlugin(
                        plugin_type=CachedPluginType.PLUGIN,
                        plugin_name="some_plugin",
                        timeout=7200,
                        pid=1234,
                    ),
                    CachedPlugin(
                        plugin_type=None,
                        plugin_name="other_process",
                        timeout=7200,
                        pid=1234,
                    ),
                ],
                killfailed=[
                    CachedPlugin(
                        plugin_type=CachedPluginType.LOCAL,
                        plugin_name="my_local_check",
                        timeout=7200,
                        pid=1234,
                    ),
                    CachedPlugin(
                        plugin_type=CachedPluginType.ORACLE,
                        plugin_name="destroy_db",
                        timeout=123,
                        pid=4711,
                    ),
                ],
            ),
            id="timeout_and_killfailed",
        ),
    ],
)
def test_parse_checkmk_cached_plugins(
    string_table: StringTable,
    expected_result: CachedPluginsSection,
) -> None:
    assert parse_checkmk_cached_plugins(string_table) == expected_result
