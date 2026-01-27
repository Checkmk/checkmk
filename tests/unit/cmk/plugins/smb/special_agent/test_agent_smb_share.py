#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"
# mypy: disable-error-code="type-arg"

from collections.abc import Mapping, Sequence
from datetime import datetime
from unittest import mock

import pytest
import time_machine
from smb.base import NotConnectedError, SharedFile  # type: ignore[import-untyped,unused-ignore]
from smb.smb_structs import OperationFailure  # type: ignore[import-untyped,unused-ignore]

from cmk.password_store.v1_unstable import Secret
from cmk.plugins.smb.special_agent.agent_smb_share import (
    connect,
    File,
    get_all_shared_files,
    iter_shared_files,
    parse_arguments,
    smb_share_agent,
    SMBShareAgentError,
)

SHARED_FOLDER = "My Shared Folder"
HOST_NAME = "HOSTNAME"
SHARE_BASE = f"\\\\{HOST_NAME}\\{SHARED_FOLDER}"


def file_(name: str) -> SharedFile:
    return SharedFile(0, 0, 0, 0, 10, 0, 32, "", name)


def folder(name: str) -> SharedFile:
    return SharedFile(0, 0, 0, 0, 10, 0, 16, "", name)


class MockShare:
    def __init__(self, name: str) -> None:
        self._name = name

    @property
    def name(self) -> str:
        return self._name


class MockSMBConnection:
    def __init__(
        self,
        *args: object,
        filesystem: Mapping[str, Mapping[str, list[SharedFile]]] | None = None,
        shares: Sequence[str] | None = None,
        is_direct_tcp: bool = False,
        disallowed_paths: list[str] | None = None,
    ) -> None:
        self.filesystem = filesystem
        self.shares = shares
        self.is_direct_tcp = is_direct_tcp
        self.disallowed_paths = disallowed_paths if disallowed_paths else []

    @staticmethod
    def connect(*args):
        return True

    def listPath(self, shared_folder: str, path: str) -> list[SharedFile]:
        if path in self.disallowed_paths:
            raise Exception(
                f"The agent tries to descend into {path} but is not allowed to! "
                f"Keep the agent as lazy as possible in order to have a performant execution!"
            )

        if self.filesystem is None or shared_folder not in self.filesystem:
            return []
        result = self.filesystem[shared_folder].get(path)
        assert result is not None
        return result

    def listShares(self) -> list[MockShare]:
        if not self.shares:
            return []
        return [MockShare(s) for s in self.shares]

    def close(self):
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
    assert args.password.reveal() == "password"
    assert args.patterns == [
        "\\\\HOSTNAME\\Share Folder 1\\*.log",
        "\\\\HOSTNAME\\Share Folder 2\\file.txt",
    ]


