#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import copy

# pylint: disable=protected-access,redefined-outer-name
import sys

import pytest
from mock import Mock, patch
from utils import import_module

#   .--defines-------------------------------------------------------------.
#   |                      _       __ _                                    |
#   |                   __| | ___ / _(_)_ __   ___  ___                    |
#   |                  / _` |/ _ \ |_| | '_ \ / _ \/ __|                   |
#   |                 | (_| |  __/  _| | | | |  __/\__ \                   |
#   |                  \__,_|\___|_| |_|_| |_|\___||___/                   |
#   |                                                                      |
#   +----------------------------------------------------------------------+

PY_VERSION_MAJOR = sys.version_info[0]

SEP_LINUX = ":"
SEP_WINDOWS = "|"
VALID_CONFIG_WITHOUT_INSTANCE = ["# A comment", "not a comment but trash", "", "", "DBUSER=user_xy"]
VALID_CONFIG_WITH_INSTANCES = [
    "# A comment",
    "",
    "not a comment but trash",
    "DBUSER=user_yz",
    "INSTANCE=/home/postgres/db1.env{sep}USER_NAME{sep}/PATH/TO/.pgpass",
]
PG_PASSFILE = ["myhost:myport:mydb:myusr:mypw"]

#   .--tests---------------------------------------------------------------.
#   |                        _            _                                |
#   |                       | |_ ___  ___| |_ ___                          |
#   |                       | __/ _ \/ __| __/ __|                         |
#   |                       | ||  __/\__ \ |_\__ \                         |
#   |                        \__\___||___/\__|___/                         |
#   |                                                                      |
#   +----------------------------------------------------------------------+


@pytest.fixture(scope="module")
def mk_postgres():
    return import_module("mk_postgres.py")


@pytest.fixture()
def is_linux(monkeypatch, mk_postgres):
    monkeypatch.setattr(mk_postgres, "IS_WINDOWS", False)
    monkeypatch.setattr(mk_postgres, "IS_LINUX", True)
    monkeypatch.setattr(mk_postgres, "open_env_file", lambda *_args: ["export PGPORT=5432"])


@pytest.fixture()
def is_windows(monkeypatch, mk_postgres):
    monkeypatch.setattr(mk_postgres, "IS_WINDOWS", True)
    monkeypatch.setattr(mk_postgres, "IS_LINUX", False)
    monkeypatch.setattr(mk_postgres, "open_env_file", lambda *_args: ["export PGPORT=5432"])
    monkeypatch.setattr(
        mk_postgres.PostgresWin,
        "_call_wmic_logicaldisk",
        staticmethod(
            lambda: "DeviceID  \r\r\nC:        \r\r\nD:        \r\r\nH:        \r\r\nI:        \r\r\nR:        \r\r\n\r\r\n"
        ),
    )


@pytest.fixture()
def is_not_implemented_os(monkeypatch, mk_postgres):
    monkeypatch.setattr(mk_postgres, "IS_WINDOWS", False)
    monkeypatch.setattr(mk_postgres, "IS_LINUX", False)


def test_not_implemented_os(is_not_implemented_os, mk_postgres):
    with pytest.raises(Exception) as e:
        mk_postgres.get_default_path()
    assert "is not yet implemented" in str(e.value)
    with pytest.raises(Exception) as e:
        mk_postgres.get_default_postgres_user()
    assert "is not yet implemented" in str(e.value)


def test_postgres_linux_get_default_path(mk_postgres, is_linux):
    assert "/etc/check_mk" == mk_postgres.get_default_path()


def test_postgres_windows_get_default_path(mk_postgres, is_windows):
    assert "c:\\ProgramData\\checkmk\\agent\\config" == mk_postgres.get_default_path()


def test_postgres_linux_get_default_postgres_user(mk_postgres, is_linux):
    assert "postgres" == mk_postgres.get_default_postgres_user()


def test_postgres_windows_get_default_postgres_user(mk_postgres, is_windows):
    assert "postgres" == mk_postgres.get_default_postgres_user()


def test_postgres_linux_config_without_instance(mk_postgres, monkeypatch, is_linux):
    dbuser, instances = mk_postgres.parse_postgres_cfg(VALID_CONFIG_WITHOUT_INSTANCE)
    assert dbuser == "user_xy"
    assert len(instances) == 0


def test_postgres_linux_config_with_instance(mk_postgres, monkeypatch, is_linux):
    config = copy.deepcopy(VALID_CONFIG_WITH_INSTANCES)
    config[-1] = config[-1].format(sep=SEP_LINUX)
    dbuser, instances = mk_postgres.parse_postgres_cfg(config)
    assert dbuser == "user_yz"
    assert len(instances) == 1
    assert instances[0]["pg_port"] == "5432"
    assert instances[0]["name"] == "db1"
    assert instances[0]["pg_user"] == "USER_NAME"
    assert instances[0]["pg_passfile"] == "/PATH/TO/.pgpass"


def test_postgres_windows_config_with_instance(mk_postgres, monkeypatch, is_windows):
    config = copy.deepcopy(VALID_CONFIG_WITH_INSTANCES)
    config[-1] = config[-1].format(sep=SEP_WINDOWS)
    dbuser, instances = mk_postgres.parse_postgres_cfg(config)
    assert len(instances) == 1
    assert dbuser == "user_yz"
    assert instances[0]["pg_port"] == "5432"
    assert instances[0]["name"] == "db1"
    assert instances[0]["pg_user"] == "USER_NAME"
    assert instances[0]["pg_passfile"] == "/PATH/TO/.pgpass"


