#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import hashlib
import logging
import operator
import os
import re
import subprocess
import time
from collections.abc import Callable
from pathlib import Path
from typing import Final, NewType, Self

import git
import requests
from packaging.version import Version

from tests.testlib.repo import (
    branch_from_env,
    current_base_branch_name,
    current_branch_version,
    repo_path,
)
from tests.testlib.utils import (
    edition_from_env,
    get_cmk_download_credentials,
    package_hash_path,
    version_spec_from_env,
)

from cmk.utils.version import Edition

logger = logging.getLogger()

PackageUrl = NewType("PackageUrl", str)


# It's ok to make it currently only work on debian based distros
class CMKVersion:
    DEFAULT = "default"
    DAILY = "daily"
    TIMESTAMP_FORMAT = r"%Y.%m.%d"

    def __init__(
        self,
        version_spec: str,
        edition: Edition,
        branch: str = current_base_branch_name(),
        branch_version: str = current_branch_version(),
    ) -> None:
        self.version_spec: Final = version_spec
        self.version_rc_aware: Final = self._version(version_spec, branch, branch_version)
        self.version: Final = re.sub(r"-rc(\d+)", "", self.version_rc_aware)
        self.edition: Final = edition
        self.branch: Final = branch
        self.branch_version: Final = branch_version

    def _get_default_version(self) -> str:
        if os.path.exists("/etc/alternatives/omd"):
            path = os.readlink("/etc/alternatives/omd")
        else:
            path = os.readlink("/omd/versions/default")
        return os.path.split(path)[-1].rsplit(".", 1)[0]

    def _version(self, version_spec: str, branch: str, branch_version: str) -> str:
        if version_spec == self.DAILY:
            date_part = time.strftime(CMKVersion.TIMESTAMP_FORMAT)
            if branch.startswith("sandbox"):
                return f"{date_part}-{branch.replace('/', '-')}"
            return f"{branch_version}-{date_part}"

        if version_spec == self.DEFAULT:
            return self._get_default_version()

        if version_spec.lower() == "git":
            raise RuntimeError(
                "The VERSION='GIT' semantic has been deprecated for system tests. If you want to"
                " patch your omd version with your local changes from the git repository, you need"
                " to manually f12 the corresponding directories."
            )

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

    def is_saas_edition(self) -> bool:
        return self.edition is Edition.CSE

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

    def __repr__(self) -> str:
        return f"CMKVersion([{self.version}][{self.edition.long}][{self.branch}])"

    @staticmethod
    def _checkmk_compare_versions_logic(
        primary: object, other: object, compare_operator: Callable[..., bool]
    ) -> bool:
        if isinstance(primary, CMKVersion) and isinstance(other, CMKVersion):
            primary_version, primary_timestamp = CMKVersion._sanitize_version_spec(primary.version)
            other_version, other_timestamp = CMKVersion._sanitize_version_spec(other.version)
            # if only one of the versions has a timestamp and other does not
            if bool(primary_timestamp) ^ bool(other_timestamp):
                # `==` operation
                if compare_operator is operator.eq:
                    return False
                # `>` and `<` operations
                # disregard patch versions for comparison
                # to avoid `2.2.0p26 > 2.2.0-<timestamp>` resulting in false positive
                primary_version = CMKVersion._disregard_patch_version(primary_version)
                other_version = CMKVersion._disregard_patch_version(other_version)
                if primary_version == other_version:
                    # timestamped builds are the latest versions
                    return (
                        bool(primary_timestamp)
                        if compare_operator is operator.gt
                        else not bool(primary_timestamp)
                    )
                return compare_operator(primary_version, other_version)
            # both versions have timestamps and versions are equal
            if (bool(primary_timestamp) and bool(other_timestamp)) and (
                primary_version == other_version
            ):
                return compare_operator(primary_timestamp, other_timestamp)
            # (timestamps do not exist) or (timestamps exist but versions are unequal)
            return compare_operator(primary_version, other_version)
        raise TypeError(f"Invalid comparison!{type(primary)} is compared to '{type(other)}'.")

    @staticmethod
    def _sanitize_version_spec(version: str) -> tuple[Version, time.struct_time | None]:
        """Sanitize `version_spec` and segregate it into version and timestamp.

        Uses `packaging.version.Version` to wrap Checkmk version.
        """
        _timestamp = None

        # treat `patch-version` as `micro-version`.
        _version = version.replace("0p", "")

        # detect daily builds
        if match := re.search(
            r"([1-9]?\d\.[1-9]?\d\.[1-9]?\d)-([1-9]\d{3}\.[0-1]\d\.[0-3]\d)", _version
        ):
            _version = match.groups()[0]
            _timestamp = time.strptime(match.groups()[1], CMKVersion.TIMESTAMP_FORMAT)
        return Version(_version), _timestamp

    @staticmethod
    def _disregard_patch_version(version: Version) -> Version:
        if version.micro > 0:
            # parse only major.minor version and create a new Version object
            _version = f"{version.major}.{version.minor}.0"
            return Version(_version)
        return version

    def __eq__(self, other: object) -> bool:
        return CMKVersion._checkmk_compare_versions_logic(self, other, operator.eq)

    def __gt__(self, other: Self) -> bool:
        return CMKVersion._checkmk_compare_versions_logic(self, other, operator.gt)

    def __lt__(self, other: Self) -> bool:
        return CMKVersion._checkmk_compare_versions_logic(self, other, operator.lt)

    def __ge__(self, other: Self) -> bool:
        return self > other or self == other

    def __le__(self, other: Self) -> bool:
        return self < other or self == other


def version_from_env(
    *,
    fallback_version_spec: str | None = None,
    fallback_edition: Edition | None = None,
    fallback_branch: str | Callable[[], str] | None = None,
) -> CMKVersion:
    return CMKVersion(
        version_spec_from_env(fallback_version_spec or CMKVersion.DAILY),
        edition_from_env(fallback_edition or Edition.CEE),
        branch_from_env(env_var="BRANCH", fallback=fallback_branch or current_base_branch_name),
    )


def get_min_version(edition: Edition | None = None) -> CMKVersion:
    """Minimal version supported for an update to the daily version of this branch."""
    if edition is None:
        # by default, fallback to edition: CEE
        edition = edition_from_env(fallback=Edition.CEE)
    return CMKVersion(os.getenv("MIN_VERSION", "2.2.0p11"), edition)


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
        if content.startswith("AlmaLinux release 10"):
            return "el10"
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

        logger.info("Downloading from: %s to %s", package_url, temp_package_path)
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


# TODO: Duplicated in cmk_dev.utils.distro_code
def code_name(distro_name: str) -> str:
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
        "almalinux-10": "el10",
        "sles-15sp1": "sles15sp1",
        "sles-15sp2": "sles15sp2",
        "sles-15sp3": "sles15sp3",
        "sles-15sp4": "sles15sp4",
        "sles-12sp5": "sles12sp5",
        "sles-15sp5": "sles15sp5",
        "sles-15sp6": "sles15sp6",
        "sles-15sp7": "sles15sp7",
    }.get(distro_name):
        return code
    raise RuntimeError(f"Unknown distro: {distro_name}")


def git_tag_exists(version: CMKVersion) -> bool:
    return f"v{version.version}" in [str(t) for t in git.Repo(repo_path()).tags]
