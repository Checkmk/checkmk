#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from .bakery_api.v1 import FileGenerator, OS, Plugin, PluginConfig, register


class _Site(BaseModel):
    site_name: str
    tags: list[str] = []
    service_check_commands: list[str] = []


class _Config(BaseModel):
    deployment: tuple[Literal["do_not_deploy", "sync", "cached"], float | None]
    tags: list[str] = []
    service_check_commands: list[str] = []
    sites: list[_Site] = []


def get_mk_site_object_counts_files(conf: Mapping[str, object]) -> FileGenerator:
    config = _Config.model_validate(conf)
    if config.deployment[0] == "do_not_deploy":
        return

    yield Plugin(
        base_os=OS.LINUX,
        source=Path("mk_site_object_counts"),
        interval=None if (v := config.deployment[1]) is None else int(v),
    )

    yield PluginConfig(
        base_os=OS.LINUX,
        lines=list(_get_mk_site_object_counts_config(config)),
        target=Path("site_object_counts.cfg"),
        include_header=True,
    )


def _get_mk_site_object_counts_config(config: _Config) -> Iterable[str]:
    if config.tags:
        yield "TAGS={}".format(" ".join(config.tags))
    if config.service_check_commands:
        yield "SERVICE_CHECK_COMMANDS={}".format(" ".join(config.service_check_commands))

    site_names = []
    for site in config.sites:
        site_names.append(site.site_name)
        if site.tags:
            yield "TAGS_{}={}".format(site.site_name, " ".join(site.tags))
        if site.service_check_commands:
            yield "SERVICE_CHECK_COMMANDS_{}={}".format(
                site.site_name, " ".join(site.service_check_commands)
            )
    if site_names:
        yield "SITES={}".format(" ".join(site_names))


register.bakery_plugin(
    name="mk_site_object_counts",
    files_function=get_mk_site_object_counts_files,
)
