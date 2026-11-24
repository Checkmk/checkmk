# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import difflib
import functools
import os
import subprocess
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from pathlib import Path
from typing import Literal, override

INSTALLATION_PATH = Path("/omd/versions")


class Edition(StrEnum):
    # old
    OLD_RAW = "cre"
    OLD_ENTERPRISE = "cee"
    OLD_MANAGED = "cme"
    OLD_CLOUD = "cce"
    OLD_SAAS = "cse"
    # new
    COMMUNITY = "community"
    PRO = "pro"
    ULTIMATEMT = "ultimatemt"
    ULTIMATE = "ultimate"
    CLOUD = "cloud"


def _map_edition_to_package_name(edition: Edition) -> str:
    match edition:
        case Edition.OLD_RAW:
            return "raw"
        case Edition.OLD_ENTERPRISE:
            return "enterprise"
        case Edition.OLD_MANAGED:
            return "managed"
        case Edition.OLD_CLOUD:
            return "cloud"
        case Edition.OLD_SAAS:
            return "saas"
        case _:
            return edition.value


def edition_value_from_package_name(package_edition: str) -> str:
    """Map a debian package edition (e.g. "enterprise") to the OMD edition value (e.g. "cee").

    Inverse of :func:`_map_edition_to_package_name`. Unknown names are returned
    unchanged. Note that "cloud" is ambiguous between the old (cce) and new (cloud)
    editions; the new edition wins to match the package naming for current versions.
    """
    by_package_name = {_map_edition_to_package_name(edition): edition.value for edition in Edition}
    return by_package_name.get(package_edition, package_edition)


@functools.total_ordering
class BaseVersion:
    def __init__(self, major: int, minor: int, patch: int = 0):
        self.major = major
        self.minor = minor
        self.patch = patch

    @classmethod
    def from_str(cls, version_str: str) -> BaseVersion:
        """Create a Version object from a string.
        This method expects the version string to be in the format 'd.d[.d]'.
        """
        match version_str.split("."):
            case (major_str, minor_str):
                return cls(major=int(major_str), minor=int(minor_str))
            case (major_str, minor_str, patch_str):
                return cls(major=int(major_str), minor=int(minor_str), patch=int(patch_str))
            case _:
                raise ValueError("Version must be in 'd.d[.d]' format")

    @override
    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"

    @override
    def __eq__(self, other: object) -> bool:
        if isinstance(other, BaseVersion):
            return (self.major, self.minor, self.patch) == (
                other.major,
                other.minor,
                other.patch,
            )
        return NotImplemented

    def __lt__(self, other: object) -> bool:  # type: ignore[return]  # noqa: RET503
        if isinstance(other, BaseVersion):
            return (self.major, self.minor, self.patch) < (
                other.major,
                other.minor,
                other.patch,
            )

    def iso_format(self) -> str:
        """Return the version in ISO format."""
        return self.__str__()

    @property
    def download_folder_name(self) -> str:
        """Get the download folder name for this version."""
        return self.__str__()


class VersionWithPatch(BaseVersion):
    def __init__(self, base_version: BaseVersion, patch_type: Literal["p", "b"], patch: int):
        self.base_version = base_version
        self.patch_type = patch_type
        self.patch = patch

    @override
    def __str__(self) -> str:
        if self.patch_type == "p" and self.patch == 0:
            return f"{self.base_version}"
        return f"{self.base_version}{self.patch_type}{self.patch}"

    @override
    def iso_format(self) -> str:
        return self.__str__()


class VersionWithReleaseCandidate(BaseVersion):
    def __init__(
        self,
        base_version: BaseVersion,
        patch_type: Literal["p", "b"],
        patch: int,
        rc: int,
        folder_suffix: str = "",
    ):
        self.base_version = base_version
        self.patch_type: Literal["p", "b"] = patch_type
        self.patch = patch
        self.rc = rc
        self.folder_suffix = folder_suffix

    @override
    def __str__(self) -> str:
        return f"{self.base_version}{self.patch_type}{self.patch}"

    @override
    def iso_format(self) -> str:
        return self.__str__()

    @property
    @override
    def download_folder_name(self) -> str:
        return f"{self.base_version}{self.patch_type}{self.patch}-rc{self.rc}{self.folder_suffix}"


