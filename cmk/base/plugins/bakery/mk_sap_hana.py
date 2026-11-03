#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator, Mapping, Sequence
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from cmk.utils.password_store import extract_formspec_password, FormSpecPassword

from .bakery_api.v1 import FileGenerator, OS, Plugin, PluginConfig, register


class _UserAndPassword(BaseModel):
    user: str
    password: FormSpecPassword


_SingleCredentials = (
    tuple[Literal["user_password"], _UserAndPassword] | tuple[Literal["userstorekey"], str]
)


class _Database(BaseModel):
    sid: str
    instance: str
    database: str
    credentials: _SingleCredentials


_Credentials = _SingleCredentials | tuple[Literal["databases"], Sequence[_Database]]


class _Config(BaseModel):
    deployment: tuple[Literal["do_not_deploy"], None] | tuple[Literal["sync"], _Credentials]
    credentials_sap_connect: (
        tuple[Literal["none"], None] | tuple[Literal["credentials"], _UserAndPassword]
    ) = ("none", None)
    runas: Literal["instance", "agent"] | None = None


def get_mk_sap_hana_files(conf: Mapping[str, object]) -> FileGenerator:
    config = _Config.model_validate(conf)
    match config.deployment:
        case ("do_not_deploy", _):
            return
        case ("sync", credentials):
            yield Plugin(
                base_os=OS.LINUX,
                source=Path("mk_sap_hana"),
            )
            yield PluginConfig(
                base_os=OS.LINUX,
                lines=list(_get_mk_sap_hana_config(credentials, config)),
                target=Path("sap_hana.cfg"),
                include_header=True,
            )


def _get_mk_sap_hana_config(credentials: _Credentials, config: _Config) -> Iterator[str]:
    match credentials:
        case ("databases", databases):
            yield _get_sap_hana_databases(databases)
        case ("userstorekey", key):
            yield f"USERSTOREKEY={key}"
        case ("user_password", user_and_password):
            yield from _user_and_pwd_lines(user_and_password)

    match config.credentials_sap_connect:
        case ("credentials", csc):
            yield from _user_and_pwd_lines(csc, suffix="_CONNECT")
        case ("none", _):
            pass

    if config.runas is not None:
        yield f"RUNAS={config.runas}"


def _user_and_pwd_lines(
    credentials: _UserAndPassword,
    *,
    suffix: Literal["", "_CONNECT"] = "",
) -> tuple[str, str]:
    return (
        f"USER{suffix}={credentials.user}",
        f"PASSWORD{suffix}={extract_formspec_password(credentials.password)}",
    )


def _database_credential_fields(credentials: _SingleCredentials) -> tuple[str, str, str]:
    """Return (user, password, userstorekey)"""
    match credentials:
        case ("user_password", user_and_password):
            return (
                user_and_password.user,
                extract_formspec_password(user_and_password.password),
                "",
            )
        case ("userstorekey", key):
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
