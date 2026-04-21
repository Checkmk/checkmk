#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import configparser
import io
from collections.abc import Mapping
from pathlib import Path
from typing import assert_never, Literal

from pydantic import BaseModel

from cmk.utils.password_store import extract_formspec_password

from .bakery_api.v1 import FileGenerator, OS, Plugin, PluginConfig, register

_CertKeyChoices = Literal["cert_filepath", "uploaded_cert_file"]


class _TlsConfig(BaseModel):
    insecure: bool
    ca_file: str | None = None
    cert_key_file: tuple[_CertKeyChoices, str] | None = None


class _AuthConfig(BaseModel):
    auth_mechanism: Literal[
        "DEFAULT",
        "MONGODB-CR",
        "SCRAM-SHA-256",
        "SCRAM-SHA-1",
        "MONGODB-X509",
    ]
    auth_source: str
    username: str
    password: (
        tuple[Literal["cmk_postprocessed"], Literal["stored_password"], tuple[str, str]]
        | tuple[Literal["cmk_postprocessed"], Literal["explicit_password"], tuple[str, str]]
    )
    host: str | None = None
    port: int | None = None
    tls: _TlsConfig | None = None


class _Config(BaseModel):
    deployment: tuple[Literal["do_not_deploy", "sync", "cached"], float | None]
    auth: _AuthConfig | None = None


class MongoDBConfigParser(configparser.ConfigParser):
    def __init__(self) -> None:
        super().__init__()
        self["MONGODB"] = {}

    def get_lines(self) -> list[str]:
        buffer = io.StringIO()
        self.write(buffer)
        return buffer.getvalue().rstrip().split("\n")


def _update_parser_with_cert(
    parser: MongoDBConfigParser, opt_name: _CertKeyChoices, value: str
) -> FileGenerator:
    match opt_name:
        case "cert_filepath":
            parser["MONGODB"]["tls_cert_key_file"] = value
        case "uploaded_cert_file":
            parser["MONGODB"]["tls_cert_key_file"] = "/etc/check_mk/mk_mongodb.pem"
            yield PluginConfig(
                base_os=OS.LINUX,
                lines=[value],
                target=Path("mk_mongodb.pem"),
            )
        case _:
            assert_never(opt_name)


def get_mk_mongodb_files(conf: Mapping[str, object]) -> FileGenerator:
    config = _Config.model_validate(conf)
    if config.deployment[0] == "do_not_deploy":
        return

    interval = None if (v := config.deployment[1]) is None else int(v)
    yield Plugin(base_os=OS.LINUX, source=Path("mk_mongodb.py"), interval=interval)

    parser = make_config_parser(config.auth)

    if (
        config.auth is not None
        and config.auth.tls is not None
        and (ckf := config.auth.tls.cert_key_file) is not None
    ):
        yield from _update_parser_with_cert(parser, *ckf)

    yield PluginConfig(
        base_os=OS.LINUX,
        lines=parser.get_lines(),
        target=Path("mk_mongodb.cfg"),
        include_header=True,
    )


def make_config_parser(auth: _AuthConfig | None) -> MongoDBConfigParser:
    parser = MongoDBConfigParser()
    if auth is None:
        return parser

    parser["MONGODB"] = {
        "username": auth.username,
        "password": extract_formspec_password(auth.password),
        "auth_source": auth.auth_source,
        "auth_mechanism": auth.auth_mechanism,
    }
    if auth.host is not None:
        parser["MONGODB"]["host"] = auth.host
    if auth.port is not None:
        parser["MONGODB"]["port"] = str(auth.port)

    if auth.tls is not None:
        parser["MONGODB"].update(
            {
                "tls_enable": "true",
                "tls_verify": str(not auth.tls.insecure).lower(),
            }
        )
        if auth.tls.ca_file:
            parser["MONGODB"]["tls_ca_file"] = auth.tls.ca_file

    return parser


register.bakery_plugin(
    name="mk_mongodb",
    files_function=get_mk_mongodb_files,
)