class VersionWithReleaseDate(BaseVersion):
    def __init__(self, base_version: BaseVersion, release_date: date):
        self.base_version = base_version
        self.release_date = release_date

    @override
    def __str__(self) -> str:
        return f"{self.base_version}-{self.release_date.strftime('%Y.%m.%d')}"

    @override
    def __repr__(self) -> str:
        return self.__str__()

    @override
    def iso_format(self) -> str:
        return f"{self.base_version}-{self.release_date.isoformat()}"


class PartialVersion(BaseVersion):
    """Represents a version that release date is not known."""


class GitVersion:
    def __init__(self, branch: str, commit_hash: str):
        self.branch = branch
        self.commit_hash = commit_hash

    @override
    def __str__(self) -> str:
        return f"git:{self.branch}:{self.commit_hash}"


Version = (
    BaseVersion
    | VersionWithPatch
    | VersionWithReleaseDate
    | PartialVersion
    | GitVersion
    | VersionWithReleaseCandidate
)


class CMKPackage:
    """Represents a Checkmk package."""

    def __init__(
        self,
        version: VersionWithPatch
        | VersionWithReleaseDate
        | BaseVersion
        | VersionWithReleaseCandidate,
        edition: Edition,
        distro_codename: str = "noble",
        arch: str = "amd64",
    ):
        self.version = version
        self.edition = edition
        self.distro_codename = distro_codename
        self.arch = arch

    @property
    def omd_version(self) -> str:
        """Get the OMD version string."""
        return f"{self.version}.{self.edition.value}"

    @property
    def package_raw_name(self) -> str:
        """Get the package name."""
        base = f"check-mk-{_map_edition_to_package_name(self.edition)}-"
        if isinstance(self.version, VersionWithReleaseCandidate):
            return f"{base}{self.version.base_version}{self.version.patch_type}{self.version.patch}"
        return f"{base}{self.version}"

    @property
    def package_name(self) -> str:
        """Get the package name."""
        return f"{self.package_raw_name}_0.{self.distro_codename}_{self.arch}.deb"

    @property
    def base_version(self) -> BaseVersion:
        """Get the base version."""
        match self.version:
            case VersionWithPatch(base_version=base_version, patch_type=_, patch=_):
                return base_version
            case VersionWithReleaseDate(base_version=base_version, release_date=_):
                return base_version
            case VersionWithReleaseCandidate(
                base_version=base_version, patch_type=_, patch=_, rc=_
            ):
                return base_version
            case BaseVersion():
                return self.version

    @override
    def __str__(self) -> str:
        return f"{self.version}.{self.edition.value}"

    @override
    def __repr__(self) -> str:
        return self.__str__()


@dataclass
class PartialCMKPackage:
    version: str

    def similarity(self, other: str) -> float:
        return difflib.SequenceMatcher(None, self.version, other).ratio()


def omd_config_set(site_name: str, config_key: str, config_value: str) -> None:
    try:
        result = subprocess.run(
            [
                "sudo",
                "omd",
                "config",
                site_name,
                "set",
                config_key,
                config_value,
            ],
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            f"Could not set configuration {config_key} to {config_value} "
            f"for site {site_name}\n{e.stderr}"
        ) from e

    if result.stderr:
        raise RuntimeError(result.stderr.decode("utf-8").strip())


def omd_config_get(site_name: str, param: str) -> str | None:
    try:
        return subprocess.run(
            [
                "sudo",
                "su",
                site_name,
                "-c",
                f"omd config show {param}",
            ],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.split("\n")[0]

    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            f"Could not get configuration {param} for site {site_name}\n{e.stderr}"
        ) from e


def omd_hook_exists(
    omd_version: str, hook_name: str, *, installation_path: Path = INSTALLATION_PATH
) -> bool:
    """Whether the installed version ships the given omd config hook."""
    return os.path.isfile(installation_path / omd_version / "lib/omd/hooks" / hook_name)


def omd_init_script_exists(
    omd_version: str, service_name: str, *, installation_path: Path = INSTALLATION_PATH
) -> bool:
    """Whether the installed version ships the init script of the given site service."""
    return os.path.isfile(installation_path / omd_version / "skel/etc/init.d" / service_name)
