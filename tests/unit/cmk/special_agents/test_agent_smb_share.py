#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from datetime import datetime
from typing import Dict, List, Tuple
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


class MockShare:
    def __init__(self, name):
        self._name = name

    @property
    def name(self) -> str:
        return self._name


class MockSMBConnection:
    def __init__(self, *args, filesystem=None, shares=None, is_direct_tcp=False):
        self.filesystem = filesystem
        self.shares = shares
        self.is_direct_tcp = is_direct_tcp

    @staticmethod
    def connect(*args):
        return True

    def listPath(self, shared_folder: str, path: str) -> List[SharedFile]:
        if shared_folder not in self.filesystem:
            return []
        return self.filesystem[shared_folder].get(path)

    def listShares(self) -> List[MockShare]:
        if not self.shares:
            return []
        return [MockShare(s) for s in self.shares]

    def close(self):
        pass


class MockSectionWriter:
    writer: List[str] = []

    def __init__(self, *args, **kwargs):
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
    "filesystem, shared_folder, pattern, expected_file_data",
    [
        (
            {
                "My Shared Folder": {
                    "": [SharedFile(0, 0, 0, 0, 10, 0, 16, "", "Subfolder1")],
                    "Subfolder1\\": [
                        SharedFile(0, 0, 0, 0, 10, 0, 32, "", "My File"),
                        SharedFile(0, 0, 0, 0, 10, 0, 32, "", "File"),
                    ],
                }
            },
            "My Shared Folder",
            ["Subfolder1", "My File"],
            [("\\\\HOSTNAME\\My Shared Folder\\Subfolder1\\My File", "My File")],
        ),
        (
            {
                "My Shared Folder": {
                    "": [
                        SharedFile(0, 0, 0, 0, 10, 0, 16, "", "Subfolder1"),
                        SharedFile(0, 0, 0, 0, 10, 0, 32, "", "file1"),
                    ],
                    "Subfolder1\\": [
                        SharedFile(0, 0, 0, 0, 10, 0, 16, "", "Subfolder2"),
                        SharedFile(0, 0, 0, 0, 10, 0, 16, "", "Subfolder3"),
                        SharedFile(0, 0, 0, 0, 10, 0, 32, "", "file2"),
                    ],
                    "Subfolder1\\Subfolder2\\": [
                        SharedFile(0, 0, 0, 0, 10, 0, 32, "", "file3"),
                        SharedFile(0, 0, 0, 0, 10, 0, 32, "", "file4"),
                    ],
                    "Subfolder1\\Subfolder3\\": [
                        SharedFile(0, 0, 0, 0, 10, 0, 32, "", "file5"),
                    ],
                }
            },
            "My Shared Folder",
            ["Subfolder1", "*folder*", "*ile*"],
            [
                ("\\\\HOSTNAME\\My Shared Folder\\Subfolder1\\Subfolder2\\file3", "file3"),
                ("\\\\HOSTNAME\\My Shared Folder\\Subfolder1\\Subfolder2\\file4", "file4"),
                ("\\\\HOSTNAME\\My Shared Folder\\Subfolder1\\Subfolder3\\file5", "file5"),
            ],
        ),
        (
            {
                "My Shared Folder": {
                    "": [
                        SharedFile(0, 0, 0, 0, 10, 0, 16, "", "Subfolder1"),
                        SharedFile(0, 0, 0, 0, 10, 0, 32, "", "some_file"),
                    ],
                    "Subfolder1\\": [
                        SharedFile(0, 0, 0, 0, 10, 0, 16, "", "Subfolder2"),
                        SharedFile(0, 0, 0, 0, 10, 0, 16, "", "Subfolder3"),
                        SharedFile(0, 0, 0, 0, 10, 0, 32, "", "some_file"),
                    ],
                    "Subfolder1\\Subfolder2\\": [
                        SharedFile(0, 0, 0, 0, 10, 0, 16, "", "Subfolder4"),
                        SharedFile(0, 0, 0, 0, 10, 0, 32, "", "some_file"),
                        SharedFile(0, 0, 0, 0, 10, 0, 32, "", "some_file"),
                    ],
                    "Subfolder1\\Subfolder2\\Subfolder4\\": [
                        SharedFile(0, 0, 0, 0, 10, 0, 32, "", "some_file"),
                    ],
                    "Subfolder1\\Subfolder3\\": [
                        SharedFile(0, 0, 0, 0, 10, 0, 16, "", "Subfolder5"),
                        SharedFile(0, 0, 0, 0, 10, 0, 32, "", "some_file"),
                    ],
                    "Subfolder1\\Subfolder3\\Subfolder5\\": [
                        SharedFile(0, 0, 0, 0, 10, 0, 32, "", "some_file"),
                    ],
                }
            },
            "My Shared Folder",
            ["Subfolder1", "*", "*", "some_file"],
            [
                (
                    "\\\\HOSTNAME\\My Shared Folder\\Subfolder1\\Subfolder2\\Subfolder4\\some_file",
                    "some_file",
                ),
                (
                    "\\\\HOSTNAME\\My Shared Folder\\Subfolder1\\Subfolder3\\Subfolder5\\some_file",
                    "some_file",
                ),
            ],
        ),
        (
            {
                "My Shared Folder": {
                    "": [
                        SharedFile(0, 0, 0, 0, 10, 0, 16, "", "Subfolder1"),
                        SharedFile(0, 0, 0, 0, 10, 0, 32, "", "some_file"),
                    ],
                    "Subfolder1\\": [
                        SharedFile(0, 0, 0, 0, 10, 0, 16, "", "Subfolder2"),
                        SharedFile(0, 0, 0, 0, 10, 0, 16, "", "Subfolder3"),
                        SharedFile(0, 0, 0, 0, 10, 0, 32, "", "some_file"),
                    ],
                    "Subfolder1\\Subfolder2\\": [
                        SharedFile(0, 0, 0, 0, 10, 0, 16, "", "Subfolder4"),
                        SharedFile(0, 0, 0, 0, 10, 0, 32, "", "some_file"),
                    ],
                    "Subfolder1\\Subfolder2\\Subfolder4\\": [
                        SharedFile(0, 0, 0, 0, 10, 0, 32, "", "some_file"),
                    ],
                    "Subfolder1\\Subfolder3\\": [
                        SharedFile(0, 0, 0, 0, 10, 0, 16, "", "Subfolder5"),
                        SharedFile(0, 0, 0, 0, 10, 0, 32, "", "some_file"),
                    ],
                    "Subfolder1\\Subfolder3\\Subfolder5\\": [
                        SharedFile(0, 0, 0, 0, 10, 0, 32, "", "some_file"),
                    ],
                }
            },
            "My Shared Folder",
            ["Subfolder1", "**", "some_file"],
            [
                ("\\\\HOSTNAME\\My Shared Folder\\Subfolder1\\Subfolder2\\some_file", "some_file"),
                (
                    "\\\\HOSTNAME\\My Shared Folder\\Subfolder1\\Subfolder3\\some_file",
                    "some_file",
                ),
            ],
        ),
        (
            {
                "My Shared Folder": {
                    "": [
                        SharedFile(0, 0, 0, 0, 10, 0, 16, "", "Subfolder1"),
                        SharedFile(0, 0, 0, 0, 10, 0, 32, "", "file1"),
                        SharedFile(0, 0, 0, 0, 10, 0, 32, "", "file2"),
                    ],
                }
            },
            "My Shared Folder",
            ["*"],
            [
                ("\\\\HOSTNAME\\My Shared Folder\\file1", "file1"),
                ("\\\\HOSTNAME\\My Shared Folder\\file2", "file2"),
            ],
        ),
        (
            {
                "My Shared Folder": {
                    "": [
                        SharedFile(0, 0, 0, 0, 10, 0, 16, "", "."),
                        SharedFile(0, 0, 0, 0, 10, 0, 16, "", ".."),
                    ],
                    "..": [SharedFile(0, 0, 0, 0, 10, 0, 32, "", "file")],
                }
            },
            "My Shared Folder",
            ["..", "file"],
            [],
        ),
    ],
)
def test_iter_shared_files(
    filesystem: Dict,
    shared_folder: str,
    pattern: List[str],
    expected_file_data: List[Tuple[str, str]],
) -> None:
    conn = MockSMBConnection(filesystem=filesystem)
    files = list(iter_shared_files(conn, "HOSTNAME", shared_folder, pattern))
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
def test_get_all_shared_files(
    patterns: List[str],
    file_data: List[Tuple[str, str]],
    expected_file_data: List[Tuple[str, List[Tuple[str, str]]]],
):
    with mock.patch("cmk.special_agents.agent_smb_share.iter_shared_files", return_value=file_data):
        conn = MockSMBConnection(shares=["SharedFolder1", "SharedFolder2"])
        files_per_pattern = [
            (p, list(f)) for p, f in get_all_shared_files(conn, "HOSTNAME", patterns)
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
def test_get_all_shared_files_errors(
    patterns: List[str],
    expected_error_message: str,
):
    conn = MockSMBConnection()
    with pytest.raises(RuntimeError, match=expected_error_message):
        dict(get_all_shared_files(conn, "HOSTNAME", patterns))


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
def test_smb_share_agent(arg_list, files, expected_result):
    args = parse_arguments(arg_list)

    with mock.patch("cmk.special_agents.agent_smb_share.get_all_shared_files", return_value=files):
        with mock.patch("cmk.special_agents.agent_smb_share.SectionWriter", MockSectionWriter):
            smb_share_agent(args)

    assert MockSectionWriter.writer == expected_result


def test_smb_share_agent_error():
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
def test_smb_share_agent_unsuccessful_connect(mock_connect):
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
def test_smb_share_agent_operation_failure(mock_connect, mock_get_files, mock_write_section):
    mock_write_section.side_effect = OperationFailure("Operation failure happened", [])
    args = parse_arguments(
        ["hostname", "127.0.0.1", "--username", "username", "--password", "password"],
    )
    with pytest.raises(OperationFailure, match="Operation failure happened"):
        smb_share_agent(args)


@mock.patch("cmk.special_agents.agent_smb_share.SMBConnection.connect", return_value=True)
@mock.patch("cmk.special_agents.agent_smb_share.SMBConnection.close")
def test_connect_error(mock_close, mock_connect):
    with pytest.raises(Exception, match="Exception during usage of smb connection"):
        with connect("username", "password", "hostname", "127.0.0.1"):
            raise Exception("Exception during usage of smb connection")

    mock_close.assert_called_once()


@mock.patch("cmk.special_agents.agent_smb_share.special_agent_main")
def test_main(mock_agent):
    assert main() == 0
