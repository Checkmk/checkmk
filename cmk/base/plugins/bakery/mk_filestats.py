#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from .bakery_api.v1 import FileGenerator, OS, Plugin, PluginConfig, register


class _Grouping(BaseModel):
    group_name: str
    condition: tuple[str, str]


class _Section(BaseModel):
    input_patterns: str = ""
    filter_regex: str = ""
    filter_regex_inverse: str = ""
    filter_size: str = ""
    filter_age: str = ""
    output: str = ""
    grouping: list[_Grouping] = Field(default_factory=list)


class _NamedSection(_Section):
    name: str


class _Config(BaseModel):
    deployment: tuple[Literal["do_not_deploy", "sync", "cached"], float | None]
    deploy_config: bool = True
    default: _Section = Field(default_factory=_Section)
    subgroups_delimiter: str = "@"
    sections: list[_NamedSection] = Field(default_factory=list)


def get_mk_filestats_files(conf: Mapping[str, object]) -> FileGenerator:
    config = _Config.model_validate(conf)
    if config.deployment[0] == "do_not_deploy":
        return

    interval = None if (v := config.deployment[1]) is None else int(v)

    for base_os in (OS.LINUX, OS.SOLARIS):
        yield Plugin(base_os=base_os, source=Path("mk_filestats.py"), interval=interval)

    if not config.deploy_config:
        return

    sections = config.sections
    default = config.default
    if not (default.model_dump(exclude_defaults=True) or sections):
        return
    lines = list(
        _get_mk_filestats_config(
            sections,
            default,
            config.subgroups_delimiter,
        )
    )

    for base_os in (OS.LINUX, OS.SOLARIS):
        yield PluginConfig(
            base_os=base_os,
            lines=lines,
            target=Path("filestats.cfg"),
            include_header=True,
        )


def _get_mk_filestats_config(
    sections: Sequence[_NamedSection],
    default: _Section,
    subgroups_delimiter: str = "@",
) -> Iterable[str]:
    yield "[DEFAULT]"
    yield f"subgroups_delimiter: {subgroups_delimiter}"
    default_dict = default.model_dump(exclude_defaults=True)
    default_dict.pop("grouping", None)
    for key, value in default_dict.items():
        yield f"{key}: {value}"
    if default.grouping:
        yield from _parse_grouping_options("DEFAULT", subgroups_delimiter, default.grouping)

    yield ""

    for section in sections:
        yield f"[{section.name}]"
        section_dict = section.model_dump(exclude_defaults=True)
        section_dict.pop("grouping", None)
        section_dict.pop("name", None)
        for key, value in section_dict.items():
            yield f"{key}: {value}"
        if section.grouping:
            yield from _parse_grouping_options(section.name, subgroups_delimiter, section.grouping)
        yield ""


def _parse_grouping_options(
    section_name: str,
    subgroups_delimiter: str,
    grouping_options: Sequence[_Grouping],
) -> Iterable[str]:
    for group_item in grouping_options:
        option_type, rule = group_item.condition
        yield ""
        yield f"[{section_name}{subgroups_delimiter}{group_item.group_name}]"
        yield f"grouping_{option_type}: {rule}"


register.bakery_plugin(
    name="mk_filestats",
    files_function=get_mk_filestats_files,
)
