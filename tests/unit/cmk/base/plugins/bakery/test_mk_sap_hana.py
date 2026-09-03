#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from cmk.bakery.v1 import OS, Plugin, PluginConfig
from cmk.base.plugins.bakery.mk_sap_hana import get_mk_sap_hana_files


def _password(secret: str) -> tuple[str, str, tuple[str, str]]:
    return ("cmk_postprocessed", "explicit_password", ("uuid-1", secret))


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
    conf = {
        "deployment": ("sync", None),
        "credentials": ("user_password", {"user": "peter", "password": _password("abc123")}),
        "credentials_sap_connect": ("none", None),
    }
    assert sorted(get_mk_sap_hana_files(conf), key=repr) == _expected(
        ["USER=peter", "PASSWORD=abc123"]
    )


def test_mk_sap_hana_files_userstorekey() -> None:
    conf = {
        "deployment": ("sync", None),
        "credentials": ("userstorekey", "storekey"),
        "credentials_sap_connect": ("none", None),
    }
    assert sorted(get_mk_sap_hana_files(conf), key=repr) == _expected(["USERSTOREKEY=storekey"])


def test_mk_sap_hana_files_userstorekey_with_runas_agent() -> None:
    conf = {
        "deployment": ("sync", None),
        "credentials": ("userstorekey", "storekey"),
        "credentials_sap_connect": ("none", None),
        "runas": "agent",
    }
    assert sorted(get_mk_sap_hana_files(conf), key=repr) == _expected(
        ["USERSTOREKEY=storekey", "RUNAS=agent"]
    )


def test_mk_sap_hana_files_with_runas_instance() -> None:
    conf = {
        "deployment": ("sync", None),
        "credentials": ("user_password", {"user": "admin", "password": _password("secret")}),
        "credentials_sap_connect": ("none", None),
        "runas": "instance",
    }
    assert sorted(get_mk_sap_hana_files(conf), key=repr) == _expected(
        ["USER=admin", "PASSWORD=secret", "RUNAS=instance"]
    )


def test_mk_sap_hana_files_databases() -> None:
    conf = {
        "deployment": ("sync", None),
        "credentials": (
            "databases",
            [
                {
                    "sid": "sid1",
                    "instance": "inst1",
                    "database": "db1",
                    "credentials": (
                        "user_password",
                        {"user": "usr1", "password": _password("pw1")},
                    ),
                },
                {
                    "sid": "sid2",
                    "instance": "inst2",
                    "database": "db2",
                    "credentials": ("userstorekey", "storekey2"),
                },
            ],
        ),
        "credentials_sap_connect": (
            "credentials",
            {"user": "peter", "password": _password("abc123")},
        ),
    }
    assert sorted(get_mk_sap_hana_files(conf), key=repr) == _expected(
        [
            "DBS=(sid1,inst1,db1,usr1,pw1, sid2,inst2,db2,,,storekey2)",
            "USER_CONNECT=peter",
            "PASSWORD_CONNECT=abc123",
        ]
    )


def test_mk_sap_hana_files_do_not_deploy() -> None:
    assert list(get_mk_sap_hana_files({"deployment": ("do_not_deploy", None)})) == []
