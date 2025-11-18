#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import os
import subprocess
import sys
from typing import override


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

    def _execute_uninstall(self, cmd: list[str], verbose: bool) -> None:
        p = self._execute(cmd, verbose)
        output = p.communicate()[0]
        if p.wait() != 0:
            sys.exit("Failed to uninstall package:\n%s" % output)

    def _execute(self, cmd: list[str], verbose: bool) -> subprocess.Popen[str]:
        if verbose:
            sys.stdout.write("Executing: " + subprocess.list2cmdline(cmd))

        return subprocess.Popen(
            cmd,
            shell=False,
            close_fds=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            encoding="utf-8",
        )


class _PackageManagerDEB(PackageManager):
    @override
    def uninstall(self, package_name: str, verbose: bool) -> None:
        self._execute_uninstall(["apt-get", "-y", "purge", package_name], verbose)

    @override
    def get_package(self, version_path: str, verbose: bool) -> list[str]:
        process = self._execute(["dpkg", "-S", version_path], verbose)
        stdout = process.communicate()[0]
        if process.wait() != 0:
            sys.stderr.write(f"Failed to get packages owning {version_path}\n {stdout}")
            return []
        return stdout.split(":", maxsplit=1)[0].split(",")


class _PackageManagerRPM(PackageManager):
    def uninstall(self, package_name: str, verbose: bool) -> None:
        self._execute_uninstall(["rpm", "-e", package_name], verbose)

    @override
    def get_package(self, version_path: str, verbose: bool) -> list[str]:
        process = self._execute(["rpm", "-qf", version_path], verbose)
        stdout = process.communicate()[0]
        if process.wait() != 0:
            sys.stderr.write(f"Failed to get packages owning {version_path}\n {stdout}")
            return []
        return stdout.splitlines()
