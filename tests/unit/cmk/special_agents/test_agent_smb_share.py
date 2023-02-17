#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from datetime import datetime
from unittest import mock

import freezegun
import pytest
from smb.base import NotConnectedError, SharedFile  # type: ignore[import]
from smb.smb_structs import OperationFailure  # type: ignore[import]

from cmk.special_agents.agent_smb_share import (
    connect,
    File,
    get_all_shared_files,
    iter_shared_files,
    main,
    parse_arguments,
    smb_share_agent,
)

SHARED_FOLDER = "My Shared Folder"
HOST_NAME = "HOSTNAME"
SHARE_BASE = f"\\\\{HOST_NAME}\\{SHARED_FOLDER}"


def file(name: str) -> SharedFile:
    return SharedFile(0, 0, 0, 0, 10, 0, 32, "", name)


def folder(name: str) -> SharedFile:
    return SharedFile(0, 0, 0, 0, 10, 0, 16, "", name)


class MockShare:
    def __init__(self, name) -> None:  # type:ignore[no-untyped-def]
        self._name = name

    @property
    def name(self) -> str:
        return self._name


class MockSMBConnection:
    def __init__(  # type:ignore[no-untyped-def]
        self, *args, filesystem=None, shares=None, is_direct_tcp=False
    ) -> None:
        self.filesystem = filesystem
        self.shares = shares
        self.is_direct_tcp = is_direct_tcp

    @staticmethod
    def connect(*args):
        return True

    def listPath(self, shared_folder: str, path: str) -> list[SharedFile]:
        if shared_folder not in self.filesystem:
            return []
        return self.filesystem[shared_folder].get(path)

    def listShares(self) -> list[MockShare]:
        if not self.shares:
            return []
        return [MockShare(s) for s in self.shares]

    def close(self):
        pass


class MockSectionWriter:
    writer: list[str] = []

    def __init__(self, *args, **kwargs) -> None:  # type:ignore[no-untyped-def]
        self.writer.clear()

    def __enter__(self):
        return self.writer

    def __exit__(self, *args):
        pass


def test_parse_arguments() -> None:
    args = parse_arguments(
        [
            "hostname",
            "127.0.0.1",
            "--username",
            "username",
            "--password",
            "password",
            "--patterns",
            "\\\\HOSTNAME\\Share Folder 1\\*.log",
            "\\\\HOSTNAME\\Share Folder 2\\file.txt",
        ]
    )
    assert args.hostname == "hostname"
    assert args.ip_address == "127.0.0.1"
    assert args.username == "username"
    assert args.password == "password"
    assert args.patterns == [
        "\\\\HOSTNAME\\Share Folder 1\\*.log",
        "\\\\HOSTNAME\\Share Folder 2\\file.txt",
    ]


