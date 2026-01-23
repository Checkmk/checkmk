#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"
# ruff: noqa: I001

import copy
import sys
from unittest.mock import Mock, patch

import pytest
from _pytest.monkeypatch import MonkeyPatch
from agents.plugins import mk_postgres

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
    "INSTANCE=/home/postgres/db1.env{sep}USER_NAME{sep}/PATH/TO/.pgpass{sep}",
]
VALID_CONFIG_WITH_PG_BINARY_PATH = [
    "PG_BINARY_PATH=C:\\PostgreSQL\\15\\bin\\psql.exe",
    "",
    "DBUSER=user_xy",
]

#   .--tests---------------------------------------------------------------.
#   |                        _            _                                |
#   |                       | |_ ___  ___| |_ ___                          |
#   |                       | __/ _ \/ __| __/ __|                         |
#   |                       | ||  __/\__ \ |_\__ \                         |
#   |                        \__\___||___/\__|___/                         |
#   |                                                                      |
#   +----------------------------------------------------------------------+


class TestNotImplementedOS:
    @pytest.fixture(autouse=True)
    def is_not_implemented_os(self, monkeypatch: MonkeyPatch) -> None:
        monkeypatch.setattr(mk_postgres, "IS_WINDOWS", False)
        monkeypatch.setattr(mk_postgres, "IS_LINUX", False)

    def test_not_implemented_os(self) -> None:
        with pytest.raises(Exception) as e:
            mk_postgres.helper_factory().get_default_path()
        assert "is not yet implemented" in str(e.value)
        with pytest.raises(Exception) as e:
            mk_postgres.helper_factory().get_default_postgres_user()
        assert "is not yet implemented" in str(e.value)