@patch("subprocess.Popen")
def test_postgres_factory_linux_without_instance(mock_Popen, mk_postgres, is_linux):
    process_mock = Mock()
    attrs = {
        "communicate.side_effect": [
            ("/usr/lib/postgres/psql", None),
            ("postgres\ndb1", None),
            ("12.3", None),
        ]
    }
    process_mock.configure_mock(**attrs)
    mock_Popen.return_value = process_mock
    instance = {
        "name": "main",
        "pg_user": "postgres",
        "pg_database": "postgres",
        "pg_port": "5432",
        "pg_passfile": "",
    }
    myPostgresOnLinux = mk_postgres.postgres_factory("postgres", instance)

    assert isinstance(myPostgresOnLinux, mk_postgres.PostgresLinux)
    assert myPostgresOnLinux.psql == "psql"
    assert myPostgresOnLinux.bin_path == "/usr/lib/postgres/"
    assert myPostgresOnLinux.get_databases() == ["postgres", "db1"]
    assert myPostgresOnLinux.get_server_version() == 12.3
    assert myPostgresOnLinux.pg_database == "postgres"
    assert myPostgresOnLinux.pg_port == "5432"


@patch("os.path.isfile", return_value=True)
@patch("subprocess.Popen")
def test_postgres_factory_win_without_instance(mock_Popen, mock_isfile, mk_postgres, is_windows):
    process_mock = Mock()
    attrs = {"communicate.side_effect": [(b"postgres\ndb1", b"ok"), (b"12.1", b"ok")]}
    process_mock.configure_mock(**attrs)
    mock_Popen.return_value = process_mock
    instance = {
        "pg_port": "5432",
        "pg_database": "postgres",
        "name": "data",
        "pg_user": "myuser",
        "pg_passfile": "/home/.pgpass",
    }
    myPostgresOnWin = mk_postgres.postgres_factory("postgres", instance)

    mock_isfile.assert_called_with("C:\\Program Files\\PostgreSQL\\12\\bin\\psql.exe")
    assert isinstance(myPostgresOnWin, mk_postgres.PostgresWin)
    assert myPostgresOnWin.psql == "C:\\Program Files\\PostgreSQL\\12\\bin\\psql.exe"
    assert myPostgresOnWin.bin_path == "C:\\Program Files\\PostgreSQL\\12\\bin"
    assert myPostgresOnWin.get_databases() == ["postgres", "db1"]
    assert myPostgresOnWin.get_server_version() == 12.1
    assert myPostgresOnWin.pg_database == "postgres"
    assert myPostgresOnWin.pg_port == "5432"


@patch("subprocess.Popen")
def test_postgres_factory_linux_with_instance(mock_Popen, monkeypatch, mk_postgres, is_linux):
    instance = {
        "pg_database": "mydb",
        "pg_port": "1234",
        "name": "mydb",
        "pg_user": "myuser",
        "pg_passfile": "/home/.pgpass",
    }
    process_mock = Mock()
    attrs = {
        "communicate.side_effect": [
            ("/usr/lib/postgres/psql", None),
            ("postgres\ndb1", None),
            ("12.3.6", None),
        ]
    }
    process_mock.configure_mock(**attrs)
    mock_Popen.return_value = process_mock
    myPostgresOnLinux = mk_postgres.postgres_factory("postgres", instance)

    assert isinstance(myPostgresOnLinux, mk_postgres.PostgresLinux)
    assert myPostgresOnLinux.psql == "psql"
    assert myPostgresOnLinux.bin_path == "/usr/lib/postgres/"
    assert myPostgresOnLinux.get_databases() == ["postgres", "db1"]
    assert myPostgresOnLinux.get_server_version() == 12.3
    assert myPostgresOnLinux.pg_database == "mydb"
    assert myPostgresOnLinux.pg_port == "1234"
    assert myPostgresOnLinux.pg_user == "myuser"
    assert myPostgresOnLinux.my_env["PGPASSFILE"] == "/home/.pgpass"
    assert myPostgresOnLinux.name == "mydb"


@patch("os.path.isfile", return_value=True)
@patch("subprocess.Popen")
def test_postgres_factory_windows_with_instance(
    mock_Popen,
    mock_isfile,
    monkeypatch,
    mk_postgres,
    is_windows,
):
    instance = {
        "pg_database": "mydb",
        "pg_port": "1234",
        "name": "mydb",
        "pg_user": "myuser",
        "pg_passfile": "c:\\User\\.pgpass",
    }
    process_mock = Mock()
    attrs = {"communicate.side_effect": [(b"postgres\ndb1", b"ok"), (b"12.1.5", b"ok")]}
    process_mock.configure_mock(**attrs)
    mock_Popen.return_value = process_mock

    myPostgresOnWin = mk_postgres.postgres_factory("postgres", instance)

    mock_isfile.assert_called_with("C:\\Program Files\\PostgreSQL\\12\\bin\\psql.exe")
    assert isinstance(myPostgresOnWin, mk_postgres.PostgresWin)
    assert myPostgresOnWin.psql == "C:\\Program Files\\PostgreSQL\\12\\bin\\psql.exe"
    assert myPostgresOnWin.bin_path == "C:\\Program Files\\PostgreSQL\\12\\bin"
    assert myPostgresOnWin.get_databases() == ["postgres", "db1"]
    assert myPostgresOnWin.get_server_version() == 12.1
    assert myPostgresOnWin.pg_database == "mydb"
    assert myPostgresOnWin.pg_port == "1234"
    assert myPostgresOnWin.pg_user == "myuser"
    assert myPostgresOnWin.my_env["PGPASSFILE"] == "c:\\User\\.pgpass"
    assert myPostgresOnWin.name == "mydb"
