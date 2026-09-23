#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator, Mapping, Sequence
from pathlib import Path
from typing import Literal, NamedTuple

from pydantic import BaseModel

from .bakery_api.v1 import FileGenerator, OS, password_store, Plugin, PluginConfig, register


class _UserAndPassword(NamedTuple):
    user: str
    password: password_store.PasswordId


class _Database(NamedTuple):
    sid: str
    instance: str
    database: str
    credentials: _UserAndPassword | str


class _Config(BaseModel):
    credentials: _UserAndPassword | str | list[_Database]
    credentials_sap_connect: _UserAndPassword | None = None
    runas: Literal["instance", "agent"] | None = None


def get_mk_sap_hana_files(conf: Mapping[str, object]) -> FileGenerator:
    config = _Config.model_validate(conf)
    yield Plugin(base_os=OS.LINUX, source=Path("mk_sap_hana"))

    yield PluginConfig(
        base_os=OS.LINUX,
        lines=list(_get_mk_sap_hana_config(config)),
        target=Path("sap_hana.cfg"),
        include_header=True,
    )


def _get_mk_sap_hana_config(config: _Config) -> Iterator[str]:
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
    credentials: _UserAndPassword,
    *,
    suffix: Literal["", "_CONNECT"] = "",
) -> tuple[str, str]:
    return (
        f"USER{suffix}={credentials.user}",
        f"PASSWORD{suffix}={password_store.extract(credentials.password)}",
    )


def _database_credential_fields(credentials: _UserAndPassword | str) -> tuple[str, str, str]:
    """Return (user, password, userstorekey)"""
    match credentials:
        case _UserAndPassword():
            return credentials.user, password_store.extract(credentials.password), ""
        case str(key):
            return "", "", key


def _get_sap_hana_databases(databases: Sequence[_Database]) -> str:
    entries = []
    for db in databases:
        user, password, userstorekey = _database_credential_fields(db.credentials)
        entries.append(f"{db.sid},{db.instance},{db.database},{user},{password},{userstorekey}")

    return "DBS=({})".format(" ".join(entries))


register.bakery_plugin(
    name="mk_sap_hana",
    files_function=get_mk_sap_hana_files,
)
