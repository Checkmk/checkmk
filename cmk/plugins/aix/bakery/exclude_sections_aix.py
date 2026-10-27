#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable
from pathlib import Path

from pydantic import BaseModel

from cmk.bakery.v2 import BakeryPlugin, FileGenerator, OS, PluginConfig


class _Config(BaseModel):
    sections_aix: list[str] = []


def get_agent_exclude_sections_files_aix(config: _Config) -> FileGenerator:
    if not config.sections_aix:
        return
    yield PluginConfig(
        base_os=OS.AIX,
        lines=list(get_agent_exclude_section_lines_aix(config.sections_aix)),
        target=Path("exclude_sections_aix.cfg"),
        include_header=True,
    )


def get_agent_exclude_section_lines_aix(excluded_sections_list_aix: list[str]) -> Iterable[str]:
    exclude_name = "MK_SKIP_%s=yes"
    for section_name in excluded_sections_list_aix:
        yield exclude_name % section_name.upper()


bakery_plugin_exclude_sections_aix = BakeryPlugin(
    name="exclude_sections_aix",
    parameter_parser=_Config.model_validate,
    default_parameters=None,
    files_function=get_agent_exclude_sections_files_aix,
)
