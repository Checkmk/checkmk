#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable
from pathlib import Path

from pydantic import BaseModel

from cmk.bakery.v2_alpha import BakeryPlugin, OS, Plugin, PluginConfig


class CephConfig(BaseModel):
    deploy: bool
    interval: tuple[object, float | None]
    config: str | None = None
    client: str | None = None


def get_ceph_files(confm: CephConfig) -> Iterable[Plugin | PluginConfig]:
    if not confm.deploy:
        return

    yield Plugin(
        base_os=OS.LINUX,
        source=Path("mk_ceph.py"),
        interval=None if (f_inv := confm.interval[1]) is None else round(f_inv),
    )

    config_lines = []
    if confm.config:
        config_lines.append(f"CONFIG={confm.config}")
    if confm.client:
        config_lines.append(f"CLIENT={confm.client}")
    if config_lines:
        yield PluginConfig(
            base_os=OS.LINUX, lines=config_lines, target=Path("ceph.cfg"), include_header=True
        )


bakery_plugin_ceph = BakeryPlugin(
    name="ceph",
    parameter_parser=CephConfig.model_validate,
    files_function=get_ceph_files,
)
