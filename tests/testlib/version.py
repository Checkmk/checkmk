#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Consolidate methods which relate to processing version and edition of a Checkmk package."""

import logging
import os
import re
import time
from collections.abc import Callable
from pathlib import Path
from typing import Final, Self

from tests.testlib.common.repo import (
    branch_from_env,
    current_base_branch_name,
    current_branch_version,
)
from tests.testlib.utils import version_spec_from_env

from cmk.ccc.version import (
    Edition,
    Version,
    versions_compatible,
    VersionsCompatible,
    VersionsIncompatible,
)
from cmk.ccc.version import edition as cmk_edition

logger = logging.getLogger()


class TypeCMKEdition:
    """Wrap `cmk.ccc.version:Edition` and extend with test-framework functionality.

    This object acts as an interface and wrapper to `Edition` present within the source code.
    `CMKEdition` has been initialized in this module, using this wrapper, to act as an interface
    to the test code.

    Usage:
    - `edition = CMKEdition.CCE/CEE/CME/CRE/CSE`
    - `pkg_edition = CMKEdition(edition)`
    - `pkg_edition = CMKEdition.edition_from_text("cloud")`
    - `pkg_edition = CMKEdition.from_version_string("2.4.0.cee")`
    - `pkg_edition.short/long/title`
    - `pkg_edition.is_enterprise_edition()`

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
        self._edition_data: type[Edition] | Edition
        self._edition_data = Edition if not edition else edition

    def __call__(self, edition: Edition) -> "TypeCMKEdition":
        """Return a new instance, which is initialized with an 'Edition' value."""
        return TypeCMKEdition(edition)

    def __eq__(self, item: object) -> bool:
        """Enable comparison of two `TypeCMKEdition` objects.

        Only compare objects which have an instantiated `edition_data` attribute.
        """
        if isinstance(item, self.__class__):
            return self.edition_data == item.edition_data
        raise TypeError(f"Expected comparison with another '{self.__class__.__name__}' object!")

    @property
    def edition_data(self) -> Edition:
        """Return an instantiated attribute of type `Edition`.

        Raises:
            AttributeError: raised when the edition is not instantiated.
        """
        if isinstance(self._edition_data, Edition) and hasattr(self._edition_data, "value"):
            return self._edition_data
        raise AttributeError(
            "An `edition` has not been assigned to the object!\n"
            "Use `CMKEdition(CMKEdition.CCE/CEE/...)` to initialize the object with an edition."
        )

    @property
    def short(self) -> str:
        """Return short-form of Checkmk edition."""
        return self.edition_data.short

    @property
    def long(self) -> str:
        """Return Checkmk edition as string."""
        return self.edition_data.long

    @property
    def title(self) -> str:
        """Return edition as displayed on Checkmk UI."""
        return self.edition_data.title

    def is_managed_edition(self) -> bool:
        return self.edition_data is self.CME

    def is_enterprise_edition(self) -> bool:
        return self.edition_data is self.CEE

    def is_raw_edition(self) -> bool:
        return self.edition_data is self.CRE

    def is_cloud_edition(self) -> bool:
        return self.edition_data is self.CCE

    def is_saas_edition(self) -> bool:
        return self.edition_data is self.CSE

    def edition_from_text(self, value: str) -> "TypeCMKEdition":
        """Parse Checkmk edition from short or long form of Checkmk edition texts.

        Wraps the method `Edition::from_long_edition`.

        Args:
            value (str): Text corresponding to short / long form of Checkmk editions.
                Example: 'cee', 'enterprise', 'cloud'

        Raises:
            excp: `ValueError` when the text can not be parsed.

        Returns:
            TypeCMKEdition: Object specific to the parsed Checkmk edition.
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
        return TypeCMKEdition(edition)

    def edition_from_path(self, omd_root: Path) -> "TypeCMKEdition":
        """Parse Checkmk edition using the path of a site's home directory.

        Args:
            omd_root (Path): Path of a site's home directory; '/omd/sites/<sitename>',
                as initialized within `OMD_ROOT` environment variable in a site.

        Returns:
            TypeCMKEdition: Object specific to the parsed Checkmk edition.
        """
        return TypeCMKEdition(cmk_edition(omd_root))

    def from_long_edition(self, text: str) -> Edition:
        """Deprecated; use `CMKEdition.edition_from_text` instead.

        Parse edition from long-form of edition text and wrap it in an object.
        Example of long-form of edition text: 'enterprise'.
        """
        return self._edition_data.from_long_edition(text)

    def from_version_string(self, text: str) -> "TypeCMKEdition":
        """Parse edition from a Checkmk version string.

        Args:
            text (str): Checkmk version string.
                Example of cloud edition: '2.4.0-2025.05.15.cce'.

        Returns:
            TypeCMKEdition: Object specific to the parsed Checkmk edition.
        """
        return TypeCMKEdition(self._edition_data.from_version_string(text))


