#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import hashlib
import logging
import os
import re
import subprocess
import time
from collections.abc import Callable
from pathlib import Path
from typing import Final, NewType

import requests

from tests.testlib.utils import (
    branch_from_env,
    edition_from_env,
    get_cmk_download_credentials,
    package_hash_path,
    version_spec_from_env,
)

from cmk.utils.version import Edition

logger = logging.getLogger()


# It's ok to make it currently only work on debian based distros
class CMKVersion:
    DEFAULT = "default"
    DAILY = "daily"
    GIT = "git"

    def __init__(self, version_spec: str, edition: Edition, branch: str) -> None:
        self.version_spec: Final = version_spec
        self.version_rc_aware: Final = self._version(version_spec, branch)  # branch_version
        self.version: Final = re.sub(r"-rc(\d+)", "", self.version_rc_aware)
        self.edition: Final = edition
        self.branch: Final = branch

    def _get_default_version(self) -> str:
        if os.path.exists("/etc/alternatives/omd"):
            path = os.readlink("/etc/alternatives/omd")
        else:
            path = os.readlink("/omd/versions/default")
        return os.path.split(path)[-1].rsplit(".", 1)[0]

    def _version(self, version_spec: str, branch: str) -> str:
        if version_spec in (self.DAILY, self.GIT):
            date_part = time.strftime("%Y.%m.%d")
            if branch != "master":
                return f"{branch}-{date_part}"
            return date_part

        if version_spec == self.DEFAULT:
            return self._get_default_version()

        if ".cee" in version_spec or ".cre" in version_spec:
            raise Exception("Invalid version. Remove the edition suffix!")
        return version_spec

    def is_managed_edition(self) -> bool:
        return self.edition is Edition.CME

    def is_enterprise_edition(self) -> bool:
        return self.edition is Edition.CEE

    def is_raw_edition(self) -> bool:
        return self.edition is Edition.CRE

    def is_cloud_edition(self) -> bool:
        return self.edition is Edition.CCE

    def is_release_candidate(self) -> bool:
        return self.version != self.version_rc_aware

    def version_directory(self) -> str:
        return self.omd_version()

    def omd_version(self) -> str:
        return f"{self.version}.{self.edition.short}"

    def version_path(self) -> str:
        return "/omd/versions/%s" % self.version_directory()

    def is_installed(self) -> bool:
        return os.path.exists(self.version_path())


def version_from_env(
    *,
    fallback_version_spec: str | None = None,
    fallback_edition: Edition | None = None,
    fallback_branch: str | Callable[[], str] | None = None,
) -> CMKVersion:
    return CMKVersion(
        version_spec_from_env(fallback_version_spec),
        edition_from_env(fallback_edition),
        branch_from_env(fallback_branch),
    )


def version_gte(version: str, min_version: str) -> bool:
    """Check if the given version is greater than or equal to min_version."""
    # first replace all non-numerical segments by a dot
    # and make sure there are no empty segments
    cmp_version = re.sub("[^0-9.]+", ".", version).replace("..", ".")
    min_version = re.sub("[^0-9]+", ".", min_version).replace("..", ".")

    # now split the segments
    version_pattern = r"[0-9]*(\.[0-9]*)*"
    cmp_version_match = re.match(version_pattern, cmp_version)
    cmp_version_values = cmp_version_match.group().split(".") if cmp_version_match else []
    logger.debug("cmp_version=%s; cmp_version_values=%s", cmp_version, cmp_version_values)
    min_version_match = re.match(version_pattern, min_version)
    min_version_values = min_version_match.group().split(".") if min_version_match else []
    while len(cmp_version_values) < len(min_version_values):
        cmp_version_values.append("0")
    logger.debug("min_version=%s; min_version_values=%s", min_version, min_version_values)

    # compare the version numbers segment by segment
    # if any is lower, return False
    for i, min_val in enumerate(min_version_values):
        if int(cmp_version_values[i]) < int(min_val):
            return False
    return True


def get_omd_distro_name() -> str:
    if os.path.exists("/etc/cma"):
        raise NotImplementedError()

    rh = Path("/etc/redhat-release")
    if rh.exists():
        content = rh.read_text()
        if content.startswith("CentOS release 6"):
            return "el6"
        if content.startswith("CentOS Linux release 7"):
            return "el7"
        if content.startswith("CentOS Linux release 8"):
            return "el8"
        if content.startswith("AlmaLinux release 9"):
            return "el9"
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


def _read_os_release() -> dict[str, str] | None:
    os_release = Path("/etc/os-release")
    if not os_release.exists():
        return None

    os_spec = {}
    with os_release.open() as f:
        for l in f:
            if "=" not in l:
                continue
            key, val = l.strip().split("=", 1)
            os_spec[key] = val.strip('"')

    return os_spec


PackageUrl = NewType("PackageUrl", str)