@pytest.mark.parametrize(
    "filesystem, disallowed_paths, pattern, recursive, expected_file_data",
    [
        pytest.param(
            {
                SHARED_FOLDER: {
                    "": [folder("Subfolder1")],
                    "Subfolder1\\": [
                        file_("My File"),
                        file_("File"),
                    ],
                }
            },
            [],
            ["Subfolder1", "My File"],
            False,
            {(f"{SHARE_BASE}\\Subfolder1\\My File", "My File")},
            id="exact pattern for one file to match",
        ),
        pytest.param(
            {
                SHARED_FOLDER: {
                    "": [
                        folder("Subfolder1"),
                        file_("file1"),
                    ],
                    "Subfolder1\\": [
                        folder("Subfolder2"),
                        folder("Subfolder3"),
                        file_("Ordner"),
                        file_("file2"),
                    ],
                    "Subfolder1\\Ordner\\": [],
                    "Subfolder1\\Subfolder2\\": [
                        file_("file3"),
                        file_("file4"),
                    ],
                    "Subfolder1\\Subfolder3\\": [
                        file_("file5"),
                    ],
                }
            },
            ["Subfolder1\\Ordner\\"],
            ["Subfolder1", "*folder*", "*ile*"],
            True,
            {
                (f"{SHARE_BASE}\\Subfolder1\\Subfolder2\\file3", "file3"),
                (f"{SHARE_BASE}\\Subfolder1\\Subfolder2\\file4", "file4"),
                (f"{SHARE_BASE}\\Subfolder1\\Subfolder3\\file5", "file5"),
            },
            id="wildcard in folder- and filename",
        ),
        pytest.param(
            {
                SHARED_FOLDER: {
                    "": [
                        folder("Subfolder1"),
                        file_("some_file"),
                    ],
                    "Subfolder1\\": [
                        folder("Subfolder2"),
                        folder("Subfolder3"),
                        file_("some_file"),
                    ],
                    "Subfolder1\\Subfolder2\\": [
                        folder("Subfolder4"),
                        file_("some_file"),
                        file_("some_file"),
                    ],
                    "Subfolder1\\Subfolder2\\Subfolder4\\": [
                        file_("some_file"),
                    ],
                    "Subfolder1\\Subfolder3\\": [
                        folder("Subfolder5"),
                        file_("some_file"),
                    ],
                    "Subfolder1\\Subfolder3\\Subfolder5\\": [
                        file_("some_file"),
                    ],
                }
            },
            [],
            ["Subfolder1", "*", "*", "some_file"],
            False,
            {
                (
                    f"{SHARE_BASE}\\Subfolder1\\Subfolder2\\Subfolder4\\some_file",
                    "some_file",
                ),
                (
                    f"{SHARE_BASE}\\Subfolder1\\Subfolder3\\Subfolder5\\some_file",
                    "some_file",
                ),
            },
            id="wildcard for 2 folder hierarchies",
        ),
        pytest.param(
            {
                SHARED_FOLDER: {
                    "": [
                        folder("Subfolder1"),
                        folder("do_not_go_here"),
                        file_("some_file"),
                    ],
                    "do_not_go_here\\": [],
                    "Subfolder1\\": [
                        folder("Subfolder2"),
                        folder("Subfolder3"),
                        file_("some_file"),
                    ],
                    "Subfolder1\\Subfolder2\\": [
                        folder("Subfolder4"),
                        file_("some_file"),
                    ],
                    "Subfolder1\\Subfolder2\\Subfolder4\\": [
                        file_("some_file"),
                    ],
                    "Subfolder1\\Subfolder3\\": [
                        folder("Subfolder5"),
                        file_("some_file"),
                    ],
                    "Subfolder1\\Subfolder3\\Subfolder5\\": [
                        file_("some_file"),
                    ],
                }
            },
            ["do_not_go_here\\"],
            ["Subfolder1", "**", "some_file"],
            True,
            {
                (f"{SHARE_BASE}\\Subfolder1\\some_file", "some_file"),
                (f"{SHARE_BASE}\\Subfolder1\\Subfolder2\\some_file", "some_file"),
                (f"{SHARE_BASE}\\Subfolder1\\Subfolder2\\Subfolder4\\some_file", "some_file"),
                (f"{SHARE_BASE}\\Subfolder1\\Subfolder3\\some_file", "some_file"),
                (
                    f"{SHARE_BASE}\\Subfolder1\\Subfolder3\\Subfolder5\\some_file",
                    "some_file",
                ),
            },
            id="recursive search using double star globbing but avoid looking into unneeded folders",
        ),
        pytest.param(
            {
                SHARED_FOLDER: {
                    "": [
                        folder("Subfolder1"),
                        folder("do_not_go_here"),
                        file_("some_file"),
                    ],
                    "do_not_go_here\\": [],
                    "Subfolder1\\": [
                        folder("Subfolder2"),
                        folder("Subfolder3"),
                        file_("some_file"),
                    ],
                    "Subfolder1\\Subfolder2\\": [
                        folder("Subfolder4"),
                        file_("some_file"),
                    ],
                    "Subfolder1\\Subfolder2\\Subfolder4\\": [
                        file_("some_file"),
                    ],
                    "Subfolder1\\Subfolder3\\": [
                        folder("Subfolder5"),
                        file_("some_file"),
                    ],
                    "Subfolder1\\Subfolder3\\Subfolder5\\": [
                        file_("some_file"),
                    ],
                }
            },
            ["do_not_go_here\\"],
            ["Subfolder1", "**", "some_file"],
            False,
            {
                (f"{SHARE_BASE}\\Subfolder1\\Subfolder2\\some_file", "some_file"),
                (f"{SHARE_BASE}\\Subfolder1\\Subfolder3\\some_file", "some_file"),
            },
            id="non-recursive search using double star",
        ),
        pytest.param(
            {
                SHARED_FOLDER: {
                    "": [
                        folder("Subfolder1"),
                        file_("some_file"),
                    ],
                    "Subfolder1\\": [
                        folder("Subfolder2"),
                        folder("Subfolder3"),
                        file_("some_file"),
                    ],
                    "Subfolder1\\Subfolder2\\": [
                        folder("Subfolder4"),
                        file_("some_file"),
                    ],
                    "Subfolder1\\Subfolder2\\Subfolder4\\": [
                        file_("some_file"),
                    ],
                    "Subfolder1\\Subfolder3\\": [
                        folder("Subfolder5"),
                        file_("some_file"),
                    ],
                    "Subfolder1\\Subfolder3\\Subfolder5\\": [
                        file_("some_file"),
                    ],
                }
            },
            [],
            ["Subfolder1", "**", "Subfolder5", "some_file"],
            True,
            {
                (f"{SHARE_BASE}\\Subfolder1\\Subfolder3\\Subfolder5\\some_file", "some_file"),
            },
            id="double star globbing, folder after the double star",
        ),
        pytest.param(
            {
                SHARED_FOLDER: {
                    "": [
                        folder("Subfolder1"),
                        file_("some_file"),
                    ],
                    "Subfolder1\\": [
                        folder("Subfolder2"),
                        folder("Subfolder3"),
                        file_("some_file"),
                    ],
                    "Subfolder1\\Subfolder2\\": [
                        folder("Subfolder4"),
                        file_("some_file"),
                    ],
                    "Subfolder1\\Subfolder2\\Subfolder4\\": [
                        file_("some_file"),
                    ],
                    "Subfolder1\\Subfolder3\\": [
                        folder("Subfolder5"),
                        file_("some_file"),
                    ],
                    "Subfolder1\\Subfolder3\\Subfolder5\\": [
                        file_("some_file"),
                    ],
                }
            },
            [],
            ["Subfolder1", "**", "*"],
            True,
            {
                (f"{SHARE_BASE}\\Subfolder1\\some_file", "some_file"),
                (f"{SHARE_BASE}\\Subfolder1\\Subfolder2\\some_file", "some_file"),
                (f"{SHARE_BASE}\\Subfolder1\\Subfolder2\\Subfolder4\\some_file", "some_file"),
                (f"{SHARE_BASE}\\Subfolder1\\Subfolder3\\some_file", "some_file"),
                (f"{SHARE_BASE}\\Subfolder1\\Subfolder3\\Subfolder5\\some_file", "some_file"),
            },
            id="double star globbing, single star after the double star",
        ),
        pytest.param(
            {
                SHARED_FOLDER: {
                    "": [
                        folder("Subfolder1"),
                        file_("some_file"),
                    ],
                    "Subfolder1\\": [
                        folder("Subfolder2"),
                        folder("Subfolder3"),
                        file_("some_file"),
                    ],
                    "Subfolder1\\Subfolder2\\": [
                        folder("Subfolder4"),
                        file_("some_file"),
                    ],
                    "Subfolder1\\Subfolder2\\Subfolder4\\": [
                        file_("some_file"),
                    ],
                    "Subfolder1\\Subfolder3\\": [
                        folder("Subfolder5"),
                        file_("some_file"),
                    ],
                    "Subfolder1\\Subfolder3\\Subfolder5\\": [
                        folder("Subfolder6"),
                        file_("some_file"),
                    ],
                    "Subfolder1\\Subfolder3\\Subfolder5\\Subfolder6\\": [
                        file_("some_file"),
                    ],
                }
            },
            [],
            ["Subfolder1", "**", "**", "some_file"],
            True,
            {
                (f"{SHARE_BASE}\\Subfolder1\\some_file", "some_file"),
                (f"{SHARE_BASE}\\Subfolder1\\Subfolder2\\some_file", "some_file"),
                (f"{SHARE_BASE}\\Subfolder1\\Subfolder3\\some_file", "some_file"),
                (f"{SHARE_BASE}\\Subfolder1\\Subfolder2\\Subfolder4\\some_file", "some_file"),
                (f"{SHARE_BASE}\\Subfolder1\\Subfolder3\\Subfolder5\\some_file", "some_file"),
                (
                    f"{SHARE_BASE}\\Subfolder1\\Subfolder3\\Subfolder5\\Subfolder6\\some_file",
                    "some_file",
                ),
            },
            id="double star globbing twice",
        ),
        pytest.param(
            {
                SHARED_FOLDER: {
                    "": [
                        folder("Subfolder1"),
                        file_("some_file"),
                    ],
                    "Subfolder1\\": [
                        folder("Subfolder2"),
                        folder("Subfolder3"),
                        file_("some_file"),
                    ],
                    "Subfolder1\\Subfolder2\\": [
                        folder("Subfolder4"),
                        file_("some_file"),
                    ],
                    "Subfolder1\\Subfolder2\\Subfolder4\\": [
                        file_("some_file"),
                    ],
                    "Subfolder1\\Subfolder3\\": [
                        folder("Subfolder5"),
                        file_("some_file"),
                    ],
                    "Subfolder1\\Subfolder3\\Subfolder5\\": [
                        folder("Subfolder6"),
                        file_("some_file"),
                    ],
                    "Subfolder1\\Subfolder3\\Subfolder5\\Subfolder6\\": [
                        file_("some_file"),
                    ],
                }
            },
            [],
            ["Subfolder1", "**", "**", "some_file"],
            False,
            {
                (f"{SHARE_BASE}\\Subfolder1\\Subfolder2\\Subfolder4\\some_file", "some_file"),
                (f"{SHARE_BASE}\\Subfolder1\\Subfolder3\\Subfolder5\\some_file", "some_file"),
            },
            id="non-recursive double star globbing twice",
        ),
        pytest.param(
            {
                SHARED_FOLDER: {
                    "": [
                        folder("Subfolder1"),
                        file_("some_file"),
                    ],
                    "Subfolder1\\": [
                        folder("Subfolder2"),
                        folder("Subfolder3"),
                        file_("some_file"),
                    ],
                    "Subfolder1\\Subfolder2\\": [
                        folder("Subfolder4"),
                        file_("some_file"),
                    ],
                    "Subfolder1\\Subfolder2\\Subfolder4\\": [
                        file_("some_file"),
                    ],
                    "Subfolder1\\Subfolder3\\": [
                        folder("Subfolder5"),
                        file_("some_file"),
                    ],
                    "Subfolder1\\Subfolder3\\Subfolder5\\": [
                        folder("Subfolder6"),
                        file_("some_file"),
                    ],
                    "Subfolder1\\Subfolder3\\Subfolder5\\Subfolder6\\": [
                        folder("Subfolder7"),
                        file_("some_file"),
                    ],
                    "Subfolder1\\Subfolder3\\Subfolder5\\Subfolder6\\Subfolder7\\": [
                        file_("some_file"),
                    ],
                }
            },
            [],
            ["Subfolder1", "**", "Subfolder*", "**", "some_file"],
            True,
            {
                (f"{SHARE_BASE}\\Subfolder1\\Subfolder2\\Subfolder4\\some_file", "some_file"),
                (f"{SHARE_BASE}\\Subfolder1\\Subfolder2\\some_file", "some_file"),
                (
                    f"{SHARE_BASE}\\Subfolder1\\Subfolder3\\Subfolder5\\Subfolder6\\Subfolder7\\some_file",
                    "some_file",
                ),
                (
                    f"{SHARE_BASE}\\Subfolder1\\Subfolder3\\Subfolder5\\Subfolder6\\some_file",
                    "some_file",
                ),
                (f"{SHARE_BASE}\\Subfolder1\\Subfolder3\\Subfolder5\\some_file", "some_file"),
                (f"{SHARE_BASE}\\Subfolder1\\Subfolder3\\some_file", "some_file"),
            },
            id="double star globbing twice, with a folder in between",
        ),
        pytest.param(
            {
                SHARED_FOLDER: {
                    "": [
                        folder("Subfolder1"),
                        file_("file1"),
                        file_("file2"),
                    ],
                    "Subfolder1\\": [
                        file_("file3"),
                    ],
                }
            },
            ["Subfolder1\\"],
            ["*"],
            True,
            {
                (f"{SHARE_BASE}\\file1", "file1"),
                (f"{SHARE_BASE}\\file2", "file2"),
            },
            id="match everything with *",
        ),
        pytest.param(
            {
                SHARED_FOLDER: {
                    "": [
                        folder("Subfolder1"),
                        file_("file1"),
                        file_("file2"),
                    ],
                    "Subfolder1\\": [
                        file_("file3"),
                    ],
                }
            },
            [],
            ["**"],
            True,
            {
                (f"{SHARE_BASE}\\Subfolder1\\file3", "file3"),
                (f"{SHARE_BASE}\\file1", "file1"),
                (f"{SHARE_BASE}\\file2", "file2"),
            },
            id="match only directories and no files with **",
        ),
        pytest.param(
            {
                SHARED_FOLDER: {
                    "": [
                        folder("sub1"),
                        file_("root.txt"),
                    ],
                    "sub1\\": [
                        folder("sub2"),
                        file_("sub1.txt"),
                    ],
                    "sub1\\sub2\\": [
                        folder("sub3"),
                        file_("sub2.txt"),
                    ],
                    "sub1\\sub2\\sub3\\": [
                        file_("sub3.txt"),
                    ],
                }
            },
            ["sub1\\sub2\\sub3\\"],
            ["sub1", "*", "*.txt"],
            False,
            {
                ("\\\\HOSTNAME\\My Shared Folder\\sub1\\sub2\\sub2.txt", "sub2.txt"),
            },
            id="glob one folder hierarchy and find all files with .txt suffix",
        ),
        pytest.param(
            {
                SHARED_FOLDER: {
                    "": [
                        folder("."),
                        folder(".."),
                    ],
                    "..": [file_("file")],
                }
            },
            [],
            ["..", "file"],
            False,
            set(),
            id="do not look into ..",
        ),
        pytest.param(
            {
                SHARED_FOLDER: {
                    "": [
                        folder("Subfolder1"),
                        file_("file1"),
                        file_("file2"),
                    ],
                    "Subfolder1\\": [
                        file_("file3"),
                    ],
                }
            },
            [],
            ["SUBFOLDER1", "FILE*"],
            True,
            {
                (f"{SHARE_BASE}\\Subfolder1\\file3", "file3"),
            },
            id="ignore case",
        ),
    ],
)
def test_iter_shared_files(
    filesystem: dict,
    disallowed_paths: list[str],
    pattern: list[str],
    recursive: bool,
    expected_file_data: set[tuple[str, str]],
) -> None:
    conn = MockSMBConnection(filesystem=filesystem, disallowed_paths=disallowed_paths)
    files = set(iter_shared_files(conn, HOST_NAME, SHARED_FOLDER, pattern, recursive=recursive))
    file_data = {(f.path, f.file.filename) for f in files}

    assert file_data == expected_file_data


