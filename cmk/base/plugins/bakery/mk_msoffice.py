#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from json import dumps
from pathlib import Path

from cmk.utils.password_store import lookup_for_bakery

from .bakery_api.v1 import FileGenerator, OS, Plugin, PluginConfig, register


def get_mk_msoffice_files(conf: dict[str, str]) -> FileGenerator:
    yield Plugin(base_os=OS.WINDOWS, source=Path("mk_msoffice.ps1"))
    yield PluginConfig(
        base_os=OS.WINDOWS,
        lines=_get_mk_msoffice_conf_lines(conf).splitlines(),
        target=Path("msoffice_cfg.json"),
        include_header=False,
    )


def _get_mk_msoffice_conf_lines(conf: dict[str, str]) -> str:
    match conf["client_secret"]:
        case ("password", secret):
            ...  # type: ignore[unreachable]
        case ("store", pwd_id):
            secret = lookup_for_bakery(pwd_id)  # type: ignore[unreachable]
        case other:
            raise ValueError(f"Invalid password type: {other!r}")

    config_dict = {  # type: ignore[unreachable]
        "ClientId": conf["client_id"],
        "TenantId": conf["tenant_id"],
        "ClientSecret": secret,
    }

    return dumps(config_dict, indent=4)


register.bakery_plugin(
    name="mk_msoffice",
    files_function=get_mk_msoffice_files,
)
