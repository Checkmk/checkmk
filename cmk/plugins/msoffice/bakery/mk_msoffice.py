#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from json import dumps
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from cmk.bakery.v2 import BakeryPlugin, FileGenerator, OS, Plugin, PluginConfig, Secret


class _Config(BaseModel):
    deployment: tuple[Literal["do_not_deploy", "sync"], None]
    client_id: str = ""
    tenant_id: str = ""
    client_secret: Secret | None = None


def get_mk_msoffice_files(config: _Config) -> FileGenerator:
    if config.deployment[0] == "do_not_deploy":
        return

    yield Plugin(base_os=OS.WINDOWS, source=Path("mk_msoffice.ps1"))
    yield PluginConfig(
        base_os=OS.WINDOWS,
        lines=dumps(
            {
                "ClientId": config.client_id,
                "TenantId": config.tenant_id,
                "ClientSecret": (
                    "" if config.client_secret is None else config.client_secret.revealed
                ),
            },
            indent=4,
        ).splitlines(),
        target=Path("msoffice_cfg.json"),
        include_header=False,
    )


bakery_plugin_mk_msoffice = BakeryPlugin(
    name="mk_msoffice",
    parameter_parser=_Config.model_validate,
    default_parameters=None,
    files_function=get_mk_msoffice_files,
)
