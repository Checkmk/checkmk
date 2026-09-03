#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from json import dumps
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from cmk.utils.password_store import extract_formspec_password, FormSpecPassword

from .bakery_api.v1 import FileGenerator, OS, Plugin, PluginConfig, register


class _Config(BaseModel):
    deployment: tuple[Literal["do_not_deploy", "sync"], None]
    client_id: str = ""
    tenant_id: str = ""
    client_secret: FormSpecPassword | None = None


def get_mk_msoffice_files(conf: Mapping[str, object]) -> FileGenerator:
    config = _Config.model_validate(conf)
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
                    ""
                    if config.client_secret is None
                    else extract_formspec_password(config.client_secret)
                ),
            },
            indent=4,
        ).splitlines(),
        target=Path("msoffice_cfg.json"),
        include_header=False,
    )


register.bakery_plugin(
    name="mk_msoffice",
    files_function=get_mk_msoffice_files,
)
