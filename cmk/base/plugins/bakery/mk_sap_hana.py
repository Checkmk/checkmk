#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Iterator, Mapping
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from .bakery_api.v1 import FileGenerator, OS, password_store, Plugin, PluginConfig, register

_UserAndPwd = tuple[str, password_store.PasswordId]


class _Conf(BaseModel):
    credentials: _UserAndPwd | str | list[tuple[str, str, str, _UserAndPwd | str]]
    credentials_sap_connect: _UserAndPwd | None = None
    runas: Literal["instance", "agent"] | None = None


def get_mk_sap_hana_files(conf: Mapping[str, object]) -> FileGenerator:
    config = _Conf.model_validate(conf)
    yield Plugin(base_os=OS.LINUX, source=Path("mk_sap_hana"))

    yield PluginConfig(
        base_os=OS.LINUX,
        lines=list(_get_mk_sap_hana_config(config)),
        target=Path("sap_hana.cfg"),
        include_header=True,
    )


def _get_mk_sap_hana_config(config: _Conf) -> Iterator[str]:
    match config.credentials:
        case list() as credentials:
            yield _get_sap_hana_databases(credentials)
        case str(credentials):
            yield f"USERSTOREKEY={credentials}"
        case credentials:
            yield from _user_and_pwd_lines(credentials)

    if (csc := config.credentials_sap_connect) is not None:
        yield from _user_and_pwd_lines(csc, suffix="_CONNECT")

    if config.runas is not None:
        yield f"RUNAS={config.runas}"


def _user_and_pwd_lines(
    credentials: _UserAndPwd,
    *,
    suffix: Literal["", "_CONNECT"] = "",
) -> tuple[str, str]:
    user, indiv_or_stored_pwd = credentials
    pwd = password_store.extract(indiv_or_stored_pwd)
    return (f"USER{suffix}={user}", f"PASSWORD{suffix}={pwd}")


def _database_credential_fields(credentials: _UserAndPwd | str) -> tuple[str, str, str]:
    """Return (user, password, userstorekey)"""
    match credentials:
        case (user, indiv_or_stored_pwd):
            return user, password_store.extract(indiv_or_stored_pwd), ""
        case str(key):
            return "", "", key


def _get_sap_hana_databases(db_conf: Iterable[tuple[str, str, str, _UserAndPwd | str]]) -> str:
    entries = []
    for sid, instance, db_name, credentials in db_conf:
        user, password, userstorekey = _database_credential_fields(credentials)
        entries.append(f"{sid},{instance},{db_name},{user},{password},{userstorekey}")

    return "DBS=({})".format(" ".join(entries))


register.bakery_plugin(
    name="mk_sap_hana",
    files_function=get_mk_sap_hana_files,
)