class TestLinux:
    @pytest.fixture(autouse=True)
    def is_linux(self, monkeypatch: MonkeyPatch) -> None:
        monkeypatch.setattr(mk_postgres, "IS_WINDOWS", False)
        monkeypatch.setattr(mk_postgres, "IS_LINUX", True)
        monkeypatch.setattr(
            mk_postgres,
            "open_env_file",
            lambda *_args: [
                "export PGPORT=5432",
                "export PGVERSION=12.3",
            ],
        )

    def test_get_default_path(
        self,
    ):
        assert "/etc/check_mk" == mk_postgres.helper_factory().get_default_path()

    def test_get_default_postgres_user(
        self,
    ):
        assert "postgres" == mk_postgres.helper_factory().get_default_postgres_user()

    @patch("subprocess.Popen")
    def test_postgres_binary_path_fallback(self, mock_Popen):
        process_mock = Mock()
        attrs = {
            "communicate.side_effect": [("usr/mydb-12.3/bin", None)],
            "returncode": 0,
        }
        process_mock.configure_mock(**attrs)
        mock_Popen.return_value = process_mock
        instance = {
            "pg_database": "mydb",
            "pg_port": "1234",
            "name": "mydb",
            "pg_user": "myuser",
            "pg_passfile": "/home/.pgpass",
            "pg_version": "12.3",
            "pg_host": "",
        }  # type: dict[str, str | None]
        myPostgresOnLinux = mk_postgres.postgres_factory("postgres", None, instance)

        assert myPostgresOnLinux.psql_binary_path == "usr/mydb-12.3/bin"

    def test_config_without_instance(
        self,
    ):
        sep = mk_postgres.helper_factory().get_conf_sep()
        dbuser, _pg_path, instances = mk_postgres.parse_postgres_cfg(
            VALID_CONFIG_WITHOUT_INSTANCE, sep
        )
        assert dbuser == "user_xy"
        assert len(instances) == 0

    def test_config_with_binary_path(
        self,
    ):
        sep = mk_postgres.helper_factory().get_conf_sep()
        dbuser, pg_binary, _instances = mk_postgres.parse_postgres_cfg(
            VALID_CONFIG_WITH_PG_BINARY_PATH, sep
        )
        assert dbuser == "user_xy"
        assert pg_binary == "C:\\PostgreSQL\\15\\bin\\psql.exe"

    def test_config_with_instance(
        self,
    ):
        config = copy.deepcopy(VALID_CONFIG_WITH_INSTANCES)
        config[-1] = config[-1].format(sep=SEP_LINUX)
        sep = mk_postgres.helper_factory().get_conf_sep()
        dbuser, _pg_path, instances = mk_postgres.parse_postgres_cfg(config, sep)
        assert dbuser == "user_yz"
        assert len(instances) == 1
        assert instances[0]["pg_port"] == "5432"
        assert instances[0]["name"] == "db1"
        assert instances[0]["pg_user"] == "USER_NAME"
        assert instances[0]["pg_passfile"] == "/PATH/TO/.pgpass"

    @patch("subprocess.Popen")
    def test_factory_without_instance(
        self,
        mock_Popen,
    ):
        process_mock = Mock()
        attrs = {
            "communicate.side_effect": [
                ("/usr/lib/postgres/psql", None),
                (b"postgres\x00db1", None),
                ("12.3", None),
            ],
            "returncode": 0,
        }
        process_mock.configure_mock(**attrs)
        mock_Popen.return_value = process_mock
        instance = {
            "name": "main",
            "pg_user": "postgres",
            "pg_database": "postgres",
            "pg_port": "5432",
            "pg_passfile": "",
            "pg_host": "",
        }  # type: dict[str, str | None]
        myPostgresOnLinux = mk_postgres.postgres_factory("postgres", None, instance)

        assert isinstance(myPostgresOnLinux, mk_postgres.PostgresLinux)
        assert myPostgresOnLinux.psql_binary_path == "/usr/lib/postgres/psql"
        assert myPostgresOnLinux.psql_binary_dirname == "/usr/lib/postgres"
        assert myPostgresOnLinux.get_databases() == ["postgres", "db1"]
        assert myPostgresOnLinux.get_server_version() == 12.3
        assert myPostgresOnLinux.pg_database == "postgres"
        assert myPostgresOnLinux.pg_port == "5432"

    @patch("os.path.isfile", return_value=True)
    @patch("subprocess.Popen")
    def test_factory_with_instance(
        self,
        mock_Popen,
        mock_isfile,
        monkeypatch,
    ):
        instance = {
            "pg_database": "mydb",
            "pg_port": "1234",
            "name": "mydb",
            "pg_user": "myuser",
            "pg_passfile": "/home/.pgpass",
            "pg_version": "12.3",
            "pg_host": "",
        }  # type: dict[str, str | None]
        process_mock = Mock()
        attrs = {
            "communicate.side_effect": [
                (b"postgres\x00db1", None),
                ("12.3.6", None),
            ],
            "returncode": 0,
        }
        process_mock.configure_mock(**attrs)
        mock_Popen.return_value = process_mock
        myPostgresOnLinux = mk_postgres.postgres_factory("postgres", None, instance)

        assert isinstance(myPostgresOnLinux, mk_postgres.PostgresLinux)
        assert myPostgresOnLinux.psql_binary_path == "/mydb/12.3/bin/psql"
        assert myPostgresOnLinux.psql_binary_dirname == "/mydb/12.3/bin"
        assert myPostgresOnLinux.get_databases() == ["postgres", "db1"]
        assert myPostgresOnLinux.get_server_version() == 12.3
        assert myPostgresOnLinux.pg_database == "mydb"
        assert myPostgresOnLinux.pg_port == "1234"
        assert myPostgresOnLinux.pg_user == "myuser"
        assert myPostgresOnLinux.my_env["PGPASSFILE"] == "/home/.pgpass"
        assert myPostgresOnLinux.name == "mydb"

    @patch("subprocess.Popen")
    def test_get_instances(
        self,
        mock_Popen,
        monkeypatch,
    ):
        instance = {
            "pg_database": "mydb",
            "pg_port": "1234",
            "name": "main",
            "pg_user": "myuser",
            "pg_passfile": "/home/.pgpass",
            "pg_host": "",
            "version": "12.3",
        }  # type: dict[str, str | None]
        process_mock = Mock()
        attrs = {
            "communicate.side_effect": [
                ("/usr/lib/postgres/psql", None),
                (b"postgres\x00db1", None),
                ("12.3.6", None),
            ],
            "returncode": 0,
        }
        process_mock.configure_mock(**attrs)
        mock_Popen.return_value = process_mock
        myPostgresOnLinux = mk_postgres.postgres_factory("postgres", None, instance)

        process_mock = Mock()
        attrs = {
            "communicate.side_effect": [
                (
                    "\n".join(
                        [
                            "3190 postgres: logger",
                            "1252 /usr/bin/postmaster -D /var/lib/pgsql/data",
                            "3148 postmaster -D /var/lib/pgsql/data",
                        ]
                    ),
                    None,
                ),
            ],
            "returncode": 0,
        }
        process_mock.configure_mock(**attrs)
        mock_Popen.return_value = process_mock
        assert myPostgresOnLinux.get_instances() == "\n".join(
            [
                "1252 /usr/bin/postmaster -D /var/lib/pgsql/data",
                "3148 postmaster -D /var/lib/pgsql/data",
            ]
        )

    @pytest.mark.parametrize(
        "instance_name,ps_instances,exp_instance",
        [
            pytest.param("TEST", ["test", "TEST"], "TEST", id="case sensitive upper case"),
            pytest.param("test", ["test", "TEST"], "test", id="case sensitive lower case"),
            pytest.param("test", ["TEST"], "TEST", id="not case sensitive 1"),
            pytest.param("TEST", ["test"], "test", id="not case sensitive 2"),
        ],
    )
    @patch("subprocess.Popen")
    def test_get_instances_case_sensitivity(
        self, mock_Popen, instance_name, ps_instances, exp_instance
    ):
        instance = {
            "pg_database": "mydb",
            "pg_port": "1234",
            "name": instance_name,
            "pg_user": "myuser",
            "pg_passfile": "/home/.pgpass",
            "pg_version": "12.3",
            "pg_host": "",
        }

        process_mock = Mock()
        attrs = {
            "communicate.side_effect": [
                ("/usr/lib/postgres/psql", None),
                ("postgres\ndb1", None),
                ("12.3.6", None),
            ],
            "returncode": 0,
        }
        process_mock.configure_mock(**attrs)
        mock_Popen.return_value = process_mock

        myPostgresOnLinux = mk_postgres.postgres_factory("postgres", None, instance)
        process_mock = Mock()

        proc_list = []
        for ps_instance in ps_instances:
            proc_list.extend(
                [
                    "3190 postgres: 13/%s logger" % ps_instance,
                    "785150 /usr/lib/postgresql/13/bin/postgres -D /var/lib/postgresql/13/%s "
                    % ps_instance,
                ]
            )
        attrs = {
            "communicate.side_effect": [("\n".join(proc_list), None)],
            "returncode": 0,
        }
        process_mock.configure_mock(**attrs)
        mock_Popen.return_value = process_mock

        assert myPostgresOnLinux.get_instances() == "\n".join(
            [
                "3190 postgres: 13/%s logger" % exp_instance,
                "785150 /usr/lib/postgresql/13/bin/postgres -D /var/lib/postgresql/13/%s"
                % exp_instance,
            ]
        )

    def test_parse_INSTANCE_value(self) -> None:
        # Legacy format, deprecated in Werk 16016, but kept around to not force updating the configuration.
        got = mk_postgres._parse_INSTANCE_value(
            "/home/postgres/db2.env:USER_NAME:/PATH/TO/.pgpass", SEP_LINUX
        )
        expected = ("/home/postgres/db2.env", "USER_NAME", "/PATH/TO/.pgpass", "db2")
        assert got == expected

        # Legacy format, deprecated in Werk 16016, but kept around to not force updating the configuration.
        # This is a weird edge case, that was broken in 2.1.0p30 and 2.2.0p4 .
        got = mk_postgres._parse_INSTANCE_value(
            "/home/postgres/.env:USER_NAME:/PATH/TO/.pgpass", SEP_LINUX
        )
        expected = ("/home/postgres/.env", "USER_NAME", "/PATH/TO/.pgpass", "")
        assert got == expected

        # Bad configuration, we keep this around to migrate users from old to new config format
        # But instance_name should really empty, or we should disallow this
        got = mk_postgres._parse_INSTANCE_value(
            "/home/postgres/db2.env:USER_NAME:/PATH/TO/.pgpass:", SEP_LINUX
        )
        expected = ("/home/postgres/db2.env", "USER_NAME", "/PATH/TO/.pgpass", "db2")
        assert got == expected

        # Correct configuration
        got = mk_postgres._parse_INSTANCE_value(
            "/home/postgres/db2.env:USER_NAME:/PATH/TO/.pgpass:hi", SEP_LINUX
        )
        expected = ("/home/postgres/db2.env", "USER_NAME", "/PATH/TO/.pgpass", "hi")
        assert got == expected


