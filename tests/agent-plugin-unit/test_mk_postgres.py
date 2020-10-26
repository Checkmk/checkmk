#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access,redefined-outer-name
import sys
import copy
import pytest  # type: ignore[import]
from mock import patch, Mock
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
    "# A comment", "", "not a comment but trash", "DBUSER=user_yz",
    "INSTANCE=/home/postgres/db1.env{sep}USER_NAME{sep}/PATH/TO/.pgpass"
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
    monkeypatch.setattr(mk_postgres, 'IS_WINDOWS', False)
    monkeypatch.setattr(mk_postgres, 'IS_LINUX', True)


@pytest.fixture()
def is_windows(monkeypatch, mk_postgres):
    monkeypatch.setattr(mk_postgres, 'IS_WINDOWS', True)
    monkeypatch.setattr(mk_postgres, 'IS_LINUX', False)


def test_postgres_linux_config_without_instance(mk_postgres, monkeypatch, is_linux):

    monkeypatch.setattr(mk_postgres, "open_wrapper", lambda *_args: VALID_CONFIG_WITHOUT_INSTANCE)
    config = mk_postgres.PostgresConfig()
    assert len(config.instances) == 0
    assert config.dbuser == "user_xy"


def test_postgres_linux_config_with_instance(mk_postgres, monkeypatch, is_linux):
    config = copy.deepcopy(VALID_CONFIG_WITH_INSTANCES)
    config[-1] = config[-1].format(sep=SEP_LINUX)
    monkeypatch.setattr(mk_postgres, "open_wrapper", lambda *_args: config)

    pgconfig = mk_postgres.PostgresConfig()
    assert len(pgconfig.instances) == 1
    assert pgconfig.dbuser == "user_yz"
    assert pgconfig.instances[0]["env_file"] == "/home/postgres/db1.env"
    assert pgconfig.instances[0]["name"] == "db1"
    assert pgconfig.instances[0]["pg_user"] == "USER_NAME"
    assert pgconfig.instances[0]["pg_passfile"] == "/PATH/TO/.pgpass"


def test_postgres_windows_config_with_instance(mk_postgres, monkeypatch, is_windows):
    config = copy.deepcopy(VALID_CONFIG_WITH_INSTANCES)
    config[-1] = config[-1].format(sep=SEP_WINDOWS)
    monkeypatch.setattr(mk_postgres, "open_wrapper", lambda *_args: config)
    pgconfig = mk_postgres.PostgresConfig()
    assert len(pgconfig.instances) == 1
    assert pgconfig.dbuser == "user_yz"
    assert pgconfig.instances[0]["env_file"] == "/home/postgres/db1.env"
    assert pgconfig.instances[0]["name"] == "db1"
    assert pgconfig.instances[0]["pg_user"] == "USER_NAME"
    assert pgconfig.instances[0]["pg_passfile"] == "/PATH/TO/.pgpass"


@patch('subprocess.Popen')
def test_postgres_factory_linux_without_instance(mock_Popen, mk_postgres, is_linux):
    process_mock = Mock()
    attrs = {
        'communicate.side_effect': [('/usr/lib/postgres/psql', None), ('postgres\ndb1', None),
                                    ('12.3', None)]
    }
    process_mock.configure_mock(**attrs)
    mock_Popen.return_value = process_mock
    myPostgresOnLinux = mk_postgres.postgres_factory("postgres")

    assert isinstance(myPostgresOnLinux, mk_postgres.PostgresLinux)
    assert myPostgresOnLinux.psql == "psql"
    assert myPostgresOnLinux.bin_path == "/usr/lib/postgres/"
    assert myPostgresOnLinux.databases == ["postgres", "db1"]
    assert myPostgresOnLinux.numeric_version == 12.3
    assert myPostgresOnLinux.instance == {"pg_database": "postgres", "pg_port": "5432"}


