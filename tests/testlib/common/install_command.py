#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Run the generated agent install commands against a fake curl and sudo.

InstallCommandSuite holds the tests shared by every edition; a test module only
subclasses it and passes in the install commands of its edition. This module is
not assert-rewritten, so every assertion carries its own message.
"""

import subprocess
from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import asdict
from pathlib import Path
from typing import Protocol

from cmk.shared_typing.agent_slideout import AgentInstallCmds

_FAKE_CURL = """#!/bin/sh
while [ $# -gt 0 ]; do
    [ "$1" = -o ] && out=$2
    [ "$1" = --write-out ] && fmt=$2
    shift
done
printf '%s' "$FAKE_BODY" > "$out"
[ "$fmt" = '%{http_code}' ] && printf '%s' "$FAKE_STATUS"
exit "$FAKE_EXIT"
"""

_FAKE_SUDO = """#!/bin/sh
echo "$*" >> "$SUDO_LOG"
"""

_DOWNLOAD_ENDPOINT_MARKER = "download_by"

_API_ERROR = '{"title": "Agent hash not found", "detail": "No baked agent"}'


class FakeInstallHost:
    def __init__(self, work_dir: Path) -> None:
        self.work_dir = work_dir
        self._bin_dir = work_dir / "bin"
        self._sudo_log = work_dir / "sudo.log"

    def run(
        self, cmd: str, *, status: str, body: str, curl_exit: int = 0
    ) -> subprocess.CompletedProcess[str]:
        self._bin_dir.mkdir(exist_ok=True)
        for name, script in (("curl", _FAKE_CURL), ("sudo", _FAKE_SUDO)):
            (self._bin_dir / name).write_text(script)
            (self._bin_dir / name).chmod(0o755)
        return subprocess.run(
            ["sh", "-c", cmd],
            cwd=self.work_dir,
            env={
                "PATH": f"{self._bin_dir}:/usr/bin:/bin",
                "FAKE_STATUS": status,
                "FAKE_BODY": body,
                "FAKE_EXIT": str(curl_exit),
                "SUDO_LOG": str(self._sudo_log),
            },
            capture_output=True,
            text=True,
            check=False,
        )

    def sudo_calls(self) -> list[str]:
        if not self._sudo_log.exists():
            return []
        return self._sudo_log.read_text().splitlines()


class _Metafunc(Protocol):
    @property
    def fixturenames(self) -> Sequence[str]: ...

    def parametrize(
        self, argnames: str, argvalues: Sequence[str], *, ids: Sequence[str]
    ) -> None: ...


class InstallCommandSuite(ABC):
    @abstractmethod
    def install_cmds(self) -> AgentInstallCmds: ...

    def _unix_download_commands(self) -> dict[str, str]:
        return {
            name: cmd
            for name, cmd in asdict(self.install_cmds()).items()
            if cmd and _DOWNLOAD_ENDPOINT_MARKER in cmd and not name.startswith("windows")
        }

    def pytest_generate_tests(self, metafunc: _Metafunc) -> None:
        downloads = self._unix_download_commands()
        installs = {name: cmd for name, cmd in downloads.items() if "sudo" in cmd}
        for fixture, cmds in (("download_cmd", downloads), ("install_cmd", installs)):
            if fixture in metafunc.fixturenames:
                metafunc.parametrize(fixture, list(cmds.values()), ids=list(cmds))

    def test_failed_download_prints_the_api_error_and_installs_nothing(
        self, download_cmd: str, tmp_path: Path
    ) -> None:
        host = FakeInstallHost(tmp_path)

        result = host.run(download_cmd, status="404", body=_API_ERROR)

        assert result.returncode != 0, result
        assert "No baked agent" in result.stdout, result
        assert host.sudo_calls() == [], host.sudo_calls()

    def test_interrupted_download_prints_no_package_and_installs_nothing(
        self, download_cmd: str, tmp_path: Path
    ) -> None:
        host = FakeInstallHost(tmp_path)

        result = host.run(download_cmd, status="200", body="half a package", curl_exit=18)

        assert result.returncode != 0, result
        assert "half a package" not in result.stdout, result
        assert host.sudo_calls() == [], host.sudo_calls()

    def test_successful_download_is_installed(self, install_cmd: str, tmp_path: Path) -> None:
        host = FakeInstallHost(tmp_path)

        result = host.run(install_cmd, status="200", body="agent package")

        assert result.returncode == 0, result
        package = host.sudo_calls()[-1].split()[-1]
        assert (tmp_path / package).read_text() == "agent package", package
