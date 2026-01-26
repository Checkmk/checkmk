#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Check_MK's library for code used by different components of Check_MK.

This library is currently handled as internal module of Check_MK and
does not offer stable APIs. The code may change at any time."""

from __future__ import annotations

__version__ = "2.4.0p21"

import enum
import functools
import os
import re
import sys
import time
from collections.abc import Sequence
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Final, Literal, NamedTuple, Self

from cmk.ccc.crash_reporting import VersionInfo
from cmk.ccc.site import get_omd_config


class _EditionValue(NamedTuple):
    short: str
    long: str
    title: str


class Edition(enum.Enum):
    CRE = _EditionValue("cre", "raw", "Checkmk Raw Edition")
    CEE = _EditionValue("cee", "enterprise", "Checkmk Enterprise Edition")
    CCE = _EditionValue("cce", "cloud", "Checkmk Cloud Edition")
    CSE = _EditionValue("cse", "saas", "Checkmk Cloud (SaaS)")
    CME = _EditionValue("cme", "managed", "Checkmk Managed Services Edition")

    @classmethod
    def from_version_string(cls, raw: str) -> Edition:
        return cls[raw.split(".")[-1].upper()]

    @classmethod
    def from_long_edition(cls, long: str) -> Edition:
        for e in cls:
            if e.value.long == long:
                return e
        raise RuntimeError(f"Unknown long edition: {long}")

    @property
    def title(self) -> str:
        return self.value.title

    @property
    def short(self) -> str:
        return self.value.short

    @property
    def long(self) -> str:
        return self.value.long


@cache
def omd_version(omd_root: Path) -> str:
    version_link = omd_root / "version"
    return version_link.resolve().name


@cache
def edition(omd_root: Path) -> Edition:
    try:
        return Edition.from_version_string(omd_version(omd_root))
    except KeyError:
        # Without this fallback CI jobs may fail.
        # The last job known to fail was we the building of the sphinx documentation
        return Edition.CRE


def is_cma() -> bool:
    return os.path.exists("/etc/cma/cma.conf")


def edition_has_enforced_licensing(ed: Edition, /) -> bool:
    return ed in (Edition.CME, Edition.CCE)


def edition_has_license_scheduler(ed: Edition, /) -> bool:
    return ed in (Edition.CME, Edition.CCE, Edition.CEE)


def edition_supports_nagvis(ed: Edition, /) -> bool:
    return ed is not Edition.CSE


def mark_edition_only(feature_to_mark: str, exclusive_to: Sequence[Edition]) -> str:
    """
    >>> mark_edition_only("Feature", [Edition.CRE])
    'Feature (Raw Edition)'
    >>> mark_edition_only("Feature", [Edition.CEE])
    'Feature (Enterprise Edition)'
    >>> mark_edition_only("Feature", [Edition.CCE])
    'Feature (Cloud Edition)'
    >>> mark_edition_only("Feature", [Edition.CME])
    'Feature (Managed Services Edition)'
    >>> mark_edition_only("Feature", [Edition.CCE, Edition.CME])
    'Feature (Cloud Edition, Managed Services Edition)'
    """
    return (
        f"{feature_to_mark} ({', '.join([e.title.removeprefix('Checkmk ') for e in exclusive_to])})"
    )


# Version string: <major>.<minor>.<sub><vtype><patch>-<year>.<month>.<day>
#                 [------ base -------][-- build ---]-[------ date ------]
# A version string may consist of the three parts "base", "build" and "date".
# A version string must contain at least one of the parts "base" and "date", while the following
# combinations are possible:
#
# _StableVersion:           <base>              e.g. 1.2.3
# _BetaVersion,             <base><build>       e.g. 1.2.3b4
# _InnovationVersion.       <base><build>       e.g. 1.2.3i4
# _PatchVersion:            <base><build>       e.g. 1.2.3p4
# _MasterDailyVersion:      <date>              e.g. 2021.12.24
# _StableDailyVersion:      <base>-<date>       e.g. 1.2.3-2021.12.24


class ReleaseType(enum.IntEnum):
    """
    Type of a release.

    We differentiate between:
    - innovation (`i`)
    - beta (`b`)
    - patch (`p`)
    - daily (`daily`)

    Without such a specification we fall back to `na`.

    If you want to know more head to https://docs.checkmk.com/latest/en/cmk_versions.html
    """

    i = 0
    b = 1
    na = 2
    p = 3
    daily = 4

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}.{self.name}"


@dataclass(order=True)
class BuildDate:
    year: int
    month: int
    day: int

    def __str__(self) -> str:
        return f"{self.year:04}.{self.month:02}.{self.day:02}"


@dataclass
class _ReleaseCandidate:
    value: int | None

    def __lt__(self, other: _ReleaseCandidate) -> bool:
        match self.value, other.value:
            case None, None:
                return False
            case int() as this, int() as that:
                return this < that
            case _:
                raise ValueError(
                    "This comparision can only be evaluated by looking at the git history: "
                    "We cannot tell if a release candidate was released as an official release (without the rc suffix)."
                )


@dataclass
class _ReleaseMeta:
    value: str | None

    def __str__(self) -> str:
        return f"{self.value}"


@dataclass(order=True)
class _Release:
    release_type: ReleaseType
    value: int | BuildDate

    def suffix(self) -> str:
        if self.release_type is ReleaseType.na:
            return ""
        if self.release_type is ReleaseType.daily:
            return f"-{self.value}"
        return f"{self.release_type.name}{self.value}"

    def is_unspecified(self) -> bool:
        return self.release_type is ReleaseType.na

    @classmethod
    def unspecified(cls) -> Self:
        return cls(ReleaseType.na, 0)


@dataclass(order=True, frozen=True)
class _BaseVersion:
    major: int
    minor: int
    sub: int

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.sub}"


@functools.total_ordering
class Version:
    # Regular expression patterns
    _PAT_BASE = r"([1-9]?\d)\.([1-9]?\d)\.([1-9]?\d)"  # e.g. "2.1.0"
    _PAT_DATE = r"([1-9]\d{3})\.([0-1]\d)\.([0-3]\d)"  # e.g. "2021.12.24"
    _PAT_BUILD = r"([bip])(\d+)"  # b=beta, i=innov, p=patch; e.g. "b4"
    _PAT_RC_CANDIDATE = r"-rc(\d+)"  # e.g. "-rc3"
    _PAT_META_DATA = r"\+(.*)"  # e.g. "+security"
    _RGX_STABLE = re.compile(
        rf"{_PAT_BASE}(?:{_PAT_BUILD})?(?:{_PAT_RC_CANDIDATE})?(?:{_PAT_META_DATA})?"
    )  # e.g. "2.1.0p17-rc3+security"
    # e.g. daily of version branch: "2.1.0-2021.12.24",
    # daily of master branch: "2021.12.24"
    # -> The master branch also uses the [branch_version]-[date] schema since 2023-11-16.
    #    Keep old variant in the parser for now for compatibility.
    # daily of master sandbox branch: "2022.06.02-sandbox-lm-2.2-thing"
    # daily of version sandbox branch: "2.1.0-2022.06.02-sandbox-lm-2.2-thing"
    _RGX_DAILY = re.compile(rf"(?:{_PAT_BASE}-)?{_PAT_DATE}(?:-sandbox.+)?")

    @classmethod
    def from_str(cls, raw: str) -> Self:
        try:
            return cls._parse_release_version(raw)
        except ValueError:
            return cls._parse_daily_version(raw)

    @classmethod
    def _parse_release_version(cls, vstring: str) -> Self:
        if not (match := cls._RGX_STABLE.fullmatch(vstring)):
            raise ValueError(f'Invalid version string "{vstring}"')

        match match.group(1, 2, 3, 4, 5, 6, 7):
            case major, minor, sub, None, None, None, None:
                return cls(
                    _BaseVersion(int(major), int(minor), int(sub)),
                    _Release.unspecified(),
                    _ReleaseCandidate(None),
                    _ReleaseMeta(None),
                )
            case major, minor, sub, None, None, rc, None:
                return cls(
                    _BaseVersion(int(major), int(minor), int(sub)),
                    _Release.unspecified(),
                    _ReleaseCandidate(int(rc)),
                    _ReleaseMeta(None),
                )
            case major, minor, sub, None, None, None, meta:
                return cls(
                    _BaseVersion(int(major), int(minor), int(sub)),
                    _Release.unspecified(),
                    _ReleaseCandidate(None),
                    _ReleaseMeta(meta),
                )
            case major, minor, sub, release_type, patch, None, None:
                return cls(
                    _BaseVersion(int(major), int(minor), int(sub)),
                    _Release(ReleaseType[release_type], int(patch)),
                    _ReleaseCandidate(None),
                    _ReleaseMeta(None),
                )
            case major, minor, sub, release_type, patch, rc, None:
                return cls(
                    _BaseVersion(int(major), int(minor), int(sub)),
                    _Release(ReleaseType[release_type], int(patch)),
                    _ReleaseCandidate(int(rc)),
                    _ReleaseMeta(None),
                )
            case major, minor, sub, release_type, patch, None, meta:
                return cls(
                    _BaseVersion(int(major), int(minor), int(sub)),
                    _Release(ReleaseType[release_type], int(patch)),
                    _ReleaseCandidate(None),
                    _ReleaseMeta(meta),
                )
            case major, minor, sub, release_type, patch, rc, None:
                return cls(
                    _BaseVersion(int(major), int(minor), int(sub)),
                    _Release(ReleaseType[release_type], int(patch)),
                    _ReleaseCandidate(int(rc)),
                    _ReleaseMeta(None),
                )
            case major, minor, sub, release_type, patch, rc, meta:
                return cls(
                    _BaseVersion(int(major), int(minor), int(sub)),
                    _Release(ReleaseType[release_type], int(patch)),
                    _ReleaseCandidate(int(rc)),
                    _ReleaseMeta(meta),
                )

        raise ValueError(f'Cannot parse version string "{vstring}".')

    @classmethod
    def _parse_daily_version(cls, vstring: str) -> Self:
        if not (match := cls._RGX_DAILY.fullmatch(vstring)):
            raise ValueError(f'Invalid version string "{vstring}"')

        (major, minor, sub, year, month, day) = match.group(1, 2, 3, 4, 5, 6)

        return cls(
            (
                None
                if all(x is None for x in (major, minor, sub))
                else _BaseVersion(int(major), int(minor), int(sub))
            ),
            _Release(ReleaseType.daily, BuildDate(int(year), int(month), int(day))),
            _ReleaseCandidate(None),
            _ReleaseMeta(None),
        )

    def __init__(
        self,
        base: _BaseVersion | None,
        release: _Release,
        release_candidate: _ReleaseCandidate,
        meta: _ReleaseMeta,
    ) -> None:
        self.base: Final = base
        self.release: Final = release
        self.release_candidate: Final = release_candidate
        self.meta: Final = meta

    @property
    def version_base(self) -> str:
        return "" if self.base is None else str(self.base)

    @property
    def version_without_rc(self) -> str:
        return f"{'' if self.base is None else self.base}{self.release.suffix()}".lstrip("-")

    @property
    def version_rc_aware(self) -> str:
        return str(self)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.base!r}, {self.release!r}, {self.release_candidate!r}, {self.meta!r})"

    def __str__(self) -> str:
        optional_rc_suffix = (
            "" if self.release_candidate.value is None else f"-rc{self.release_candidate.value}"
        )
        optional_meta_suffix = "" if self.meta.value is None else f"+{self.meta.value}"
        return f"{'' if self.base is None else self.base}{self.release.suffix()}{optional_rc_suffix}{optional_meta_suffix}".lstrip(
            "-"
        )

    def __lt__(self, other: Version) -> bool:
        if not isinstance(other, Version):
            return NotImplemented

        if self.base != other.base:
            if other.base is None:
                return True
            if self.base is None:
                return False
            return self.base < other.base

        if self.release != other.release:
            return self.release < other.release

        return self.release_candidate < other.release_candidate

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Version):
            return NotImplemented
        return (
            self.base == other.base
            and self.release == other.release
            and self.release_candidate == other.release_candidate
        )


VERSION_PATTERN = re.compile(r"^([.\-a-z]+)?(\d+)")


# Parses versions of Checkmk and converts them into comparable integers.
def parse_check_mk_version(v: str) -> int:
    """Figure out how to compare versions semantically.

    Parses versions of Checkmk and converts them into comparable integers.

    >>> p = parse_check_mk_version

    Watch out! This function can do more than just parse Checkmk versions :-(
    Changing this is incompatible, as it might render some rules for
    "Checkmk Agent installation auditing" invalid.
    >>> p("1.2")
    1020050000

    No idea why this should be allowed:
    >>> p("1.2.3i12p4b43")
    1020315504

    All dailies are built equal.

    >>> p("1.5.0-2019.10.10")
    1050090000

    >>> p("1.6.0-2019.10.10")
    1060090000

    >>> p("1.5.0-2019.10.24") == p("1.5.0-2018.05.05")
    True

    >>> p('1.2.4p1')
    1020450001

    >>> p('1.2.4')
    1020450000

    >>> p('1.2.4b1')
    1020420100

    >>> p('1.2.3i1p1')
    1020310101

    >>> p('1.2.3i1')
    1020310100

    >>> p('1.2.4p10')
    1020450010

    >>> p("1.5.0") > p("1.5.0p22")
    False

    >>> p("1.5.0-2019.10.10") > p("1.5.0p22")
    True

    >>> p("1.5.0p13") == p("1.5.0p13")
    True

    >>> p("1.5.0p13") > p("1.5.0p12")
    True

    >>> p("2022.06.23-sandbox-az-sles-15sp3")
    2022062390000

    """
    parts = v.split(".", 2)

    while len(parts) < 3:
        parts.append("0")

    var_map = {
        # identifier: (base-val, multiplier)
        "s": (0, 1),  # sub
        "i": (10000, 100),  # innovation
        "b": (20000, 100),  # beta
        "p": (50000, 1),  # patch-level
        "-": (90000, 0),  # daily
        ".": (90000, 0),  # daily
    }

    def _extract_rest(_rest: str) -> tuple[str, int, str]:
        for match in VERSION_PATTERN.finditer(_rest):
            _var_type = match.group(1) or "s"
            _num = match.group(2)
            return _var_type, int(_num), _rest[match.end() :]
        # Default fallback.
        return "p", 0, ""

    major, minor, rest = parts
    _, sub, rest = _extract_rest(rest)

    if rest.startswith("-sandbox"):
        rest = ""

    if len(major) == 4:  # daily!
        var_type, num, rest = "-", 0, ""
    else:
        # Only add the base once, else we could do it in the loop.
        var_type, num, rest = _extract_rest(rest)

    base, multiply = var_map[var_type]
    val = base
    val += num * multiply

    while rest:
        var_type, num, rest = _extract_rest(rest)
        _, multiply = var_map[var_type]
        val += num * multiply

    return int(f"{int(major):02}{int(minor):02}{sub:02}{val:05}")


class VersionsCompatible:
    @property
    def is_compatible(self) -> Literal[True]:
        return True


class VersionsIncompatible:
    @property
    def is_compatible(self) -> Literal[False]:
        return False

    def __init__(self, reason: str) -> None:
        self._reason = reason

    def __str__(self) -> str:
        return self._reason


def versions_compatible(
    from_v: Version,
    to_v: Version,
    /,
) -> VersionsCompatible | VersionsIncompatible:
    """Whether or not two versions are compatible (e.g. for omd update or remote automation calls)

    >>> c = versions_compatible

    Nightly build of master branch (with old version scheme) is always compatible as we don't know
    which major version it belongs to. It's also not that important to validate this case.

    >>> isinstance(c(Version.from_str("2.0.0i1"), Version.from_str("2021.12.13")), VersionsCompatible)
    True
    >>> isinstance(c(Version.from_str("2021.12.13"), Version.from_str("2.0.0i1")), VersionsCompatible)
    True
    >>> isinstance(c(Version.from_str("2021.12.13"), Version.from_str("2022.01.01")), VersionsCompatible)
    True
    >>> isinstance(c(Version.from_str("2022.01.01"), Version.from_str("2021.12.13")), VersionsCompatible)
    True

    Nightly branch builds e.g. 2.0.0-2022.01.01 are treated as 2.0.0.

    >>> isinstance(c(Version.from_str("2.0.0-2022.01.01"), Version.from_str("2.0.0p3")), VersionsCompatible)
    True
    >>> isinstance(c(Version.from_str("2.0.0p3"), Version.from_str("2.0.0-2022.01.01")), VersionsCompatible)
    True

    Same major is allowed

    >>> isinstance(c(Version.from_str("2.0.0i1"), Version.from_str("2.0.0p3")), VersionsCompatible)
    True
    >>> isinstance(c(Version.from_str("2.0.0p3"), Version.from_str("2.0.0i1")), VersionsCompatible)
    True
    >>> isinstance(c(Version.from_str("2.0.0p3"), Version.from_str("2.0.0p3")), VersionsCompatible)
    True

    Prev major to new is allowed #1

    >>> isinstance(c(Version.from_str("1.6.0i1"), Version.from_str("2.0.0")), VersionsCompatible)
    True
    >>> isinstance(c(Version.from_str("1.6.0p23"), Version.from_str("2.0.0")), VersionsCompatible)
    True
    >>> isinstance(c(Version.from_str("2.0.0p12"), Version.from_str("2.1.0i1")), VersionsCompatible)
    True

    Prepre major to new not allowed

    >>> str(c(Version.from_str("1.6.0p1"), Version.from_str("2.1.0p3")))
    'Target version too new (one major version jump at maximum).'
    >>> str(c(Version.from_str("1.6.0p1"), Version.from_str("2.1.0b1")))
    'Target version too new (one major version jump at maximum).'
    >>> str(c(Version.from_str("1.5.0i1"), Version.from_str("2.0.0")))
    'Target version too new (one major version jump at maximum).'
    >>> str(c(Version.from_str("1.4.0"), Version.from_str("2.0.0")))
    'Target version too new (one major version jump at maximum).'

    New major to old not allowed

    >>> str(c(Version.from_str("2.0.0"), Version.from_str("1.6.0p1")))
    'Target version too old (older major version is not supported).'
    >>> str(c(Version.from_str("2.1.0"), Version.from_str("2.0.0b1")))
    'Target version too old (older major version is not supported).'

    Specific patch release requirements

    >>> isinstance(c(Version.from_str("2.2.0p8"), Version.from_str("2.3.0i1")), VersionsCompatible)
    True
    >>> str(c(Version.from_str("2.2.0b1000"), Version.from_str("2.3.0i1")))
    'This target version requires at least 2.2.0p...'
    """

    # Daily builds of the master branch (in old format (used until 2023-11-16): YYYY.MM.DD) are
    # always treated to be compatible
    if from_v.base is None or to_v.base is None:
        return VersionsCompatible()

    if from_v.base == to_v.base:
        return VersionsCompatible()

    # Newer major to older is not allowed
    if from_v.base > to_v.base:
        return VersionsIncompatible(
            "Target version too old (older major version is not supported)."
        )

    # Now we need to detect the previous and pre-previous major version.
    # How can we do it without explicitly listing all version numbers?
    #
    # What version changes did we have?
    #
    # - Long ago we increased only the 3rd number which is not done anymore
    # - Until 1.6.0 we only increased the 2nd number
    # - With 2.0.0 we once increased the 1st number
    # - With 2.1.0 we will again only increase the 2nd number
    # - Increasing of the 1st number may happen again
    #
    # Seems we need to handle these cases for:
    #
    # - Steps in 1st number with reset of 2nd number can happen
    # - Steps in 2nd number can happen
    # - 3rd number and suffixes can completely be ignored for now
    #
    # We could implement a simple logic like this:
    #
    # - 1st number +1, newer 2nd is 0 -> it is uncertain which was the
    #                                    last release. We need an explicit
    #                                    lookup table for this situation.
    # - 1st number +2                      -> preprev major
    # - Equal 1st number and 2nd number +1 -> prev major
    # - Equal 1st number and 2nd number +2 -> preprev major
    #
    # Seems to be sufficient for now.
    #
    # Obviously, this only works as long as we keep the current version scheme.

    target_too_new = VersionsIncompatible(
        "Target version too new (one major version jump at maximum)."
    )

    if to_v.base.major - from_v.base.major > 1:
        return target_too_new  # preprev 1st number

    last_major_releases = {
        1: _BaseVersion(1, 6, 0),
    }

    if to_v.base.major - from_v.base.major == 1 and to_v.base.minor == 0:
        # prev major (e.g. last 1.x.0 before 2.0.0)
        if last_major_releases[from_v.base.major] == from_v.base:
            return _check_minimum_patch_release(from_v, to_v)
        return target_too_new  # preprev 1st number

    if to_v.base.major == from_v.base.major:
        if to_v.base.minor - from_v.base.minor > 1:
            return target_too_new  # preprev in 2nd number
        if to_v.base.minor - from_v.base.minor == 1:
            return _check_minimum_patch_release(from_v, to_v)  # prev in 2nd number, ignoring 3rd

    # Everything else is incompatible
    return target_too_new


# Please note: When you change the minimum patch release, you will have to update a few tests:
#
# old_version in tests/docker/test_docker.py
# test_execute_cmk_automation_previous_version in tests/unit/cmk/gui/wato/pages/test_automation.py
# get_min_version in tests/testlib/version.py
#
# The test in tests/update/cee/test_update_from_backup.py needs a new backup snapshot to work
# properly. Skip the test and ask the QA team to create a new backup snapshot.
_REQUIRED_PATCH_RELEASES_MAP: Final = {
    # max can be evaluated in place, obviously, but we keep a list for documentation.
    _BaseVersion(2, 3, 0): max(
        (
            Version.from_str("2.2.0p1"),  # at least the last major version, by default.
            Version.from_str("2.2.0p8"),  # Here we started to sign agents with SHA256
        ),
    ),
    _BaseVersion(2, 4, 0): max(
        (
            Version.from_str("2.3.0p11"),  # dcd piggyback config converted to modern format
            Version.from_str("2.3.0p26"),  # CMK-19258 - \n separated audit log
        ),
    ),
}


def _check_minimum_patch_release(
    from_v: Version,
    to_v: Version,
    /,
) -> VersionsCompatible | VersionsIncompatible:
    if to_v.base is None:
        return VersionsCompatible()
    if not (required_patch_release := _REQUIRED_PATCH_RELEASES_MAP.get(to_v.base)):
        return VersionsCompatible()
    if from_v >= required_patch_release:
        return VersionsCompatible()
    return VersionsIncompatible(f"This target version requires at least {required_patch_release}")


#   .--general infos-------------------------------------------------------.
#   |                                      _   _        __                 |
#   |       __ _  ___ _ __   ___ _ __ __ _| | (_)_ __  / _| ___  ___       |
#   |      / _` |/ _ \ '_ \ / _ \ '__/ _` | | | | '_ \| |_ / _ \/ __|      |
#   |     | (_| |  __/ | | |  __/ | | (_| | | | | | | |  _| (_) \__ \      |
#   |      \__, |\___|_| |_|\___|_|  \__,_|_| |_|_| |_|_|  \___/|___/      |
#   |      |___/                                                           |
#   '----------------------------------------------------------------------'

# Collect general infos about CheckMk and OS which are used by crash reports
# and diagnostics.


def get_general_version_infos(omd_root: Path) -> VersionInfo:
    return {
        "time": time.time(),
        "os": _get_os_info(),
        "version": __version__,
        "edition": edition(omd_root).short,
        "core": _current_monitoring_core(omd_root),
        "python_version": sys.version,
        "python_paths": sys.path,
    }


def _get_os_info() -> str:
    for path_release_file in (
        Path("/etc/redhat-release"),
        Path("/etc/SuSE-release"),
    ):
        if path_release_file.exists():
            with path_release_file.open() as release_file:
                return release_file.readline().strip()

    info = {}
    for path in [Path("/etc/os-release"), Path("/etc/lsb-release")]:
        if path.exists():
            with path.open() as release_file:
                for line in release_file.readlines():
                    if "=" in line:
                        k, v = line.split("=", 1)
                        info[k.strip()] = v.strip().strip('"')
            break

    if "PRETTY_NAME" in info:
        return info["PRETTY_NAME"]

    if info:
        return f"{info}"

    if os.environ.get("OMD_ROOT"):
        disto_info = os.environ["OMD_ROOT"] + "/share/omd/distro.info"
        if os.path.exists(disto_info):
            return open(disto_info).readline().split("=", 1)[1].strip()

    return "UNKNOWN"


def _current_monitoring_core(omd_root: Path) -> str:
    return get_omd_config(omd_root).get("CONFIG_CORE", "UNKNOWN")