@patch('os.path.isfile', return_value=True)
@patch('subprocess.Popen')
def test_postgres_factory_win_without_instance(mock_Popen, mock_isfile, mk_postgres, is_windows):
    process_mock = Mock()
    attrs = {'communicate.side_effect': [(b'postgres\ndb1', b'ok'), (b'12.1', b'ok')]}
    process_mock.configure_mock(**attrs)
    mock_Popen.return_value = process_mock
    myPostgresOnWin = mk_postgres.postgres_factory("postgres")

    mock_isfile.assert_called_with('C:\\Program Files\\PostgreSQL\\12\\bin\\psql.exe')
    assert isinstance(myPostgresOnWin, mk_postgres.PostgresWin)
    assert myPostgresOnWin.psql == "C:\\Program Files\\PostgreSQL\\12\\bin\\psql.exe"
    assert myPostgresOnWin.bin_path == "C:\\Program Files\\PostgreSQL\\12\\bin"
    assert myPostgresOnWin.databases == ["postgres", "db1"]
    assert myPostgresOnWin.numeric_version == 12.1
    assert myPostgresOnWin.instance == {"pg_database": "postgres", "pg_port": "5432"}


@patch('subprocess.Popen')
def test_postgres_factory_linux_with_instance(mock_Popen, monkeypatch, mk_postgres, is_linux):
    instance = {
        'env_file': '/home/postgres/mydb.env',
        'name': 'mydb',
        'pg_user': 'myuser',
        'pg_passfile': '/home/.pgpass',
    }
    process_mock = Mock()
    attrs = {
        'communicate.side_effect': [
            ('/usr/lib/postgres/psql', None),
            ('postgres\ndb1', None),
            ('12.3.6', None),
        ]
    }
    process_mock.configure_mock(**attrs)
    mock_Popen.return_value = process_mock

    monkeypatch.setattr(mk_postgres, "open_wrapper", lambda *_args: [
        "export PGDATABASE=mydb",
        "export PGPORT=1234",
    ])

    myPostgresOnLinux = mk_postgres.postgres_factory("postgres", instance)

    assert isinstance(myPostgresOnLinux, mk_postgres.PostgresLinux)
    assert myPostgresOnLinux.psql == "psql"
    assert myPostgresOnLinux.bin_path == "/usr/lib/postgres/"
    assert myPostgresOnLinux.databases == ["postgres", "db1"]
    assert myPostgresOnLinux.numeric_version == 12.3
    assert myPostgresOnLinux.instance == {
        "pg_database": "mydb",
        "pg_port": "1234",
        "pg_user": "myuser",
        "pg_passfile": "/home/.pgpass",
        "name": "mydb",
        "env_file": "/home/postgres/mydb.env",
    }


@patch('os.path.isfile', return_value=True)
@patch('subprocess.Popen')
def test_postgres_factory_windows_with_instance(
    mock_Popen,
    mock_isfile,
    monkeypatch,
    mk_postgres,
    is_windows,
):
    instance = {
        'env_file': 'c:\\User\\mydb.env',
        'name': 'mydb',
        'pg_user': 'myuser',
        'pg_passfile': 'c:\\User\\.pgpass',
    }
    process_mock = Mock()
    attrs = {'communicate.side_effect': [(b'postgres\ndb1', b'ok'), (b'12.1.5', b'ok')]}
    process_mock.configure_mock(**attrs)
    mock_Popen.return_value = process_mock

    monkeypatch.setattr(mk_postgres, "open_wrapper", lambda *_args: [
        "@SET PGDATABASE=mydb",
        "@SET PGPORT=1234",
    ])

    myPostgresOnWindows = mk_postgres.postgres_factory("postgres", instance)

    mock_isfile.assert_called_with('C:\\Program Files\\PostgreSQL\\12\\bin\\psql.exe')
    assert isinstance(myPostgresOnWindows, mk_postgres.PostgresWin)
    assert myPostgresOnWindows.psql == "C:\\Program Files\\PostgreSQL\\12\\bin\\psql.exe"
    assert myPostgresOnWindows.bin_path == "C:\\Program Files\\PostgreSQL\\12\\bin"
    assert myPostgresOnWindows.databases == ["postgres", "db1"]
    assert myPostgresOnWindows.numeric_version == 12.1
    assert myPostgresOnWindows.instance == {
        "pg_database": "mydb",
        "pg_port": "1234",
        "pg_user": "myuser",
        "pg_passfile": "c:\\User\\.pgpass",
        "name": "mydb",
        "env_file": "c:\\User\\mydb.env",
    }