@pytest.mark.parametrize(
    "patterns, file_data, expected_file_data",
    [
        pytest.param(
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
                    {
                        ("path1", "file1"),
                        ("path2", "file2"),
                    },
                ),
            ],
            id="find share files",
        ),
        pytest.param(
            [
                "\\\\HOSTNAME\\sharedfolder1\\Subfolder1\\File1",
            ],
            [
                ("path1", "file1"),
                ("path2", "file2"),
            ],
            [
                (
                    "\\\\HOSTNAME\\sharedfolder1\\Subfolder1\\File1",
                    {
                        ("path1", "file1"),
                        ("path2", "file2"),
                    },
                ),
            ],
            id="ignore case in share name",
        ),
    ],
)
def test_get_all_shared_files(
    patterns: list[str],
    file_data: list[tuple[str, str]],
    expected_file_data: list[tuple[str, set[tuple[str, str]]]],
) -> None:
    with mock.patch(
        "cmk.plugins.smb.special_agent.agent_smb_share.iter_shared_files", return_value=file_data
    ):
        conn = MockSMBConnection(shares=["SharedFolder1", "SharedFolder2"])
        files_per_pattern = list(
            get_all_shared_files(conn, HOST_NAME, patterns, False)  # type: ignore[arg-type,unused-ignore]
        )
        assert files_per_pattern == expected_file_data  # type: ignore[comparison-overlap,unused-ignore]


