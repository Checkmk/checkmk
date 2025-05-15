#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Consolidate methods which relate to processing version and edition of a Checkmk package."""

import logging
import operator
import os
import re
import time
from collections.abc import Callable
from pathlib import Path
from typing import Final, Self

from packaging.version import Version

from tests.testlib.common.repo import (
    branch_from_env,
    current_base_branch_name,
    current_branch_version,
)
from tests.testlib.utils import version_spec_from_env

from cmk.ccc.version import Edition

logger = logging.getLogger()


class CMKEditionType:
    """Wrap `cmk.ccc.version:Edition` and extend with test-framework functionality.

    This object acts as an interface and wrapper to `Edition` present within the source code.
    `CMKEdition` has been initialized in this module, using this wrapper, to act as an interface
    to the test code.

    Usage:
    - `edition = CMKEdition.CCE/CEE/CME/CRE/CSE`
    - `pkg_edition = CMKEdition(edition) / CMKEdition(CMKEdition.edition_from_text("cloud"))`
    - `pkg_edition.short/long/title`
    - `pkg_edition.is_enterprise_edition()`
    - `pkg_edition = CMKEdition(CMKEdition.from_version_string("2.4.0.cee"))`

    Note:
    Wrapping 'Edition' using inheritance would be easier but not possisble,
    as 'enum.Enum' with existing members must not be subclassed.
    """

    CRE = Edition.CRE
    CEE = Edition.CEE
    CCE = Edition.CCE
    CSE = Edition.CSE
    CME = Edition.CME

    def __init__(self, edition: Edition | None = None) -> None:
        self._edition: type[Edition] | Edition
        self._edition = Edition if not edition else edition

    def __call__(self, edition: Edition) -> "CMKEditionType":
        """Return a new instance, which is initialized with an 'Edition' value."""
        return CMKEditionType(edition)

    @property
    def edition(self) -> Edition:
        if isinstance(self._edition, Edition) and hasattr(self._edition, "value"):
            return self._edition
        raise AttributeError(
            "An `edition` has not been assigned to the object!\n"
            "Use `CMKEdition(CMKEdition.CCE/CEE/...)` to initialize the object with an edition."
        )

    @property
    def short(self) -> str:
        """Return short-form of Checkmk edition."""
        return self.edition.short

    @property
    def long(self) -> str:
        """Return Checkmk edition as string."""
        return self.edition.long

    @property
    def title(self) -> str:
        """Return edition as displayed on Checkmk UI."""
        return self.edition.title

    def is_managed_edition(self) -> bool:
        return self.edition is self.CME

    def is_enterprise_edition(self) -> bool:
        return self.edition is self.CEE

    def is_raw_edition(self) -> bool:
        return self.edition is self.CRE

    def is_cloud_edition(self) -> bool:
        return self.edition is self.CCE

    def is_saas_edition(self) -> bool:
        return self.edition is self.CSE

    def edition_from_text(self, value: str) -> Edition:
        """Parse text and return an Edition.

        'short' and 'long' forms of edition strings are accepted. Example,
        'cee', 'enterprise', 'cloud'.
        """
        excp = ValueError()
        try:
            edition = self.from_long_edition(value)
        except RuntimeError as excp_short:
            excp.add_note(str(excp_short))
            try:
                edition = getattr(self, value.upper())
            except AttributeError as excp_long:
                excp.add_note(str(excp_long))
                excp.add_note(
                    f"String: '{value}' neither matches 'short' nor 'long' edition formats!"
                )
                raise excp
        return edition

    def from_long_edition(self, text: str) -> Edition:
        return self._edition.from_long_edition(text)

    def from_version_string(self, text: str) -> Edition:
        return self._edition.from_version_string(text)


# import this in other modules, rather than 'CMKEditionType'.
CMKEdition: Final = CMKEditionType()


