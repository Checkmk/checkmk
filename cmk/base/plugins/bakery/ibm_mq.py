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
    only_qm: Sequence[str] = ()
    skip_qm: Sequence[str] = ()
    execute_as_another_user: str | None = None


def get_ibm_mq_files(conf: Mapping[str, object]) -> FileGenerator:
    config = _Config.model_validate(conf)
    if config.deployment[0] == "do_not_deploy":
        return

    yield Plugin(
        base_os=OS.LINUX,
        source=Path("ibm_mq"),
        interval=None if (v := config.deployment[1]) is None else int(v),
    )

    config_lines = list(_get_ibm_mq_config(config))
    if config_lines:
        yield PluginConfig(
            base_os=OS.LINUX,
            lines=config_lines,
            target=Path("ibm_mq.cfg"),
            include_header=True,
        )


def _get_ibm_mq_config(config: _Config) -> Iterable[str]:
    if config.only_qm:
        yield "ONLY_QM=%s\n" % " ".join(config.only_qm)
    if config.skip_qm:
        yield "SKIP_QM=%s\n" % " ".join(config.skip_qm)
    if config.execute_as_another_user == "mqm":
        yield "EXEC_USER=MQM"


register.bakery_plugin(
    name="ibm_mq",
    files_function=get_ibm_mq_files,
)
