#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable
from pathlib import Path

from pydantic import BaseModel

from cmk.bakery.v2 import BakeryPlugin, FileGenerator, OS, PluginConfig


class _Config(BaseModel):
    sections: list[str] | None = None


def get_agent_exclude_sections_files(config: _Config) -> FileGenerator:
    if config.sections is None:
        return
    yield PluginConfig(
        base_os=OS.LINUX,
        lines=list(get_agent_exclude_section_lines(config.sections)),
        target=Path("exclude_sections.cfg"),
        include_header=True,
    )


def get_agent_exclude_section_lines(excluded_sections_list: list[str]) -> Iterable[str]:
    exclude_name = "MK_SKIP_%s=yes"
    for section_name in excluded_sections_list:
        yield exclude_name % section_name.upper()


bakery_plugin_agent_exclude_sections = BakeryPlugin(
    name="agent_exclude_sections",
    parameter_parser=_Config.model_validate,
    default_parameters=None,
    files_function=get_agent_exclude_sections_files,
)
