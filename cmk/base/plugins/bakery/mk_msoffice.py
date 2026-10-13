#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from json import dumps
from pathlib import Path

from cmk.utils.password_store import lookup_for_bakery

from .bakery_api.v1 import FileGenerator, OS, Plugin, PluginConfig, register


def get_mk_msoffice_files(conf: Mapping[str, object]) -> FileGenerator:
    yield Plugin(base_os=OS.WINDOWS, source=Path("mk_msoffice.ps1"))
    yield PluginConfig(
        base_os=OS.WINDOWS,
        lines=dumps(
            {
                "ClientId": conf["client_id"],
                "TenantId": conf["tenant_id"],
                "ClientSecret": _client_secret(conf["client_secret"]),
            },
            indent=4,
        ).splitlines(),
        target=Path("msoffice_cfg.json"),
        include_header=False,
    )


def _client_secret(value: object) -> str:
    match value:
        case ("password", str(secret)):
            return secret
        case ("store", str(pwd_id)):
            return lookup_for_bakery(pwd_id)
        case other:
            raise ValueError(f"Invalid password type: {other!r}")


register.bakery_plugin(
    name="mk_msoffice",
    files_function=get_mk_msoffice_files,
)
