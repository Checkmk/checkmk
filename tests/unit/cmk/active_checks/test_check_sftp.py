#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.active_checks.check_sftp import Args, file_available, get_paths, parse_arguments, PathDict


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

    with pytest.raises(TypeError):
        get_paths(
            opt_put_local="some value",
            opt_get_local=None,
            opt_put_remote=None,
            opt_get_remote=None,
            opt_timestamp=None,
            omd_root="/omdroot",
            working_dir="/workdir",
        )

    with pytest.raises(TypeError):
        get_paths(
            opt_put_local=None,
            opt_get_local=None,
            opt_put_remote=None,
            opt_get_remote="some value",
            opt_timestamp=None,
            omd_root="/omdroot",
            working_dir="/workdir",
        )


def test_file_available() -> None:
    class _SFTPMock:
        def __init__(self) -> None:
            self.listed_dirs: list[str] = []

        def listdir(self, dir_: str) -> list[str]:
            self.listed_dirs.append(dir_)
            return []

    sftp_mock = _SFTPMock()
    assert not file_available("opt_put_local", None, sftp_mock, "/workdir")  # type: ignore[arg-type]
    assert sftp_mock.listed_dirs == ["/workdir/None"]