class TestWindows:
    @pytest.fixture(autouse=True)
    def is_windows(self, monkeypatch: MonkeyPatch) -> None:
        monkeypatch.setattr(mk_postgres, "IS_WINDOWS", True)
        monkeypatch.setattr(mk_postgres, "IS_LINUX", False)
        monkeypatch.setattr(
            mk_postgres,
            "open_env_file",
            lambda *_args: [
                "export PGPORT=5432",
                "export PGVERSION=12.1",
            ],
        )
        monkeypatch.setattr(
            mk_postgres.PostgresWin,
            "_call_wmic_logicaldisk",
            staticmethod(
                lambda: "DeviceID  \r\r\nC:        \r\r\nD:        \r\r\nH:        \r\r\nI:        \r\r\nR:        \r\r\n\r\r\n"
            ),
        )

    def test_get_default_path(self) -> None:
        assert (
            "c:\\ProgramData\\checkmk\\agent\\config"
            == mk_postgres.helper_factory().get_default_path()
        )

    def test_get_default_postgres_user(self) -> None:
        assert "postgres" == mk_postgres.helper_factory().get_default_postgres_user()

    def test_config_with_instance(
        self,
    ):
        config = copy.deepcopy(VALID_CONFIG_WITH_INSTANCES)
        config[-1] = config[-1].format(sep=SEP_WINDOWS)
        sep = mk_postgres.helper_factory().get_conf_sep()
        dbuser, _pg_path, instances = mk_postgres.parse_postgres_cfg(config, sep)
        assert len(instances) == 1
        assert dbuser == "user_yz"
        assert instances[0]["pg_port"] == "5432"
        assert instances[0]["name"] == "db1"
        assert instances[0]["pg_user"] == "USER_NAME"
        assert instances[0]["pg_passfile"] == "/PATH/TO/.pgpass"
        assert instances[0]["pg_version"] == "12.1"

    @patch("os.path.isfile", return_value=True)
    @patch("subprocess.Popen")
    def test_factory_without_instance(self, mock_Popen: Mock, mock_isfile: Mock) -> None:
        process_mock = Mock()
        attrs = {
            "communicate.side_effect": [
                (b"postgres\x00db1\x00", b"ok"),
                (b"12.1", b"ok"),
            ],
            "returncode": 0,
        }
        process_mock.configure_mock(**attrs)
        mock_Popen.return_value = process_mock
        instance = {
            "pg_port": "5432",
            "pg_database": "postgres",
            "name": "data",
            "pg_user": "myuser",
            "pg_passfile": "/home/.pgpass",
            "pg_host": "",
        }  # type: dict[str, str | None]
        myPostgresOnWin = mk_postgres.postgres_factory("postgres", None, instance)

        mock_isfile.assert_called_with("C:\\Program Files\\PostgreSQL\\12\\bin\\psql.exe")
        assert isinstance(myPostgresOnWin, mk_postgres.PostgresWin)
        assert (
            myPostgresOnWin.psql_binary_path == "C:\\Program Files\\PostgreSQL\\12\\bin\\psql.exe"
        )
        assert myPostgresOnWin.psql_binary_dirname == "C:\\Program Files\\PostgreSQL\\12\\bin"
        assert myPostgresOnWin.get_databases() == ["postgres", "db1"]
        assert myPostgresOnWin.get_server_version() == 12.1
        assert myPostgresOnWin.pg_database == "postgres"
        assert myPostgresOnWin.pg_port == "5432"

    @patch("os.path.isfile", return_value=True)
    @patch("subprocess.Popen")
    def test_factory_do_not_overwrite_PG_PASSFILE(
        self,
        mock_Popen,
        mock_isfile,
    ):
        instance = {
            "pg_database": "mydb",
            "pg_port": "1234",
            "name": "mydb",
            "pg_user": "myuser",
            "pg_version": "12.1",
            "pg_host": "",
        }  # type: dict[str, str | None]
        process_mock = Mock()
        attrs = {
            "communicate.side_effect": [
                (b"postgres\x00db1\x00", b"ok"),
                (b"12.1.5\x00", b"ok"),
            ],
            "returncode": 0,
        }
        process_mock.configure_mock(**attrs)
        mock_Popen.return_value = process_mock

        myPostgresOnWin = mk_postgres.postgres_factory("postgres", None, instance)

        mock_isfile.assert_called_with("C:\\Program Files\\PostgreSQL\\12\\bin\\psql.exe")
        assert "PGPASSFILE" not in myPostgresOnWin.my_env

    @patch("os.path.isfile", return_value=True)
    @patch("subprocess.Popen")
    def test_factory_with_instance(
        self,
        mock_Popen,
        mock_isfile,
    ):
        instance = {
            "pg_database": "mydb",
            "pg_port": "1234",
            "name": "mydb",
            "pg_user": "myuser",
            "pg_passfile": "c:\\User\\.pgpass",
            "pg_version": "12.1",
            "pg_host": "",
        }  # type: dict[str, str | None]
        process_mock = Mock()
        attrs = {
            "communicate.side_effect": [
                (b"postgres\x00db1\x00", b"ok"),
                (b"12.1.5\x00", b"ok"),
            ],
            "returncode": 0,
        }
        process_mock.configure_mock(**attrs)
        mock_Popen.return_value = process_mock

        myPostgresOnWin = mk_postgres.postgres_factory("postgres", None, instance)

        mock_isfile.assert_called_with("C:\\Program Files\\PostgreSQL\\12\\bin\\psql.exe")
        assert isinstance(myPostgresOnWin, mk_postgres.PostgresWin)
        assert (
            myPostgresOnWin.psql_binary_path == "C:\\Program Files\\PostgreSQL\\12\\bin\\psql.exe"
        )
        assert myPostgresOnWin.psql_binary_dirname == "C:\\Program Files\\PostgreSQL\\12\\bin"
        assert myPostgresOnWin.get_databases() == ["postgres", "db1"]
        assert myPostgresOnWin.get_server_version() == 12.1
        assert myPostgresOnWin.pg_database == "mydb"
        assert myPostgresOnWin.pg_port == "1234"
        assert myPostgresOnWin.pg_user == "myuser"
        assert myPostgresOnWin.my_env["PGPASSFILE"] == "c:\\User\\.pgpass"
        assert myPostgresOnWin.name == "mydb"

    def test_parse_INSTANCE_value(self) -> None:
        # Legacy format, deprecated in Werk 16016, but kept around to not force updating the configuration.
        got = mk_postgres._parse_INSTANCE_value(
            "/home/postgres/db2.env|USER_NAME|/PATH/TO/.pgpass", SEP_WINDOWS
        )
        expected = ("/home/postgres/db2.env", "USER_NAME", "/PATH/TO/.pgpass", "db2")
        assert got == expected

        # Legacy format, deprecated in Werk 16016, but kept around to not force updating the configuration.
        # This is a weird edge case, that was broken in 2.1.0p30 and 2.2.0p4 .
        got = mk_postgres._parse_INSTANCE_value(
            "/home/postgres/.env|USER_NAME|/PATH/TO/.pgpass", SEP_WINDOWS
        )
        expected = ("/home/postgres/.env", "USER_NAME", "/PATH/TO/.pgpass", "")
        assert got == expected

        # Bad configuration, we keep this around to migrate users from old to new config format
        # But instance_name should really empty, or we should disallow this
        got = mk_postgres._parse_INSTANCE_value(
            "/home/postgres/db2.env|USER_NAME|/PATH/TO/.pgpass|", SEP_WINDOWS
        )
        expected = ("/home/postgres/db2.env", "USER_NAME", "/PATH/TO/.pgpass", "db2")
        assert got == expected

        # Correct configuration
        got = mk_postgres._parse_INSTANCE_value(
            "/home/postgres/db2.env|USER_NAME|/PATH/TO/.pgpass|hi", SEP_WINDOWS
        )
        expected = ("/home/postgres/db2.env", "USER_NAME", "/PATH/TO/.pgpass", "hi")
        assert got == expected
        # Legacy format, deprecated in Werk 16016, but kept around to not force updating the configuration.
        got = mk_postgres._parse_INSTANCE_value(
            "/home/postgres/db2.env|USER_NAME|/PATH/TO/.pgpass", SEP_WINDOWS
        )
        expected = ("/home/postgres/db2.env", "USER_NAME", "/PATH/TO/.pgpass", "db2")
        assert got == expected

        # Legacy format, deprecated in Werk 16016, but kept around to not force updating the configuration.
        # This is a weird edge case, that was broken in 2.1.0p30 and 2.2.0p4 .
        got = mk_postgres._parse_INSTANCE_value(
            "/home/postgres/.env|USER_NAME|/PATH/TO/.pgpass", SEP_WINDOWS
        )
        expected = ("/home/postgres/.env", "USER_NAME", "/PATH/TO/.pgpass", "")
        assert got == expected

        # Bad configuration, we keep this around to migrate users from old to new config format
        # But instance_name should really empty, or we should disallow this
        got = mk_postgres._parse_INSTANCE_value(
            "/home/postgres/db2.env|USER_NAME|/PATH/TO/.pgpass|", SEP_WINDOWS
        )
        expected = ("/home/postgres/db2.env", "USER_NAME", "/PATH/TO/.pgpass", "db2")
        assert got == expected

        # Correct configuration
        got = mk_postgres._parse_INSTANCE_value(
            "/home/postgres/db2.env|USER_NAME|/PATH/TO/.pgpass|hi", SEP_WINDOWS
        )
        expected = ("/home/postgres/db2.env", "USER_NAME", "/PATH/TO/.pgpass", "hi")
        assert got == expected


