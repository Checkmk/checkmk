#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from omdlib.package_manager import _PackageManagerDEB


class _StubCompletedProcess:
    def __init__(self, stdout: str, stderr: str, returncode: int) -> None:
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode


def test_get_package_ignores_warning_deb() -> None:
    result = _PackageManagerDEB().get_package(
        "/opt/omd/versions/2.4.0p17.cre",
        verbose=False,
        _completed_run=_StubCompletedProcess(
            "check-mk-raw-2.4.0p17: /opt/omd/versions/2.4.0p17.cre\n",
            "dpkg-query: warning: files list file for package 'openssh-blacklist' missing\n",
            0,
        ),
    )
    assert result == ["check-mk-raw-2.4.0p17"]
