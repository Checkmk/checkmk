#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import os
import subprocess
import sys
from typing import override, Protocol


class _Popen(Protocol):
    def communicate(self) -> tuple[str, str]: ...

    @property
    def returncode(self) -> int | None: ...


class PackageManager(abc.ABC):
    @classmethod
    def factory(cls, distro_code: str) -> "PackageManager | None":
        if os.path.exists("/etc/cma"):
            return None

        if distro_code.startswith("el") or distro_code.startswith("sles"):
            return _PackageManagerRPM()
        return _PackageManagerDEB()

    @abc.abstractmethod
    def uninstall(self, package_name: str, verbose: bool) -> None:
        raise NotImplementedError()

    @abc.abstractmethod
    def get_package(self, version_path: str, verbose: bool) -> list[str]:
        raise NotImplementedError()

    def _execute(self, cmd: list[str], verbose: bool) -> subprocess.Popen[str]:
        if verbose:
            sys.stdout.write("Executing: " + subprocess.list2cmdline(cmd) + "\n")

        return subprocess.Popen(
            cmd,
            shell=False,
            close_fds=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
        )


class _PackageManagerDEB(PackageManager):
    @override
    def uninstall(self, package_name: str, verbose: bool) -> None:
        p = self._execute(["apt-get", "-y", "purge", package_name], verbose)
        stdout, stderr = p.communicate()
        if p.returncode != 0:
            sys.stderr.write("Failed to uninstall package:\n")
            sys.stderr.write(f"stdout:\n {stdout}\n")
            sys.stderr.write(f"stderr:\n {stderr}\n")
            sys.exit(1)

    @override
    def get_package(self, version_path: str, verbose: bool) -> list[str]:
        process = self._execute(["dpkg", "-S", version_path], verbose)
        return self._get_package(process, version_path)

    @classmethod
    def _get_package(cls, process: _Popen, version_path: str) -> list[str]:
        stdout, stderr = process.communicate()
        if process.returncode != 0:
            sys.stderr.write(f"Failed to get packages owning {version_path}\n")
            sys.stderr.write(f"stdout:\n {stdout}\n")
            sys.stderr.write(f"stderr:\n {stderr}\n")
            return []
        return stdout.split(":", maxsplit=1)[0].split(",")


class _PackageManagerRPM(PackageManager):
    @override
    def uninstall(self, package_name: str, verbose: bool) -> None:
        p = self._execute(["rpm", "-e", package_name], verbose)
        stdout, stderr = p.communicate()
        if p.returncode != 0:
            sys.stderr.write("Failed to uninstall package:\n")
            sys.stderr.write(f"stdout:\n {stdout}\n")
            sys.stderr.write(f"stderr:\n {stderr}\n")
            sys.exit(1)

    @override
    def get_package(self, version_path: str, verbose: bool) -> list[str]:
        process = self._execute(["rpm", "-qf", version_path], verbose)
        return self._get_package(process, version_path)

    @classmethod
    def _get_package(cls, process: _Popen, version_path: str) -> list[str]:
        stdout, stderr = process.communicate()
        if process.returncode != 0:
            sys.stderr.write(f"Failed to get packages owning {version_path}\n")
            sys.stderr.write(f"stdout:\n {stdout}\n")
            sys.stderr.write(f"stderr:\n {stderr}\n")
            return []
        return stdout.splitlines()
