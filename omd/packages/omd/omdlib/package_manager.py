#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import subprocess
import sys
from typing import Protocol


class _CommandError:
    def __init__(self, msg: str = "") -> None:
        self.msg = msg

    def show(self, prefix: str) -> str:
        return f"{prefix}:\n{self.msg}" if self.msg else f"{prefix}\n"


class _CompletedProcess(Protocol):
    stdout: str
    stderr: str
    returncode: int


def _run(
    cmd: list[str], verbose: bool, _completed_run: _CompletedProcess | None = None
) -> str | _CommandError:
    if verbose:
        sys.stdout.write("Executing: " + subprocess.list2cmdline(cmd) + "\n")
    if _completed_run is not None:
        result: _CompletedProcess = _completed_run
    else:
        result = subprocess.run(
            cmd,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            encoding="utf-8",
            check=False,
        )
    if result.returncode != 0:
        return _CommandError(f"stdout:\n {result.stdout}\nstderr:\n {result.stderr}\n")
    return result.stdout


def _stream(cmd: list[str]) -> _CommandError | None:
    sys.stdout.write("Executing: " + subprocess.list2cmdline(cmd) + "\n")

    result = subprocess.run(cmd, stdin=subprocess.DEVNULL, encoding="utf-8", check=False)
    if result.returncode != 0:
        return _CommandError()
    return None


class PackageManager(Protocol):
    def uninstall(self, package_name: str, verbose: bool) -> None: ...

    def get_package(
        self, version_path: str, verbose: bool, _completed_run: _CompletedProcess | None = None
    ) -> list[str]: ...


def package_manager_factory(distro_code: str) -> PackageManager | None:
    if os.path.exists("/etc/cma"):
        return None

    if distro_code.startswith("el") or distro_code.startswith("sles"):
        return _PackageManagerRPM()
    return _PackageManagerDEB()


class _PackageManagerDEB:
    def uninstall(self, package_name: str, verbose: bool) -> None:
        cmd = ["apt-get", "-y", "purge", package_name]
        error = _stream(cmd) if verbose else _run(cmd, verbose)
        if isinstance(error, _CommandError):
            sys.exit(error.show("Failed to uninstall package"))

    def get_package(
        self, version_path: str, verbose: bool, _completed_run: _CompletedProcess | None = None
    ) -> list[str]:
        result = _run(["dpkg", "-S", version_path], verbose, _completed_run)
        if isinstance(result, _CommandError):
            sys.exit(result.show(f"Failed to get packages owning {version_path}"))
        return result.split(":", maxsplit=1)[0].split(",")


class _PackageManagerRPM:
    def uninstall(self, package_name: str, verbose: bool) -> None:
        cmd = ["rpm", "-e", package_name]
        error = _stream(cmd) if verbose else _run(cmd, verbose)
        if isinstance(error, _CommandError):
            sys.exit(error.show("Failed to uninstall package"))

    def get_package(
        self, version_path: str, verbose: bool, _completed_run: _CompletedProcess | None = None
    ) -> list[str]:
        result = _run(["rpm", "-qf", version_path], verbose, _completed_run)
        if isinstance(result, _CommandError):
            sys.exit(result.show(f"Failed to get packages owning {version_path}"))
        return result.splitlines()
