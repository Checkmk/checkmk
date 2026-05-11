#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from pathlib import Path

import pytest

from cmk.bakery.v2_unstable import OS, Plugin, PluginConfig, Secret
from cmk.plugins.mongodb.bakery.mk_mongodb import (
    _AuthConfig,
    _TlsConfig,
    bakery_plugin_mk_mongodb,
    make_config_parser,
)

_PASSWORD = Secret("mdbpwd", "explicit_password", "uuid-1")

mk_mongodb_conf_uploaded_cert_file = {
    "deployment": ("sync", None),
    "auth": {
        "host": "some_host",
        "auth_mechanism": "MONGODB-X509",
        "tls": {
            "insecure": False,
            "cert_key_file": ("uploaded_cert_file", "some_cert_file_content"),
        },
        "auth_source": "admin",
        "username": "mongodb_username",
        "password": _PASSWORD,
    },
}

mk_mongodb_lines_uploaded_cert_file = [
    "[MONGODB]",
    "username = mongodb_username",
    "password = mdbpwd",
    "auth_source = admin",
    "auth_mechanism = MONGODB-X509",
    "host = some_host",
    "tls_enable = true",
    "tls_verify = true",
    "tls_cert_key_file = /etc/check_mk/mk_mongodb.pem",
]


@pytest.mark.parametrize(
    ["auth", "expected_result"],
    [
        (
            None,
            ["[MONGODB]"],
        ),
        (
            _AuthConfig(
                auth_mechanism="DEFAULT",
                tls=_TlsConfig(insecure=True),
                auth_source="admin",
                username="mongodb_username",
                password=_PASSWORD,
            ),
            [
                "[MONGODB]",
                "username = mongodb_username",
                "password = mdbpwd",
                "auth_source = admin",
                "auth_mechanism = DEFAULT",
                "tls_enable = true",
                "tls_verify = false",
            ],
        ),
        (
            _AuthConfig(
                host="some_host",
                auth_mechanism="SCRAM-SHA-256",
                tls=_TlsConfig(insecure=False, ca_file="/some/path.pem"),
                auth_source="admin",
                username="mongodb_username",
                password=_PASSWORD,
            ),
            [
                "[MONGODB]",
                "username = mongodb_username",
                "password = mdbpwd",
                "auth_source = admin",
                "auth_mechanism = SCRAM-SHA-256",
                "host = some_host",
                "tls_enable = true",
                "tls_verify = true",
                "tls_ca_file = /some/path.pem",
            ],
        ),
        (
            _AuthConfig(
                auth_mechanism="MONGODB-CR",
                auth_source="admin",
                username="mongodb_username",
                password=_PASSWORD,
            ),
            [
                "[MONGODB]",
                "username = mongodb_username",
                "password = mdbpwd",
                "auth_source = admin",
                "auth_mechanism = MONGODB-CR",
            ],
        ),
        (
            _AuthConfig(
                host="some_host",
                auth_mechanism="SCRAM-SHA-256",
                port=27017,
                auth_source="admin",
                username="mongodb_username",
                password=_PASSWORD,
            ),
            [
                "[MONGODB]",
                "username = mongodb_username",
                "password = mdbpwd",
                "auth_source = admin",
                "auth_mechanism = SCRAM-SHA-256",
                "host = some_host",
                "port = 27017",
            ],
        ),
        (
            _AuthConfig(
                host="some_host",
                auth_mechanism="MONGODB-X509",
                tls=_TlsConfig(insecure=False, cert_key_file=("cert_filepath", "/some/path.pem")),
                auth_source="admin",
                username="mongodb_username",
                password=_PASSWORD,
            ),
            [
                "[MONGODB]",
                "username = mongodb_username",
                "password = mdbpwd",
                "auth_source = admin",
                "auth_mechanism = MONGODB-X509",
                "host = some_host",
                "tls_enable = true",
                "tls_verify = true",
            ],
        ),
        (
            _AuthConfig(
                host="some_host",
                auth_mechanism="MONGODB-X509",
                tls=_TlsConfig(
                    insecure=False,
                    cert_key_file=("uploaded_cert_file", "some_cert_file_content"),
                ),
                auth_source="admin",
                username="mongodb_username",
                password=_PASSWORD,
            ),
            [
                "[MONGODB]",
                "username = mongodb_username",
                "password = mdbpwd",
                "auth_source = admin",
                "auth_mechanism = MONGODB-X509",
                "host = some_host",
                "tls_enable = true",
                "tls_verify = true",
            ],
        ),
    ],
    ids=[
        "no_auth",
        "tls_enabled_and_insecure",
        "tls_enabled_and_secure",
        "no_tls",
        "port_is_defined",
        "cert_key_file_path_defined",
        "cert_key_file_uploaded",
    ],
)
def test_make_config_parser(auth: _AuthConfig | None, expected_result: list[str]) -> None:
    assert make_config_parser(auth).get_lines() == expected_result


@pytest.mark.parametrize(
    "conf, expected_files",
    [
        (
            mk_mongodb_conf_uploaded_cert_file,
            [
                Plugin(base_os=OS.LINUX, source=Path("mk_mongodb.py"), interval=None),
                PluginConfig(
                    base_os=OS.LINUX,
                    lines=["some_cert_file_content"],
                    target=Path("mk_mongodb.pem"),
                ),
                PluginConfig(
                    base_os=OS.LINUX,
                    lines=mk_mongodb_lines_uploaded_cert_file,
                    target=Path("mk_mongodb.cfg"),
                    include_header=True,
                ),
            ],
        ),
        (
            {"deployment": ("sync", None)},
            [
                Plugin(base_os=OS.LINUX, source=Path("mk_mongodb.py"), interval=None),
                PluginConfig(
                    base_os=OS.LINUX,
                    lines=["[MONGODB]"],
                    target=Path("mk_mongodb.cfg"),
                    include_header=True,
                ),
            ],
        ),
        (
            {"deployment": ("do_not_deploy", None)},
            [],
        ),
    ],
)
def test_mk_mongodb_files(
    conf: dict[str, object],
    expected_files: list[Plugin | PluginConfig],
) -> None:
    parsed = bakery_plugin_mk_mongodb.parameter_parser(conf)
    result = list(bakery_plugin_mk_mongodb.files_function(parsed))
    assert result == expected_files