@pytest.mark.parametrize(
    "filesystem, pattern, expected_file_data",
    [
        pytest.param(
            {
                SHARED_FOLDER: {
                    "": [folder("Subfolder1")],
                    "Subfolder1\\": [
                        file("My File"),
                        file("File"),
                    ],
                }
            },
            ["Subfolder1", "My File"],
            [(f"{SHARE_BASE}\\Subfolder1\\My File", "My File")],
            id="exact pattern for one file to match",
        ),
        pytest.param(
            {
                SHARED_FOLDER: {
                    "": [
                        folder("Subfolder1"),
                        file("file1"),
                    ],
                    "Subfolder1\\": [
                        folder("Subfolder2"),
                        folder("Subfolder3"),
                        file("file2"),
                    ],
                    "Subfolder1\\Subfolder2\\": [
                        file("file3"),
                        file("file4"),
                    ],
                    "Subfolder1\\Subfolder3\\": [
                        file("file5"),
                    ],
                }
            },
            ["Subfolder1", "*folder*", "*ile*"],
            [
                (f"{SHARE_BASE}\\Subfolder1\\Subfolder2\\file3", "file3"),
                (f"{SHARE_BASE}\\Subfolder1\\Subfolder2\\file4", "file4"),
                (f"{SHARE_BASE}\\Subfolder1\\Subfolder3\\file5", "file5"),
            ],
            id="wildcard in folder- and filename",
        ),
        pytest.param(
            {
                SHARED_FOLDER: {
                    "": [
                        folder("Subfolder1"),
                        file("some_file"),
                    ],
                    "Subfolder1\\": [
                        folder("Subfolder2"),
                        folder("Subfolder3"),
                        file("some_file"),
                    ],
                    "Subfolder1\\Subfolder2\\": [
                        folder("Subfolder4"),
                        file("some_file"),
                        file("some_file"),
                    ],
                    "Subfolder1\\Subfolder2\\Subfolder4\\": [
                        file("some_file"),
                    ],
                    "Subfolder1\\Subfolder3\\": [
                        folder("Subfolder5"),
                        file("some_file"),
                    ],
                    "Subfolder1\\Subfolder3\\Subfolder5\\": [
                        file("some_file"),
                    ],
                }
            },
            ["Subfolder1", "*", "*", "some_file"],
            [
                (
                    f"{SHARE_BASE}\\Subfolder1\\Subfolder2\\Subfolder4\\some_file",
                    "some_file",
                ),
                (
                    f"{SHARE_BASE}\\Subfolder1\\Subfolder3\\Subfolder5\\some_file",
                    "some_file",
                ),
            ],
            id="wildcard for 2 folder hirachies",
        ),
        pytest.param(
            {
                SHARED_FOLDER: {
                    "": [
                        folder("Subfolder1"),
                        file("some_file"),
                    ],
                    "Subfolder1\\": [
                        folder("Subfolder2"),
                        folder("Subfolder3"),
                        file("some_file"),
                    ],
                    "Subfolder1\\Subfolder2\\": [
                        folder("Subfolder4"),
                        file("some_file"),
                    ],
                    "Subfolder1\\Subfolder2\\Subfolder4\\": [
                        file("some_file"),
                    ],
                    "Subfolder1\\Subfolder3\\": [
                        folder("Subfolder5"),
                        file("some_file"),
                    ],
                    "Subfolder1\\Subfolder3\\Subfolder5\\": [
                        file("some_file"),
                    ],
                }
            },
            ["Subfolder1", "**", "some_file"],
            [
                (f"{SHARE_BASE}\\Subfolder1\\Subfolder2\\some_file", "some_file"),
                (
                    f"{SHARE_BASE}\\Subfolder1\\Subfolder3\\some_file",
                    "some_file",
                ),
            ],
            id="double star globbing, ignore one folder hirachy and don't match in current folder",
        ),
        pytest.param(
            {
                SHARED_FOLDER: {
                    "": [
                        folder("Subfolder1"),
                        file("file1"),
                        file("file2"),
                    ],
                }
            },
            ["*"],
            [
                (f"{SHARE_BASE}\\file1", "file1"),
                (f"{SHARE_BASE}\\file2", "file2"),
            ],
            id="match everything with *",
        ),
        pytest.param(
            {
                SHARED_FOLDER: {
                    "": [
                        folder("."),
                        folder(".."),
                    ],
                    "..": [file("file")],
                }
            },
            ["..", "file"],
            [],
            id="do not look into ..",
        ),
    ],
)
def test_iter_shared_files(
    filesystem: dict,
    pattern: list[str],
    expected_file_data: list[tuple[str, str]],
) -> None:
    conn = MockSMBConnection(filesystem=filesystem)
    files = list(iter_shared_files(conn, HOST_NAME, SHARED_FOLDER, pattern))
    file_data = [(f.path, f.file.filename) for f in files]

    assert file_data == expected_file_data


@pytest.mark.parametrize(
    "patterns, file_data, expected_file_data",
    [
        (
            [
                "\\\\HOSTNAME\\SharedFolder1\\Subfolder1\\File1",
            ],
            [
                ("path1", "file1"),
                ("path2", "file2"),
            ],
            [
                (
                    "\\\\HOSTNAME\\SharedFolder1\\Subfolder1\\File1",
                    [
                        ("path1", "file1"),
                        ("path2", "file2"),
                    ],
                ),
            ],
        ),
    ],
)
def test_get_all_shared_files(  # type:ignore[no-untyped-def]
    patterns: list[str],
    file_data: list[tuple[str, str]],
    expected_file_data: list[tuple[str, list[tuple[str, str]]]],
):
    with mock.patch("cmk.special_agents.agent_smb_share.iter_shared_files", return_value=file_data):
        conn = MockSMBConnection(shares=["SharedFolder1", "SharedFolder2"])
        files_per_pattern = [
            (p, list(f)) for p, f in get_all_shared_files(conn, HOST_NAME, patterns)
        ]
        assert files_per_pattern == expected_file_data


@pytest.mark.parametrize(
    "patterns, expected_error_message",
    [
        (
            ["\\\\INCORRECT_HOSTNAME\\SharedFolder1\\Subfolder1\\File1"],
            r"Pattern \\\\INCORRECT_HOSTNAME\\SharedFolder1\\Subfolder1\\File1 doesn't match HOSTNAME hostname",
        ),
        (
            ["\\\\HOSTNAME\\SharedFolder1\\Subfolder1\\File1"],
            "Share SharedFolder1 doesn't exist on host HOSTNAME",
        ),
    ],
)
def test_get_all_shared_files_errors(  # type:ignore[no-untyped-def]
    patterns: list[str],
    expected_error_message: str,
):
    conn = MockSMBConnection()
    with pytest.raises(RuntimeError, match=expected_error_message):
        dict(get_all_shared_files(conn, HOST_NAME, patterns))