def test_parse_env_file(tmp_path):
    path = tmp_path / ".env"
    with open(str(path), "wb") as fo:
        fo.write(
            b"export PGDATABASE='ut_pg_database'\n"
            b"PGPORT=ut_pg_port  # missing export, but still parsed... \n"
            b'export PGVERSION="some version"   \n'
        )
    assert mk_postgres.parse_env_file(str(path)) == (
        "'ut_pg_database'",  # this double quoting seems to be funny.
        # but this is the expected behaviour (and we want to make a minimal change)
        # the value will be used on the commandline, so bash will handle the quoting...
        "ut_pg_port",
        '"some version"',  # same as above
        "",
    )


def test_parse_env_file_comments(tmp_path):
    path = tmp_path / ".env"
    with open(str(path), "wb") as fo:
        fo.write(
            b"export PGDATABASE=ut_pg_database\n"
            b"# export PGDATABASE=ut_some_other_database\n"
            b"PGPORT=123\n"
            b"#PGPORT=345\n"
        )
    assert mk_postgres.parse_env_file(str(path)) == (
        "ut_pg_database",
        "123",
        None,
        "",
    )


def test_parse_env_file_pghost(tmp_path):
    path = tmp_path / ".env"
    with open(str(path), "wb") as fo:
        fo.write(
            b"export PGDATABASE=ut_pg_database\n"
            b"# export PGDATABASE=ut_some_other_database\n"
            b"PGPORT=123\n"
            b'export PGHOST="hostname.my.domain"\n'
        )
    assert mk_postgres.parse_env_file(str(path)) == (
        "ut_pg_database",
        "123",
        None,
        '"hostname.my.domain"',
    )


def test_parse_env_file_parser(tmp_path):
    path = tmp_path / ".env"
    with open(str(path), "wb") as fo:
        fo.write(
            b"# this is a comment\n"
            b" # t = is a comment\n"
            b"\t#\tt =s a comment\n"
            b"\n"  # empty line
            b"export PGDATABASE=ut_pg_database\n"
            b"PGPORT=123\n"
        )
    assert mk_postgres.parse_env_file(str(path)) == (
        "ut_pg_database",
        "123",
        None,
        "",
    )
