#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest

from cmk.ccc.exceptions import MKGeneralException

from cmk.utils.backup.targets import TargetId
from cmk.utils.backup.targets.local import LocalTarget


class TestLocalTarget:
    def test_check_ready_ok(self):
        LocalTarget(
            TargetId(""),
            {
                "path": "/",
                "is_mountpoint": False,
            },
        ).check_ready()

    @pytest.mark.parametrize(
        ["path", "expected_error_msg"],
        [
            ("/a", "not exist"),
            ("/a/", "not exist"),
            ("/a/b", "not exist"),
            ("a/b", "canonical"),
            ("/a//", "not exist"),
            ("/a//b", "not exist"),
            ("/a/.", "not exist"),
            ("/a/./b", "not exist"),
            ("/a/..", "canonical"),
            ("/a/b/../../etc/shadow", "canonical"),
        ],
    )
    def test_check_ready_error(
        self,
        monkeypatch: pytest.MonkeyPatch,
        path: Path,
        expected_error_msg: str,
    ) -> None:
        monkeypatch.setattr("os.getcwd", lambda: "/test")
        monkeypatch.setattr("os.path.islink", lambda x: False)
        with pytest.raises(
            MKGeneralException,
            match=expected_error_msg,
        ):
            LocalTarget(
                TargetId(""),
                {
                    "path": str(path),
                    "is_mountpoint": False,
                },
            ).check_ready()
