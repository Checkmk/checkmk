#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import hashlib
import logging
import os
import subprocess
from pathlib import Path
from typing import NewType

import requests

from tests.testlib.utils import (
    get_cmk_download_credentials,
    package_hash_path,
    run,
)
from tests.testlib.version import CMKVersion, version_from_env

from cmk.ccc.version import Edition

logger = logging.getLogger()

PackageUrl = NewType("PackageUrl", str)

DISTRO_CODES = {
    "cma-4": "cma-4",
    "debian-11": "bullseye",
    "debian-12": "bookworm",
    "ubuntu-22.04": "jammy",
    "ubuntu-23.04": "lunar",
    "ubuntu-23.10": "mantic",
    "ubuntu-24.04": "noble",
    "almalinux-9": "el9",
    "sles-15sp1": "sles15sp1",
    "sles-15sp2": "sles15sp2",
    "sles-15sp3": "sles15sp3",
    "sles-15sp4": "sles15sp4",
    "sles-15sp5": "sles15sp5",
    "sles-15sp6": "sles15sp6",
}


class ABCPackageManager(abc.ABC):
    @classmethod
    def factory(cls, distro_name: str | None = None) -> "ABCPackageManager":
        if not distro_name:
            distro_name = _get_omd_distro_name()
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

    def download(
        self, version: CMKVersion | None = None, target_folder: Path | None = None
    ) -> Path:
        version = version or version_from_env()
        package_name = self.package_name(version.edition, version.version)
        package_url = self.package_url_internal(version.version, package_name)

        target_path = (
            target_folder / package_name if target_folder else self._temp_package_path(package_name)
        )
        if target_path.exists():
            return target_path
        return self._download_package(package_name, package_url, target_path)

    def install(self, version: str, edition: Edition) -> None:
        package_name = self.package_name(edition, version)
        build_system_path = self._build_system_package_path(version, package_name)
        packages_dir = Path(__file__).parent.parent.parent / "package_download"
        if (package_path := packages_dir / package_name).exists():
            logger.info("Install from locally available package %s", package_path)
            self._write_package_hash(version, edition, package_path)
            self._install_package(package_path)

        elif build_system_path.exists():
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

            logger.info("Install from tstbuild or portal (%s)", package_path)
            self._write_package_hash(version, edition, package_path)
            self._install_package(package_path)
            os.unlink(package_path)

    def _write_package_hash(self, version: str, edition: Edition, package_path: Path) -> None:
        pkg_hash = _sha256_file(package_path)
        package_hash_path(version, edition).write_text(f"{pkg_hash}  {package_path.name}\n")

    @abc.abstractmethod
    def package_name(self, edition: Edition, version: str) -> str:
        raise NotImplementedError()

    def _build_system_package_path(self, version: str, package_name: str) -> Path:
        """On Jenkins inside a container the previous built packages get mounted into /packages."""
        return Path("/packages", version, package_name)

    def _temp_package_path(self, package_name: str) -> Path:
        return Path("/tmp", package_name)

    def _download_package(
        self, package_name: str, package_url: PackageUrl, package_path: Path | None = None
    ) -> Path:
        package_path = package_path or self._temp_package_path(package_name)
        logger.info("Downloading from: %s to %s", package_url, package_path)
        response = requests.get(  # nosec
            package_url, auth=get_cmk_download_credentials(), verify=True
        )
        response.raise_for_status()

        with open(package_path, "wb") as f:
            f.write(response.content)

        return package_path

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
                run(["rm", "-f", systemctl.as_posix()], sudo=True)
            run(["ln", "-s", "/bin/true", systemctl.as_posix()], sudo=True)

        if os.geteuid() != 0:
            cmd.insert(0, "sudo")

        try:
            subprocess.run(cmd, shell=False, close_fds=True, encoding="utf-8", check=True)
        except subprocess.CalledProcessError as excp:
            if excp.returncode >> 8 != 0:
                excp.add_note("Failed to install package!")
                raise excp


class PackageManagerDEB(ABCPackageManager):
    def package_name(self, edition: Edition, version: str) -> str:
        return f"check-mk-{edition.long}-{version.split('-rc')[0]}_0.{self.distro_name}_amd64.deb"

    def _install_package(self, package_path: Path) -> None:
        # all dependencies are installed via install-cmk-dependencies.sh in the Dockerfile
        # this step should fail in case additional packages would be required
        self._execute(["dpkg", "-i", package_path])


class ABCPackageManagerRPM(ABCPackageManager):
    def package_name(self, edition: Edition, version: str) -> str:
        return f"check-mk-{edition.long}-{version.split('-rc')[0]}-{self.distro_name}-38.x86_64.rpm"


class PackageManagerSuSE(ABCPackageManagerRPM):
    def _install_package(self, package_path: Path) -> None:
        self._execute(["rpm", "-i", package_path])


class PackageManagerRHEL(ABCPackageManagerRPM):
    def _install_package(self, package_path: Path) -> None:
        self._execute(["rpm", "-i", package_path])


class PackageManagerCMA(PackageManagerDEB):
    def package_name(self, edition: Edition, version: str) -> str:
        return f"check-mk-{edition.long}-{version.split('-rc')[0]}-{self.distro_name.split('-')[1]}-x86_64.cma"


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


# TODO: Duplicated in cmk_dev.utils.distro_code
def code_name(distro_name: str) -> str:
    if code := DISTRO_CODES.get(distro_name):
        return code
    raise RuntimeError(f"Unknown distro: {distro_name}")


def _get_omd_distro_name() -> str:
    if os.path.exists("/etc/cma"):
        raise NotImplementedError()

    rh = Path("/etc/redhat-release")
    if rh.exists():
        content = rh.read_text()
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
