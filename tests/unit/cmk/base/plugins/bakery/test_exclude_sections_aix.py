#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from cmk.bakery.v1 import OS, PluginConfig
from cmk.base.plugins.bakery.exclude_sections_aix import (
    get_agent_exclude_section_lines_aix,
    get_agent_exclude_sections_files_aix,
)


def test_exclude_sections_files_aix_with_sections() -> None:
    conf = {"sections_aix": ["cpu", "mem", "df"]}
    result = list(get_agent_exclude_sections_files_aix(conf))
    assert len(result) == 1
    plugin_config = result[0]
    assert isinstance(plugin_config, PluginConfig)
    assert plugin_config.base_os == OS.AIX
    assert plugin_config.target == Path("exclude_sections_aix.cfg")
    assert plugin_config.include_header is True
    assert plugin_config.lines == [
        "MK_SKIP_CPU=yes",
        "MK_SKIP_MEM=yes",
        "MK_SKIP_DF=yes",
    ]


def test_exclude_sections_files_aix_no_sections() -> None:
    result = list(get_agent_exclude_sections_files_aix({}))
    assert result == []


def test_get_agent_exclude_section_lines_aix() -> None:
    result = list(get_agent_exclude_section_lines_aix(["cpu", "mem"]))
    assert result == ["MK_SKIP_CPU=yes", "MK_SKIP_MEM=yes"]
