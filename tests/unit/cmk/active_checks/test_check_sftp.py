#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
from collections.abc import Iterable
from unittest.mock import MagicMock, patch

import pytest

from cmk.active_checks.check_sftp import (
    Args,
    file_available,
    get_paths,
    parse_arguments,
    PathDict,
    run_check,
)


def test_parse_arguments() -> None:
    assert parse_arguments([]) == Args(
        host=None,
        user=None,
        pass_=None,
        port=22,
        get_remote=None,
        get_local=None,
        put_local=None,
        put_remote=None,
        timestamp=None,
        timeout=10.0,
        verbose=False,
        look_for_keys=False,
    )


def test_get_paths() -> None:
    assert (
        get_paths(
            opt_put_local=None,
            opt_get_local=None,
            opt_put_remote=None,
            opt_get_remote=None,
            opt_timestamp=None,
            omd_root="/omdroot",
            working_dir="/workdir",
        )
        == PathDict()
    )

    assert get_paths(
        opt_put_local="some value",
        opt_get_local=None,
        opt_put_remote=None,
        opt_get_remote=None,
        opt_timestamp=None,
        omd_root="/omdroot",
        working_dir="/workdir",
    ) == PathDict(
        local_put_path="/omdroot/some value",
        put_filename="some value",
        remote_put_path="/workdir/some value",
    )

    assert get_paths(
        opt_put_local=None,
        opt_get_local=None,
        opt_put_remote=None,
        opt_get_remote="some value",
        opt_timestamp=None,
        omd_root="/omdroot",
        working_dir="/workdir",
    ) == PathDict(
        get_filename="some value",
        local_get_path="/omdroot/some value",
        remote_get_path="/workdir/some value",
    )

    assert get_paths(
        opt_put_local="foobar",
        opt_get_local=None,
        opt_put_remote=None,
        opt_get_remote=None,
        opt_timestamp=None,
        omd_root="/omdroot",
        working_dir="/workdir",
    ) == PathDict(
        put_filename="foobar",
        local_put_path="/omdroot/foobar",
        remote_put_path="/workdir/foobar",
    )

    # absolute paths do not work properly...
    assert get_paths(
        opt_put_local="/foobar",
        opt_get_local=None,
        opt_put_remote=None,
        opt_get_remote=None,
        opt_timestamp=None,
        omd_root="/omdroot",
        working_dir="/workdir",
    ) == PathDict(
        put_filename="foobar",
        local_put_path="/omdroot//foobar",
        remote_put_path="/workdir/foobar",
    )


class ConnectionMock:
    def __init__(self) -> None:
        self._workdir: str | None = None
        self.get_calls: list[tuple[str, str]] = []
        self.put_calls: list[tuple[str, str]] = []
        self.remove_calls: list[str] = []
        self.stat_calls: list[str] = []
        self.listdir_calls: list[str] = []

    def reset_mock(self) -> None:
        self._workdir = None
        assert not self.get_calls
        assert not self.put_calls
        assert not self.remove_calls
        assert not self.stat_calls
        assert not self.listdir_calls

    def chdir(self, workdir: str) -> None:
        self._workdir = workdir

    def getcwd(self) -> str | None:
        return self._workdir

    def get(self, source: str, destination: str) -> None:
        self.get_calls.append((source, destination))

    def listdir(self, dir_: str) -> list[str]:
        self.listdir_calls.append(dir_)
        return ["entry_in_dir"]

    def put(self, source: str, destination: str) -> None:
        self.put_calls.append((source, destination))

    def remove(self, path: str) -> None:
        self.remove_calls.append(path)

    def stat(self, path: str) -> object:
        self.stat_calls.append(path)
        return MagicMock(return_value=3)


@pytest.fixture(name="connection_mock")
def mock_connection() -> Iterable[ConnectionMock]:
    mock = ConnectionMock()
    with patch("cmk.active_checks.check_sftp.connection", lambda *_: mock):
        yield mock


def test_file_available(connection_mock: ConnectionMock) -> None:
    assert not file_available("opt_put_local", None, connection_mock, "/workdir")  # type: ignore[arg-type]
    assert connection_mock.listdir_calls.pop() == "/workdir/None"
    connection_mock.reset_mock()


@pytest.fixture(name="omd_root_mock")
def mock_omd_root() -> Iterable[None]:
    old_omd_root = os.environ.get("OMD_ROOT")
    try:
        os.environ["OMD_ROOT"] = "/omdroot"
        yield
    finally:
        if old_omd_root is not None:
            os.environ["OMD_ROOT"] = old_omd_root
        else:
            del os.environ["OMD_ROOT"]