@pytest.mark.parametrize(
    "patterns, expected_error_message",
    [
        (
            ["\\\\INCORRECT_HOSTNAME\\SharedFolder1\\Subfolder1\\File1"],
            r"Pattern \\\\INCORRECT_HOSTNAME\\SharedFolder1\\Subfolder1\\File1 doesn't match HOSTNAME host name",
        ),
        (
            ["\\\\HOSTNAME\\SharedFolder1\\Subfolder1\\File1"],
            "Share SharedFolder1 doesn't exist on host HOSTNAME",
        ),
    ],
)
def test_get_all_shared_files_errors(
    patterns: list[str],
    expected_error_message: str,
) -> None:
    conn = MockSMBConnection()
    with pytest.raises(SMBShareAgentError, match=expected_error_message):
        dict(get_all_shared_files(conn, HOST_NAME, patterns, False))  # type: ignore[arg-type,unused-ignore]


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
                    {
                        File(
                            "\\Share Folder 1\\smb_share.log",
                            SharedFile(0, 0, 0, 1111111, 100, 0, 16, "", "smb_share.log"),
                        ),
                        File(
                            "\\Share Folder 1\\error.log",
                            SharedFile(0, 0, 0, 1111112, 200, 0, 16, "", "error.log"),
                        ),
                    },
                ),
                (
                    "\\Share Folder 2\\file.txt",
                    [],
                ),
            ],
            (
                "<<<fileinfo:sep(124)>>>\n1641020400\n[[[header]]]\nname|status|size|time\n"
                "[[[content]]]\n\\Share Folder 1\\error.log|ok|200|0\n"
                "\\Share Folder 1\\smb_share.log|ok|100|0\n"
                "\\Share Folder 2\\file.txt|missing\n"
            ),
        )
    ],
)
@mock.patch("cmk.plugins.smb.special_agent.agent_smb_share.SMBConnection", MockSMBConnection)
@time_machine.travel(datetime(2022, 1, 1, 7, 0, 0, 0))
def test_smb_share_agent(
    capsys: pytest.CaptureFixture[str],
    arg_list: Sequence[str] | None,
    files: tuple[str, Sequence[File]],
    expected_result: Sequence[object],
) -> None:
    args = parse_arguments(arg_list)
    with mock.patch(
        "cmk.plugins.smb.special_agent.agent_smb_share.get_all_shared_files", return_value=files
    ):
        smb_share_agent(args)

    assert capsys.readouterr().out == expected_result