# It's ok to make it currently only work on debian based distros
class CMKVersion:
    """
    Compare versions without timestamps.
    >>> CMKVersion("2.0.0p12") < CMKVersion("2.1.0p12")
    True
    >>> CMKVersion("2.3.0p3") > CMKVersion("2.3.0")
    True
    >>> CMKVersion("2.3.0") >= CMKVersion("2.3.0")
    True
    >>> CMKVersion("2.2.0p11") <= CMKVersion("2.2.0p11")
    True

    Only one of the versions has a timestamp (only daily builds have a timestamp)
    >>> CMKVersion("2.2.0-2024.05.05") > CMKVersion("2.2.0p26")
    True
    >>> CMKVersion("2.2.0-2024.05.05") < CMKVersion("2.3.0p3")
    True
    >>> CMKVersion("2.1.0-2024.05.05") != CMKVersion("2.1.0p18")
    True

    Both the versions have a timestamp (patch versions are always `0`)
    >>> CMKVersion("2.3.0-2024.05.05") > CMKVersion("2.2.0-2024.05.05")
    True
    >>> CMKVersion("2.2.0-2024.05.05") < CMKVersion("2.2.0-2024.05.10")
    True
    """

    DEFAULT = "default"
    DAILY = "daily"
    TIMESTAMP_FORMAT = r"%Y.%m.%d"

    def __init__(
        self,
        version_spec: str,
        branch: str = current_base_branch_name(),
        branch_version: str = current_branch_version(),
    ) -> None:
        self.version_spec: Final = version_spec
        self.version_rc_aware: Final = self._version(version_spec, branch, branch_version)
        self.version: Final = re.sub(r"-rc(\d+)", "", self.version_rc_aware)
        self.semantic: Final = (
            _semantic_match.group(0)
            if (_semantic_match := re.match(r"\d+\.\d+\.\d+", self.version))
            else branch_version
        )
        self.branch: Final = branch
        self.branch_version: Final = branch_version

    @staticmethod
    def _get_default_version() -> str:
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
            return CMKVersion._get_default_version()

        if version_spec.lower() == "git":
            raise RuntimeError(
                "The VERSION='GIT' semantic has been deprecated for system tests. If you want to"
                " patch your omd version with your local changes from the git repository, you need"
                " to manually f12 the corresponding directories."
            )

        if ".cee" in version_spec or ".cre" in version_spec:
            raise Exception("Invalid version. Remove the edition suffix!")
        return version_spec

    def is_release_candidate(self) -> bool:
        return self.version != self.version_rc_aware

    def __repr__(self) -> str:
        return f"CMKVersion([{self.version}][{self.branch}])"

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
        raise TypeError(
            f"Invalid comparison, mismatching types! {type(primary)} != '{type(other)}'."
        )

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


class CMKPackageInfo:
    """Consolidate information about a Checkmk package."""

    def __init__(self, version: CMKVersion, edition: CMKEditionType) -> None:
        self._version = version
        self._edition = edition

    def __str__(self) -> str:
        return self.omd_version()

    def __repr__(self) -> str:
        return (
            "CMKPackageInfo"
            f"([{self._version.version}][{self._edition.long}][{self._version.branch}])"
        )

    @property
    def version(self) -> CMKVersion:
        return self._version

    @property
    def edition(self) -> CMKEditionType:
        return self._edition

    def is_installed(self) -> bool:
        return os.path.exists(self.version_path())

    def version_path(self) -> str:
        return "/omd/versions/%s" % self.version_directory()

    def version_directory(self) -> str:
        return self.omd_version()

    def omd_version(self) -> str:
        return f"{self._version.version}.{self._edition.short}"


def package_hash_path(version: str, edition: CMKEditionType) -> Path:
    return Path(f"/tmp/cmk_package_hash_{version}_{edition.long}")


def version_from_env(
    *,
    fallback_version_spec: str | None = None,
    fallback_branch: str | Callable[[], str] | None = None,
) -> CMKVersion:
    return CMKVersion(
        version_spec_from_env(fallback_version_spec or CMKVersion.DAILY),
        branch_from_env(env_var="BRANCH", fallback=fallback_branch or current_base_branch_name),
    )


def edition_from_env(fallback: Edition = CMKEdition.CEE) -> CMKEditionType:
    value = os.getenv("EDITION", "")
    try:
        edition = CMKEdition.edition_from_text(value)
    except ValueError:
        edition = fallback
    return CMKEdition(edition)


def get_min_version() -> CMKVersion:
    """Minimal version supported for an update to the daily version of this branch."""
    return CMKVersion(os.getenv("MIN_VERSION", "2.4.0"))