class ABCPackageManager(abc.ABC):
    @classmethod
    def factory(cls, distro_name: str | None = None) -> "ABCPackageManager":
        if not distro_name:
            distro_name = get_omd_distro_name()
        logger.info("Distro: %s", distro_name)

        if distro_name.startswith("sles"):
            return PackageManagerSuSE(distro_name)

        if distro_name.startswith("el"):
            return PackageManagerRHEL(distro_name)

        if distro_name.startswith("cma"):
            return PackageManagerCMA(distro_name)

        return PackageManagerDEB(distro_name)

    def __init__(self, distro_name: str) -> None:
        self.distro_name = distro_name

    @classmethod
    def _is_debuntu(cls) -> bool:
        return Path("/etc/debian_version").exists()

    def install(self, version: str, edition: Edition) -> None:
        package_name = self.package_name(edition, version)
        build_system_path = self._build_system_package_path(version, package_name)

        if build_system_path.exists():
            logger.info("Install from build system package (%s)", build_system_path)
            self._write_package_hash(version, edition, build_system_path)
            self._install_package(build_system_path)

        else:
            try:
                # Prefer downloading from tstbuild: This is the place where also sandbox builds
                # should be found.
                logger.info("Try install from tstbuild")
                package_path = self._download_package(
                    package_name, self.package_url_internal(version, package_name)
                )
            except requests.exceptions.HTTPError:
                logger.info("Could not Install from tstbuild, trying download portal...")
                package_path = self._download_package(
                    package_name, self.package_url_public(version, package_name)
                )

            self._write_package_hash(version, edition, package_path)
            self._install_package(package_path)
            os.unlink(package_path)

    def _write_package_hash(self, version: str, edition: Edition, package_path: Path) -> None:
        pkg_hash = sha256_file(package_path)
        package_hash_path(version, edition).write_text(f"{pkg_hash}  {package_path.name}\n")

    @abc.abstractmethod
    def package_name(self, edition: Edition, version: str) -> str:
        raise NotImplementedError()

    def _build_system_package_path(self, version: str, package_name: str) -> Path:
        """On Jenkins inside a container the previous built packages get mounted into /packages."""
        return Path("/packages", version, package_name)

    def _download_package(self, package_name: str, package_url: PackageUrl) -> Path:
        temp_package_path = Path("/tmp", package_name)

        logger.info("Downloading from: %s", package_url)
        response = requests.get(  # nosec
            package_url, auth=get_cmk_download_credentials(), verify=False
        )
        response.raise_for_status()

        with open(temp_package_path, "wb") as f:
            f.write(response.content)

        return temp_package_path

    def package_url_public(self, version: str, package_name: str) -> PackageUrl:
        return PackageUrl(f"https://download.checkmk.com/checkmk/{version}/{package_name}")

    def package_url_internal(self, version: str, package_name: str) -> PackageUrl:
        return PackageUrl(f"https://tstbuilds-artifacts.lan.tribe29.com/{version}/{package_name}")

    @abc.abstractmethod
    def _install_package(self, package_path: Path) -> None:
        raise NotImplementedError()

    def _execute(self, cmd: list[str | Path]) -> None:
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

        completed_process = subprocess.run(
            cmd, shell=False, close_fds=True, encoding="utf-8", check=False
        )
        if completed_process.returncode >> 8 != 0:
            raise Exception("Failed to install package")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


class PackageManagerDEB(ABCPackageManager):
    def package_name(self, edition: Edition, version: str) -> str:
        return f"check-mk-{edition.long}-{version}_0.{self.distro_name}_amd64.deb"

    def _install_package(self, package_path: Path) -> None:
        # As long as we do not have all dependencies preinstalled, we need to ensure that the
        # package mirror information are up-to-date
        self._execute(["apt-get", "update"])
        self._execute(["apt", "install", "-y", package_path])


class ABCPackageManagerRPM(ABCPackageManager):
    def package_name(self, edition: Edition, version: str) -> str:
        return f"check-mk-{edition.long}-{version}-{self.distro_name}-38.x86_64.rpm"


class PackageManagerSuSE(ABCPackageManagerRPM):
    def _install_package(self, package_path: Path) -> None:
        self._execute(["zypper", "in", "-y", package_path])


class PackageManagerRHEL(ABCPackageManagerRPM):
    def _install_package(self, package_path: Path) -> None:
        self._execute(["/usr/bin/yum", "-y", "install", package_path])


class PackageManagerCMA(PackageManagerDEB):
    def package_name(self, edition: Edition, version: str) -> str:
        return f"check-mk-{edition.long}-{version}-{self.distro_name.split('-')[1]}-x86_64.cma"


# TODO: Duplicated in cmk_dev.utils.distro_code
def code_name(distro_name):
    if code := {
        "cma-3": "cma-3",
        "cma-4": "cma-4",
        "debian-10": "buster",
        "debian-11": "bullseye",
        "debian-12": "bookworm",
        "ubuntu-20.04": "focal",
        "ubuntu-22.04": "jammy",
        "ubuntu-23.04": "lunar",
        "ubuntu-24.04": "noble",
        "centos-7": "el7",
        "centos-8": "el8",
        "almalinux-9": "el9",
        "sles-15sp1": "sles15sp1",
        "sles-15sp2": "sles15sp2",
        "sles-15sp3": "sles15sp3",
        "sles-15sp4": "sles15sp4",
        "sles-12sp5": "sles12sp5",
        "sles-15sp5": "sles15sp5",
        "sles-15sp6": "sles15sp6",
    }.get(distro_name):
        return code
    raise RuntimeError(f"Unknown distro: {distro_name}")