# import this in other modules, rather than 'TypeCMKEdition'.
CMKEdition: Final = TypeCMKEdition()


# It's ok to make it currently only work on debian based distros
class CMKVersion:
    """Holds an instance of `cmk.ccc.version::Version`.

    This object acts as an interface to `cmk.ccc.version::Version`. Additionally,
    `CMKVersion` encapsualtes version-centric actions within this object. Like,
    + `versions_compatible`
    """

    # pre-defined version specs
    DEFAULT = "default"
    DAILY = "daily"
    TIMESTAMP_FORMAT = r"%Y.%m.%d"

    def __init__(
        self,
        version_spec: str,
        branch: str = current_base_branch_name(),
        branch_version: str = current_branch_version(),
    ) -> None:
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

        self.version_spec: Final[str] = version_spec
        self._version_raw: Final[str] = self._convert_spec_to_version(
            version_spec, branch, branch_version
        )

        self.version_data: Final = Version.from_str(self._version_raw)
        self.version_rc_aware: Final[str] = self.version_data.version_rc_aware

        self.version: Final[str] = self.version_data.version_without_rc
        self.semantic: Final[str] = (
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

    def _convert_spec_to_version(self, version_spec: str, branch: str, branch_version: str) -> str:
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
        return bool(self.version_data.release_candidate.value)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}([{self.version}][{self.branch}])"

    def _check_instance(self, other: object) -> None:
        if not isinstance(other, self.__class__):
            raise TypeError(f"Expected comparison with another '{self.__class__.__name__}' object!")

    def __eq__(self, other: object) -> bool:
        self._check_instance(other)
        return self.version_data.__eq__(getattr(other, "version_data"))

    def __gt__(self, other: Self) -> bool:
        self._check_instance(other)
        return self.version_data.__gt__(other.version_data)

    def __lt__(self, other: Self) -> bool:
        self._check_instance(other)
        return self.version_data.__lt__(other.version_data)

    def __ge__(self, other: Self) -> bool:
        self._check_instance(other)
        return self.version_data.__ge__(other.version_data)

    def __le__(self, other: Self) -> bool:
        self._check_instance(other)
        return self.version_data.__le__(other.version_data)

    def is_update_compatible(
        self, target_version: "CMKVersion"
    ) -> VersionsCompatible | VersionsIncompatible:
        """Validate whether present version can be updated to target version.

        Args:
            target_version (CMKVersion): Object corresponding to the target version.

        Returns:
            VersionsCompatible | VersionsIncompatible:
                Object which collects compatibility status and corresponding reason.
        """
        return versions_compatible(self.version_data, target_version.version_data)


class CMKPackageInfo:
    """Consolidate information about a Checkmk package."""

    def __init__(self, version: CMKVersion, edition: TypeCMKEdition) -> None:
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
    def edition(self) -> TypeCMKEdition:
        return self._edition

    def is_installed(self) -> bool:
        return os.path.exists(self.version_path())

    def version_path(self) -> str:
        return "/omd/versions/%s" % self.version_directory()

    def version_directory(self) -> str:
        return self.omd_version()

    def omd_version(self) -> str:
        return f"{self._version.version}.{self._edition.short}"


def package_hash_path(version: str, edition: TypeCMKEdition) -> Path:
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


def edition_from_env(fallback: TypeCMKEdition = CMKEdition(CMKEdition.CEE)) -> TypeCMKEdition:
    value = os.getenv("EDITION", "")
    try:
        edition = CMKEdition.edition_from_text(value)
    except ValueError:
        edition = fallback
    return edition


def get_min_version() -> CMKVersion:
    """Minimal version supported for an update to the daily version of this branch."""
    return CMKVersion(os.getenv("MIN_VERSION", "2.4.0p3"))