def test_smb_share_agent_error(capsys: pytest.CaptureFixture) -> None:
    args = parse_arguments(
        ["hostname", "127.0.0.1", "--username", "username", "--password", "password"],
    )

    with mock.patch(
        "cmk.plugins.smb.special_agent.agent_smb_share.SMBConnection.connect"
    ) as mock_connection:
        mock_connection.side_effect = NotConnectedError
        smb_share_agent(args)
        assert (
            capsys.readouterr().err
            == "Could not connect to the remote host. Check your ip address and remote name."
        )


@mock.patch(
    "cmk.plugins.smb.special_agent.agent_smb_share.SMBConnection.connect", return_value=False
)
def test_smb_share_agent_unsuccessful_connect(
    mock_connect: mock.Mock, capsys: pytest.CaptureFixture
) -> None:
    args = parse_arguments(
        ["hostname", "127.0.0.1", "--username", "username", "--password", "password"],
    )
    smb_share_agent(args)
    assert (
        capsys.readouterr().err
        == "Connection to the remote host was declined. Check your credentials."
    )


@mock.patch("cmk.plugins.smb.special_agent.agent_smb_share.connect")
@mock.patch("cmk.plugins.smb.special_agent.agent_smb_share.get_all_shared_files")
@mock.patch("cmk.plugins.smb.special_agent.agent_smb_share.write_section")
def test_smb_share_agent_operation_failure(
    mock_connect: mock.Mock,
    mock_get_files: mock.Mock,
    mock_write_section: mock.Mock,
    capsys: pytest.CaptureFixture,
) -> None:
    mock_write_section.side_effect = OperationFailure("Operation failure happened", [])
    args = parse_arguments(
        ["hostname", "127.0.0.1", "--username", "username", "--password", "password"],
    )

    smb_share_agent(args)
    assert capsys.readouterr().err == "Operation failure happened"


