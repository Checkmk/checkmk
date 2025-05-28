#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import os
import subprocess
import sys
from collections.abc import Sequence
from typing import Literal, override


def select_matching_packages(version: str, installed_packages: Sequence[str]) -> list[str]:
    raw_version = version[:-4]
    target_package_name = f"{get_edition(version)}-{raw_version}"
    with_version_str = [package for package in installed_packages if target_package_name in package]
    if "p" in raw_version:
        return with_version_str
    if "-" in raw_version:
        return with_version_str
    return [
        package
        for package in with_version_str
        if f"{raw_version}p" not in package and f"{raw_version}-" not in package
    ]


def get_edition(
    omd_version: str,
) -> Literal["raw", "enterprise", "managed", "free", "cloud", "saas", "unknown"]:
    """Returns the long Checkmk Edition name or "unknown" of the given OMD version"""
    parts = omd_version.split(".")
    if parts[-1] == "demo":
        edition_short = parts[-2]
    else:
        edition_short = parts[-1]

    if edition_short == "cre":
        return "raw"
    if edition_short == "cee":
        return "enterprise"
    if edition_short == "cme":
        return "managed"
    if edition_short == "cfe":
        return "free"
    if edition_short == "cce":
        return "cloud"
    if edition_short == "cse":
        return "saas"
    return "unknown"


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
    def get_all_installed_packages(self, verbose: bool) -> list[str]:
        raise NotImplementedError()

    def _execute_uninstall(self, cmd: list[str], verbose: bool) -> None:
        p = self._execute(cmd, verbose)
        output = p.communicate()[0]
        if p.wait() != 0:
            sys.exit("Failed to uninstall package:\n%s" % output)

    def _execute(self, cmd: list[str], verbose: bool) -> subprocess.Popen:
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
    def get_all_installed_packages(self, verbose: bool) -> list[str]:
        p = self._execute(["dpkg", "-l"], verbose)
        output = p.communicate()[0]
        if p.wait() != 0:
            sys.exit("Failed to get all installed packages:\n%s" % output)

        packages: list[str] = []
        for package in output.split("\n"):
            if not package.startswith("ii"):
                continue

            packages.append(package.split()[1])

        return packages


class _PackageManagerRPM(PackageManager):
    def uninstall(self, package_name: str, verbose: bool) -> None:
        self._execute_uninstall(["rpm", "-e", package_name], verbose)

    def get_all_installed_packages(self, verbose: bool) -> list[str]:
        p = self._execute(["rpm", "-qa"], verbose)
        output = p.communicate()[0]

        if p.wait() != 0:
            sys.exit("Failed to find packages:\n%s" % output)

        packages: list[str] = []
        for package in output.split("\n"):
            packages.append(package)

        return packages
