#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Is executed in container from git top level as working directory to install
the desired Checkmk version"""

import os
import sys
import logging
import subprocess
import abc
from typing import List, Optional, Dict

# Explicitly check for Python 3 (which is understood by mypy)
if sys.version_info[0] >= 3:
    from pathlib import Path  # pylint: disable=import-error
else:
    from pathlib2 import Path  # pylint: disable=import-error

import requests

# Make the testlib available
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from testlib.utils import (
    current_base_branch_name,
    add_python_paths,
)
from testlib.version import CMKVersion
from testlib.utils import get_cmk_download_credentials

logging.basicConfig(level=logging.INFO, format='%(asctime)-15s %(filename)s %(message)s')
logger = logging.getLogger()


def main():
    add_python_paths()

    version_spec = os.environ.get("VERSION", CMKVersion.DAILY)
    edition = os.environ.get("EDITION", CMKVersion.CEE)
    branch = os.environ.get("BRANCH", current_base_branch_name())

    logger.info("Version: %s, Edition: %s, Branch: %s", version_spec, edition, branch)
    version = CMKVersion(version_spec, edition, branch)

    if version.is_installed():
        logger.info("Version %s is already installed. Terminating.")
        return 0

    manager = ABCPackageManager.factory()
    manager.install(version.version, version.edition())

    if not version.is_installed():
        logger.error("Failed not install version")

    return 0


def get_omd_distro_name():
    # type: () -> str
    if os.path.exists("/etc/cma"):
        raise NotImplementedError()

    rh = Path("/etc/redhat-release")
    if rh.exists():
        content = rh.open().read()
        if content.startswith("CentOS release 6"):
            return "el6"
        if content.startswith("CentOS Linux release 7"):
            return "el7"
        if content.startswith("CentOS Linux release 8"):
            return "el8"
        raise NotImplementedError()

    os_spec = _read_os_release()
    if not os_spec:
        raise NotImplementedError()

    if os_spec["NAME"] == "SLES":
        return "sles%s" % os_spec["VERSION"].lower().replace("-", "")

    if os_spec["NAME"] in ["Ubuntu", "Debian GNU/Linux"]:
        if os_spec["VERSION_ID"] == "14.04":
            return "trusty"
        if os_spec["VERSION_ID"] == "8":
            return "jessie"
        return os_spec["VERSION_CODENAME"]

    raise NotImplementedError()


def _read_os_release():
    # type: () -> Optional[Dict[str, str]]
    os_release = Path("/etc/os-release")
    if not os_release.exists():
        return None

    os_spec = {}
    with os_release.open() as f:
        for l in f:
            if "=" not in l:
                continue
            key, val = l.strip().split("=", 1)
            os_spec[key] = val.strip("\"")

    return os_spec


class ABCPackageManager(abc.ABC):
    @classmethod
    def factory(cls):
        # type: () -> ABCPackageManager
        distro_name = get_omd_distro_name()
        logger.info("Distro: %s", distro_name)

        if distro_name.startswith("sles"):
            return PackageManagerSuSE(distro_name)

        if distro_name.startswith("el"):
            return PackageManagerRHEL(distro_name)

        return PackageManagerDEB(distro_name)

    def __init__(self, distro_name):
        # type: (str) -> None
        self.distro_name = distro_name

    @classmethod
    def _is_debuntu(cls):
        # type: () -> bool
        return Path("/etc/debian_version").exists()

    def install(self, version, edition):
        # type: (str, str) -> None
        package_name = self._package_name(edition, version)
        build_system_path = self._build_system_package_path(version, package_name)

        if build_system_path.exists():
            logger.info("Install from build system package (%s)", build_system_path)
            self._install_package(build_system_path)

        else:
            logger.info("Install from download portal")
            package_path = self._download_package(version, package_name)
            self._install_package(package_path)
            os.unlink(package_path)

    @abc.abstractmethod
    def _package_name(self, edition, version):
        # type: (str, str) -> str
        raise NotImplementedError()

    def _build_system_package_path(self, version, package_name):
        # type: (str, str) -> Path
        return Path("/bauwelt/download").joinpath(version, package_name)

    def _download_package(self, version, package_name):
        # type: (str, str) -> Path
        temp_package_path = Path("/tmp", package_name)
        package_url = self._package_url(version, package_name)

        logger.info("Downloading from: %s", package_url)
        response = requests.get(  # nosec
            package_url, auth=get_cmk_download_credentials(), verify=False)
        response.raise_for_status()

        with open(temp_package_path, "wb") as f:
            f.write(response.content)

        return temp_package_path

    def _package_url(self, version, package_name):
        # type: (str, str) -> str
        return "https://checkmk.com/support/%s/%s" % (version, package_name)

    @abc.abstractmethod
    def _install_package(self, package_path):
        # type: (Path) -> None
        raise NotImplementedError()

    def _execute(self, cmd):
        # type: (List[str]) -> None
        logger.debug("Executing: %s", subprocess.list2cmdline(list(map(str, cmd))))

        # Workaround to fix package installation issues
        # - systemctl in docker leads to: Failed to connect to bus: No such file or directory
        if Path("/.dockerenv").exists():
            systemctl = Path("/bin/systemctl")
            if systemctl.exists():
                systemctl.unlink()
            systemctl.symlink_to("/bin/true")

        if os.geteuid() != 0:
            cmd.insert(0, "sudo")

        p = subprocess.Popen(cmd, shell=False, close_fds=True, encoding="utf-8")
        if p.wait() >> 8 != 0:
            raise Exception("Failed to install package")


class PackageManagerDEB(ABCPackageManager):
    def _package_name(self, edition, version):
        return "check-mk-%s-%s_0.%s_amd64.deb" % (edition, version, self.distro_name)

    def _install_package(self, package_path):
        self._execute(["/usr/bin/gdebi", "--non-interactive", package_path])


class ABCPackageManagerRPM(ABCPackageManager):
    def _package_name(self, edition, version):
        return "check-mk-%s-%s-%s-38.x86_64.rpm" % (edition, version, self.distro_name)


class PackageManagerSuSE(ABCPackageManagerRPM):
    def _install_package(self, package_path):
        # TODO: Cleanup --no-gpg-checks
        self._execute(["zypper", "--no-gpg-checks", "in", "-y", package_path])


class PackageManagerRHEL(ABCPackageManagerRPM):
    def _install_package(self, package_path):
        self._execute(["/usr/bin/yum", "-y", "install", package_path])


if __name__ == "__main__":
    sys.exit(main())