@mock.patch(
    "cmk.plugins.smb.special_agent.agent_smb_share.SMBConnection.connect", return_value=True
)
@mock.patch("cmk.plugins.smb.special_agent.agent_smb_share.SMBConnection.close")
def test_connect_error(mock_close: mock.Mock, mock_connect: mock.Mock) -> None:
    with pytest.raises(Exception, match="Exception during usage of smb connection"):
        with connect("username", Secret("password"), "hostname", "127.0.0.1"):
            raise Exception("Exception during usage of smb connection")

    mock_close.assert_called_once()


@pytest.mark.parametrize(
    "file1,file2,expected_result",
    [
        pytest.param(
            File(
                "\\Share Folder 1\\smb_share.log",
                SharedFile(0, 0, 0, 1111111, 100, 0, 16, "", "smb_share.log"),
            ),
            File(
                "\\Share Folder 1\\smb_share.log",
                SharedFile(0, 0, 0, 1111112, 101, 0, 16, "", "smb_share.log"),
            ),
            True,
            id="files with the same path",
        ),
        pytest.param(
            File(
                "\\Share Folder 1\\smb_share.log",
                SharedFile(0, 0, 0, 1111111, 100, 0, 16, "", "smb_share.log"),
            ),
            File(
                "\\Share Folder 2\\smb_share.log",
                SharedFile(0, 0, 0, 1111111, 100, 0, 16, "", "smb_share.log"),
            ),
            False,
            id="files with different paths",
        ),
        pytest.param(
            File(
                "\\Share Folder 1\\smb_share.log",
                SharedFile(0, 0, 0, 1111111, 100, 0, 16, "", "smb_share.log"),
            ),
            5,
            False,
            id="comparison with an object of a different type",
        ),
    ],
)
def test_file_comparison(file1: File, file2: File, expected_result: bool) -> None:
    result = file1 == file2
    assert result == expected_result
