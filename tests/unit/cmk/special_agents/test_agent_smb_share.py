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

from cmk.special_agents.agent_smb_share import (
    connect,
    File,
    get_all_shared_files,
    iter_shared_files,
    parse_arguments,
    smb_share_agent,
)


class MockSMBConnection:
    def __init__(self, *args, filesystem=None):
        self.filesystem = filesystem

    @staticmethod
    def connect(*args):
        return True

    def listPath(self, shared_folder: str, path: str) -> List[SharedFile]:
        if shared_folder not in self.filesystem:
            return []
        return self.filesystem[shared_folder].get(path)

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
            "Share Folder 1",
            "Share Folder 2",
            "--username",
            "username",
            "--password",
            "password",
            "--port",
            "139",
            "--patterns",
            "\\Share Folder 1\\*.log",
            "\\Share Folder 2\\file.txt",
        ]
    )
    assert args.hostname == "hostname"
    assert args.ip_address == "127.0.0.1"
    assert args.username == "username"
    assert args.password == "password"
    assert args.share_names == ["Share Folder 1", "Share Folder 2"]
    assert args.port == 139
    assert args.patterns == ["\\Share Folder 1\\*.log", "\\Share Folder 2\\file.txt"]


@pytest.mark.parametrize(
    "filesystem, shared_folder, path, pattern, expected_file_data",
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
            "",
            "\\My Shared Folder\\Subfolder1\\My File",
            [("\\My Shared Folder\\Subfolder1\\My File", "My File")],
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
                        SharedFile(0, 0, 0, 0, 10, 0, 32, "", "file2"),
                    ],
                    "Subfolder1\\Subfolder2\\": [
                        SharedFile(0, 0, 0, 0, 10, 0, 32, "", "file3"),
                        SharedFile(0, 0, 0, 0, 10, 0, 32, "", "file4"),
                    ],
                }
            },
            "My Shared Folder",
            "",
            "\\My Shared Folder\\Subfolder1\\Subfolder2\\*ile*",
            [
                ("\\My Shared Folder\\Subfolder1\\Subfolder2\\file3", "file3"),
                ("\\My Shared Folder\\Subfolder1\\Subfolder2\\file4", "file4"),
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
            "",
            "\\My Shared Folder\\*",
            [
                ("\\My Shared Folder\\file1", "file1"),
                ("\\My Shared Folder\\file2", "file2"),
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
            "",
            "\\My Shared Folder\\..\\file",
            [],
        ),
    ],
)
def test_iter_shared_files(
    filesystem: Dict,
    shared_folder: str,
    path: str,
    pattern: str,
    expected_file_data: List[Tuple[str, str]],
) -> None:
    conn = MockSMBConnection(filesystem=filesystem)
    files = list(iter_shared_files(conn, shared_folder, pattern, subdir=path))
    file_data = [(f.path, f.file.filename) for f in files]

    assert file_data == expected_file_data


@pytest.mark.parametrize(
    "share_folders, patterns, file_data, expected_file_data",
    [
        (
            ["SharedFolder1", "SharedFolder2"],
            ["\\SharedFolder1\\Subfolder1\\File1", "\\SharedFolder2\\Subfolder2\\File2"],
            [
                ("path1", "file1"),
                ("path2", "file2"),
            ],
            [
                (
                    "\\SharedFolder1\\Subfolder1\\File1",
                    [
                        ("path1", "file1"),
                        ("path2", "file2"),
                        ("path1", "file1"),
                        ("path2", "file2"),
                    ],
                ),
                (
                    "\\SharedFolder2\\Subfolder2\\File2",
                    [
                        ("path1", "file1"),
                        ("path2", "file2"),
                        ("path1", "file1"),
                        ("path2", "file2"),
                    ],
                ),
            ],
        ),
    ],
)
def test_get_all_shared_files(
    share_folders: List[str],
    patterns: List[str],
    file_data: List[Tuple[str, str]],
    expected_file_data: List[Tuple[str, List[Tuple[str, str]]]],
):
    with mock.patch("cmk.special_agents.agent_smb_share.iter_shared_files", return_value=file_data):
        files_per_pattern = get_all_shared_files(None, share_folders, patterns)
        assert list(files_per_pattern) == expected_file_data


@pytest.mark.parametrize(
    "arg_list, files, expected_result",
    [
        (
            [
                "hostname",
                "127.0.0.1",
                "username",
                "password",
                "Share Folder 1",
                "--port",
                "139",
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
        [
            "hostname",
            "127.0.0.1",
            "username",
            "password",
            "Share Folder 1",
        ],
    )

    with mock.patch("cmk.special_agents.agent_smb_share.SMBConnection.connect") as mock_connection:
        mock_connection.side_effect = NotConnectedError
        with pytest.raises(
            RuntimeError,
            match="Could not connect to the remote host. Check your ip address, port and remote name.",
        ):
            smb_share_agent(args)


@mock.patch("cmk.special_agents.agent_smb_share.SMBConnection.connect", return_value=False)
def test_smb_share_agent_unsuccessful_connect(mock_connect):
    args = parse_arguments(
        [
            "hostname",
            "127.0.0.1",
            "username",
            "password",
            "Share Folder 1",
        ],
    )

    with pytest.raises(
        RuntimeError, match="Connection to the remote host was declined. Check your credentials."
    ):
        smb_share_agent(args)


@mock.patch("cmk.special_agents.agent_smb_share.SMBConnection.connect", return_value=True)
@mock.patch("cmk.special_agents.agent_smb_share.SMBConnection.close")
def test_smb_share_agent_connect(mock_close, mock_connect):
    with pytest.raises(Exception, match="Exception during usage of smb connection"):
        with connect("username", "password", "hostname", "127.0.0.1", 139):
            raise Exception("Exception during usage of smb connection")

    mock_close.assert_called_once()
