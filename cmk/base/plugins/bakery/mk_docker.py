#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from .bakery_api.v1 import FileGenerator, OS, Plugin, PluginConfig, register


class _Config(BaseModel):
    deployment: tuple[Literal["do_not_deploy", "sync", "cached"], float | None]
    node: Sequence[str] = []
    containers: Sequence[str] = []
    container_id: str = "short"
    base_url: str | None = None
    persist_period_node_disk_usage: int | None = None


def get_mk_docker_files(conf: Mapping[str, object]) -> FileGenerator:
    config = _Config.model_validate(conf)
    if config.deployment[0] == "do_not_deploy":
        return

    yield Plugin(
        base_os=OS.LINUX,
        source=Path("mk_docker.py"),
        interval=None if (v := config.deployment[1]) is None else int(v),
    )

    yield PluginConfig(
        base_os=OS.LINUX,
        lines=list(_get_mk_docker_config(config)),
        target=Path("docker.cfg"),
        include_header=True,
    )


def _get_mk_docker_config(config: _Config) -> Iterable[str]:
    yield "[DOCKER]"
    skip_sections = list(config.node) + list(config.containers)
    if skip_sections:
        yield "skip_sections: %s" % ",".join(skip_sections)
    else:
        yield "# skip_sections: no sections skipped"

    yield "container_id: %s" % config.container_id

    if config.base_url is not None:
        yield "base_url: %s" % config.base_url

    if config.persist_period_node_disk_usage is not None:
        yield f"persist_period_node_disk_usage: {config.persist_period_node_disk_usage}"


register.bakery_plugin(
    name="mk_docker",
    files_function=get_mk_docker_files,
)
