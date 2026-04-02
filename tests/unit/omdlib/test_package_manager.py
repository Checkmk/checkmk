#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from omdlib.package_manager import _PackageManagerDEB


class _StubPopen:
    def __init__(self, stdout: str, stderr: str, returncode: int) -> None:
        self._stdout = stdout
        self._stderr = stderr
        self._returncode = returncode
        self.returncode: int | None = None

    def communicate(self) -> tuple[str, str]:
        self.returncode = self._returncode
        return self._stdout, self._stderr


def test_get_package_ignores_warning_deb() -> None:
    result = _PackageManagerDEB._get_package(
        _StubPopen(
            "check-mk-raw-2.4.0p17: /opt/omd/versions/2.4.0p17.cre\n",
            "dpkg-query: warning: files list file for package 'openssh-blacklist' missing\n",
            0,
        ),
        "/opt/omd/versions/2.4.0p17.cre",
    )
    assert result == ["check-mk-raw-2.4.0p17"]