@pytest.mark.parametrize(
    "arg_list, files, expected_result",
    [
        (
            [
                "hostname",
                "127.0.0.1",
                "--username",
                "username",
                "--password",
                "password",
                "--patterns",
                "\\Share Folder 1\\*.log",
                "\\Share Folder 2\\file.txt",
            ],
            [
                (
                    "\\Share Folder 1\\*.log",
                    [
                        File(
                            "\\Share Folder 1\\smb_share.log",
                            SharedFile(0, 0, 0, 1111111, 100, 0, 16, "", "smb_share.log"),
                        ),
                        File(
                            "\\Share Folder 1\\error.log",
                            SharedFile(0, 0, 0, 1111112, 200, 0, 16, "", "error.log"),
                        ),
                    ],
                ),
                (
                    "\\Share Folder 2\\file.txt",
                    [],
                ),
            ],
            [
                1641020400,
                "[[[header]]]",
                "name|status|size|time",
                "[[[content]]]",
                "\\Share Folder 1\\smb_share.log|ok|100|0",
                "\\Share Folder 1\\error.log|ok|200|0",
                "\\Share Folder 2\\file.txt|missing",
            ],
        )
    ],
)
@mock.patch("cmk.special_agents.agent_smb_share.SMBConnection", MockSMBConnection)
@freezegun.freeze_time(datetime(2022, 1, 1, 7, 0, 0, 0))
def test_smb_share_agent(arg_list, files, expected_result) -> None:  # type:ignore[no-untyped-def]
    args = parse_arguments(arg_list)

    with mock.patch("cmk.special_agents.agent_smb_share.get_all_shared_files", return_value=files):
        with mock.patch("cmk.special_agents.agent_smb_share.SectionWriter", MockSectionWriter):
            smb_share_agent(args)

    assert MockSectionWriter.writer == expected_result


def test_smb_share_agent_error() -> None:
    args = parse_arguments(
        ["hostname", "127.0.0.1", "--username", "username", "--password", "password"],
    )

    with mock.patch("cmk.special_agents.agent_smb_share.SMBConnection.connect") as mock_connection:
        mock_connection.side_effect = NotConnectedError
        with pytest.raises(
            RuntimeError,
            match="Could not connect to the remote host. Check your ip address and remote name.",
        ):
            smb_share_agent(args)


@mock.patch("cmk.special_agents.agent_smb_share.SMBConnection.connect", return_value=False)
def test_smb_share_agent_unsuccessful_connect(mock_connect) -> None:  # type:ignore[no-untyped-def]
    args = parse_arguments(
        ["hostname", "127.0.0.1", "--username", "username", "--password", "password"],
    )

    with pytest.raises(
        RuntimeError, match="Connection to the remote host was declined. Check your credentials."
    ):
        smb_share_agent(args)


@mock.patch("cmk.special_agents.agent_smb_share.connect")
@mock.patch("cmk.special_agents.agent_smb_share.get_all_shared_files")
@mock.patch("cmk.special_agents.agent_smb_share.write_section")
def test_smb_share_agent_operation_failure(  # type:ignore[no-untyped-def]
    mock_connect, mock_get_files, mock_write_section
) -> None:
    mock_write_section.side_effect = OperationFailure("Operation failure happened", [])
    args = parse_arguments(
        ["hostname", "127.0.0.1", "--username", "username", "--password", "password"],
    )
    with pytest.raises(OperationFailure, match="Operation failure happened"):
        smb_share_agent(args)


@mock.patch("cmk.special_agents.agent_smb_share.SMBConnection.connect", return_value=True)
@mock.patch("cmk.special_agents.agent_smb_share.SMBConnection.close")
def test_connect_error(mock_close, mock_connect) -> None:  # type:ignore[no-untyped-def]
    with pytest.raises(Exception, match="Exception during usage of smb connection"):
        with connect("username", "password", "hostname", "127.0.0.1"):
            raise Exception("Exception during usage of smb connection")

    mock_close.assert_called_once()


@mock.patch("cmk.special_agents.agent_smb_share.special_agent_main", return_value=0)
def test_main(mock_agent) -> None:  # type:ignore[no-untyped-def]
    assert main() == 0
