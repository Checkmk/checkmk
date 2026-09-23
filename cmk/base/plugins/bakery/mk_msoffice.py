#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from json import dumps
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from cmk.utils.password_store import lookup_for_bakery

from .bakery_api.v1 import FileGenerator, OS, Plugin, PluginConfig, register


class _Config(BaseModel):
    client_id: str
    tenant_id: str
    client_secret: tuple[Literal["password", "store"], str]


def get_mk_msoffice_files(conf: Mapping[str, object]) -> FileGenerator:
    config = _Config.model_validate(conf)
    yield Plugin(base_os=OS.WINDOWS, source=Path("mk_msoffice.ps1"))
    yield PluginConfig(
        base_os=OS.WINDOWS,
        lines=dumps(
            {
                "ClientId": config.client_id,
                "TenantId": config.tenant_id,
                "ClientSecret": _client_secret(config.client_secret),
            },
            indent=4,
        ).splitlines(),
        target=Path("msoffice_cfg.json"),
        include_header=False,
    )


def _client_secret(value: tuple[Literal["password", "store"], str]) -> str:
    kind, secret_or_id = value
    return lookup_for_bakery(secret_or_id) if kind == "store" else secret_or_id


register.bakery_plugin(
    name="mk_msoffice",
    files_function=get_mk_msoffice_files,
)
