#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from cmk.bakery.v1 import OS, Plugin, PluginConfig
from cmk.base.plugins.bakery.mk_sap_hana import get_mk_sap_hana_files


def _expected(lines: list[str]) -> list[object]:
    return sorted(
        [
            Plugin(base_os=OS.LINUX, source=Path("mk_sap_hana")),
            PluginConfig(
                base_os=OS.LINUX,
                lines=lines,
                target=Path("sap_hana.cfg"),
                include_header=True,
            ),
        ],
        key=repr,
    )


def test_mk_sap_hana_files_user_password() -> None:
    conf = {"credentials": ("peter", ("password", "abc123"))}
    assert sorted(get_mk_sap_hana_files(conf), key=repr) == _expected(
        ["USER=peter", "PASSWORD=abc123"]
    )


def test_mk_sap_hana_files_userstorekey() -> None:
    conf = {"credentials": "storekey"}
    assert sorted(get_mk_sap_hana_files(conf), key=repr) == _expected(["USERSTOREKEY=storekey"])


def test_mk_sap_hana_files_userstorekey_with_runas() -> None:
    conf = {"credentials": "storekey", "runas": "agent"}
    assert sorted(get_mk_sap_hana_files(conf), key=repr) == _expected(
        ["USERSTOREKEY=storekey", "RUNAS=agent"]
    )


def test_mk_sap_hana_files_databases() -> None:
    conf = {
        "credentials": [
            ("sid1", "inst1", "db1", ("usr1", ("password", "pw1"))),
            ("sid2", "inst2", "db2", "storekey2"),
        ],
        "credentials_sap_connect": ("peter", ("password", "abc123")),
    }
    assert sorted(get_mk_sap_hana_files(conf), key=repr) == _expected(
        [
            "DBS=(sid1,inst1,db1,usr1,pw1, sid2,inst2,db2,,,storekey2)",
            "USER_CONNECT=peter",
            "PASSWORD_CONNECT=abc123",
        ]
    )


def test_mk_sap_hana_files_with_runas_instance() -> None:
    conf = {"credentials": ("admin", ("password", "secret")), "runas": "instance"}
    assert sorted(get_mk_sap_hana_files(conf), key=repr) == _expected(
        ["USER=admin", "PASSWORD=secret", "RUNAS=instance"]
    )