@pytest.fixture(name="create_testfile_mock")
def mock_create_testfile() -> Iterable[None]:
    with patch("cmk.active_checks.check_sftp.create_testfile"):
        yield


def test_run_check(omd_root_mock: None, connection_mock: ConnectionMock) -> None:
    assert run_check(["-v"]) == (0, "Login successful")
    connection_mock.reset_mock()


def test_run_check_pulling_files(omd_root_mock: None, connection_mock: ConnectionMock) -> None:
    assert run_check(
        [
            "--get-remote",
            "get_remote",
            "-v",
        ]
    ) == (
        0,
        "Login successful, Successfully got file from SFTP server",
    )
    assert connection_mock.get_calls.pop() == ("./get_remote", "/omdroot/get_remote")
    connection_mock.reset_mock()

    assert run_check(
        [
            "--get-remote",
            "get_remote",
            "--get-local",
            "get_local",
            "-v",
        ]
    ) == (
        0,
        "Login successful, Successfully got file from SFTP server",
    )
    assert connection_mock.get_calls.pop() == ("./get_remote", "/omdroot/get_local/get_remote")
    connection_mock.reset_mock()

    assert run_check(
        [
            "--get-local",
            "get_local",
            "-v",
        ]
    ) == (
        0,
        "Login successful",
    )
    connection_mock.reset_mock()


def test_run_check_pushing_files(
    omd_root_mock: None, create_testfile_mock: None, connection_mock: ConnectionMock
) -> None:
    # file that does not exist on the remote
    assert run_check(
        [
            "--put-local",
            "put_local",
            "-v",
        ]
    ) == (
        0,
        "Login successful, Successfully put file to SFTP server",
    )
    assert connection_mock.put_calls.pop() == ("/omdroot/put_local", "./put_local")
    assert connection_mock.remove_calls.pop() == "./put_local"
    assert connection_mock.listdir_calls.pop() == "./None"
    connection_mock.reset_mock()

    # file that does exist on the remote
    # That is not removed...
    assert run_check(
        [
            "--put-local",
            "entry_in_dir",
            "-v",
        ]
    ) == (
        0,
        "Login successful, Successfully put file to SFTP server",
    )
    assert connection_mock.put_calls.pop() == ("/omdroot/entry_in_dir", "./entry_in_dir")
    assert connection_mock.listdir_calls.pop() == "./None"
    connection_mock.reset_mock()

    # the put-remote is a path...
    assert run_check(
        [
            "--put-local",
            "put_local",
            "--put-remote",
            "entry_in_dir",
            "-v",
        ]
    ) == (
        0,
        "Login successful, Successfully put file to SFTP server",
    )
    assert connection_mock.put_calls.pop() == ("/omdroot/put_local", "./entry_in_dir/put_local")
    assert connection_mock.remove_calls.pop() == "./entry_in_dir/put_local"
    assert connection_mock.listdir_calls.pop() == "./entry_in_dir"
    connection_mock.reset_mock()


def test_run_check_get_timestamp(
    omd_root_mock: None, create_testfile_mock: None, connection_mock: ConnectionMock
) -> None:
    # file that does not exist on the remote
    state, message = run_check(
        [
            "--get-timestamp",
            "get_timestamp",
            "-v",
        ]
    )
    # The timestamp is interpreted as local time...
    assert state == 0
    assert message.startswith("Login successful, Timestamp of get_timestamp is:")
    assert connection_mock.stat_calls.pop() == "./get_timestamp"
    connection_mock.reset_mock()


def test_run_check_failures(
    omd_root_mock: None, create_testfile_mock: None, connection_mock: ConnectionMock
) -> None:
    state, message = run_check(
        [
            "--get-remote",
            "get_remote",
            "--put-local",
            "tmp/sftp/put_local",
            "--get-timestamp",
            "get_timestamp",
            "-v",
        ]
    )
    assert state == 0
    assert message.startswith(
        "Login successful, Successfully put file to SFTP server, Successfully got file from SFTP server, Timestamp of get_timestamp is: "
    )

    with (
        patch("cmk.active_checks.check_sftp.put_file", MagicMock(side_effect=Exception("Boom!"))),
        patch("cmk.active_checks.check_sftp.get_file", MagicMock(side_effect=Exception("Boom!"))),
        patch(
            "cmk.active_checks.check_sftp.get_timestamp", MagicMock(side_effect=Exception("Boom!"))
        ),
    ):
        assert run_check(
            [
                "--get-remote",
                "get_remote",
                "--put-local",
                "put_local",
                "--get-timestamp",
                "get_timestamp",
            ]
        ) == (
            2,
            "Login successful, Could not put file to SFTP server! (!!), Could not get file from SFTP server! (!!), Could not get timestamp of file! (!!)",
        )
