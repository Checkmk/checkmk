#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Check_MK's library for code used by different components of Check_MK.

This library is currently handled as internal module of Check_MK and
does not offer stable APIs. The code may change at any time."""

from __future__ import annotations

__version__ = "2.2.0p40"

import datetime
import enum
import functools
import os
import re
import sys
import time
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Final, NamedTuple, Union

from typing_extensions import assert_never

import cmk.utils.paths
from cmk.utils.i18n import _
from cmk.utils.site import get_omd_config


class _EditionValue(NamedTuple):
    short: str
    long: str
    title: str


class Edition(_EditionValue, enum.Enum):
    CRE = _EditionValue("cre", "raw", "Checkmk Raw Edition")
    CEE = _EditionValue("cee", "enterprise", "Checkmk Enterprise Edition")
    CCE = _EditionValue("cce", "cloud", "Checkmk Cloud Edition")
    CME = _EditionValue("cme", "managed", "Checkmk Managed Services Edition")

    @classmethod
    def from_version_string(cls, raw: str) -> Edition:
        return cls[raw.split(".")[-1].upper()]

    @classmethod
    def from_long_edition(cls, long: str) -> Edition:
        for e in cls:
            if e.long == long:
                return e
        raise RuntimeError(f"Unknown long edition: {long}")


@lru_cache
def omd_version() -> str:
    version_link = cmk.utils.paths.omd_root / "version"
    return version_link.resolve().name


@lru_cache
def edition() -> Edition:
    try:
        return Edition[omd_version().split(".")[-1].upper()]
    except KeyError:
        # Without this fallback CI jobs may fail.
        # The last job known to fail was we the building of the sphinx documentation
        return Edition.CRE


def is_enterprise_edition() -> bool:
    return edition() is Edition.CEE


def is_cloud_edition() -> bool:
    return edition() is Edition.CCE


def is_raw_edition() -> bool:
    return edition() is Edition.CRE


def is_managed_edition() -> bool:
    return edition() is Edition.CME


def is_cma() -> bool:
    return os.path.exists("/etc/cma/cma.conf")


def mark_edition_only(feature_to_mark: str, exclusive_to: Edition) -> str:
    """
    >>> mark_edition_only("Feature", Edition.CRE)
    'Feature (Raw Edition)'
    >>> mark_edition_only("Feature", Edition.CEE)
    'Feature (Enterprise Edition)'
    >>> mark_edition_only("Feature", Edition.CCE)
    'Feature (Cloud Edition)'
    >>> mark_edition_only("Feature", Edition.CME)
    'Feature (Managed Services Edition)'
    """
    return f"{feature_to_mark} ({exclusive_to.title.removeprefix('Checkmk ')})"


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
@dataclass
class _VersionBase:
    major: int
    minor: int
    sub: int


@dataclass
class _VersionDate:
    date: datetime.date


@dataclass
class _ReleaseCandidate:
    release_candidate: int | None


@dataclass
class _ReleaseMeta:
    meta: str | None


@dataclass
class _StableVersion(_VersionBase, _ReleaseCandidate, _ReleaseMeta):
    pass


@dataclass
class _BetaVersion(_VersionBase, _ReleaseCandidate, _ReleaseMeta):
    vtype = "b"
    patch: int


@dataclass
class _InnovationVersion(_VersionBase, _ReleaseCandidate, _ReleaseMeta):
    vtype = "i"
    patch: int


@dataclass
class _PatchVersion(_VersionBase, _ReleaseCandidate, _ReleaseMeta):
    vtype = "p"
    patch: int


@dataclass
class _MasterDailyVersion(_VersionDate):
    release_candidate = None
    meta = None


@dataclass
class _StableDailyVersion(_VersionDate, _VersionBase):
    # Order of attributes: major, minor, sub, date
    release_candidate = None
    meta = None


_NoneDailyVersion = _StableVersion | _BetaVersion | _InnovationVersion | _PatchVersion
_DailyVersion = _MasterDailyVersion | _StableDailyVersion
# We still need "Union" because of https://github.com/python/mypy/issues/12005
_Version = Union[_DailyVersion, _NoneDailyVersion]


@functools.total_ordering
class Version:
    # Regular expression patterns
    _pat_base: str = r"([1-9]?\d)\.([1-9]?\d)\.([1-9]?\d)"  # e.g. "2.1.0"
    _pat_date: str = r"([1-9]\d{3})\.([0-1]\d)\.([0-3]\d)"  # e.g. "2021.12.24"
    _pat_build: str = r"([bip])(\d+)"  # b=beta, i=innov, p=patch; e.g. "b4"
    _pat_rc_candidate: str = r"-rc(\d+)"  # e.g. "-rc3"
    _pat_meta_data = r"\+(.*)"  # e.g. "+security"
    _pat_stable: str = rf"{_pat_base}(?:{_pat_build})?(?:{_pat_rc_candidate})?(?:{_pat_meta_data})?"  # e.g. "2.1.0p17-rc3+security"
    # e.g. daily of version branch: "2.1.0-2021.12.24",
    # daily of master branch: "2021.12.24"
    # daily of master sandbox branch: "2022.06.02-sandbox-lm-2.2-thing"
    # daily of version sandbox branch: "2.1.0-2022.06.02-sandbox-lm-2.2-thing"
    _pat_daily: str = f"(?:{_pat_base}-)?{_pat_date}(?:-sandbox.+)?"

    def __init__(self, vstring: str) -> None:
        try:
            self.version: _Version = self._parse_none_daily_version(vstring)
        except ValueError:
            self.version = self._parse_daily_version(vstring)

    @property
    def version_base(self) -> str:
        v = self.version
        if isinstance(v, _MasterDailyVersion):
            return ""
        return "%d.%d.%d" % (v.major, v.minor, v.sub)

    @property
    def version_without_rc(self) -> str:
        suffix = ""
        if hasattr(self.version, "vtype"):
            suffix = f"{self.version.vtype}"
        if hasattr(self.version, "patch"):
            suffix = f"{suffix}{self.version.patch}"
        if hasattr(self.version, "date"):
            suffix = f"-{self.version.date.strftime('%Y.%m.%d')}{suffix}"
        return f"{'' if self.version_base is None else self.version_base}{suffix}".lstrip("-")

    @property
    def version_rc_aware(self) -> str:
        return str(self)

    @classmethod
    def _parse_none_daily_version(cls, vstring: str) -> _NoneDailyVersion:
        # Match the version pattern on vstring and check if there is a match
        match = re.match("^%s$" % cls._pat_stable, vstring)
        if not match:
            raise ValueError('Invalid version string "%s"' % vstring)

        major, minor, sub, vtype, patch, rc, meta = match.group(1, 2, 3, 4, 5, 6, 7)
        if rc is not None:
            rc = int(rc)

        if vtype is None and patch is None:
            return _StableVersion(
                major=int(major),
                minor=int(minor),
                sub=int(sub),
                release_candidate=rc,
                meta=meta,
            )
        if vtype == "b":
            return _BetaVersion(
                major=int(major),
                minor=int(minor),
                sub=int(sub),
                patch=int(patch),
                release_candidate=rc,
                meta=meta,
            )
        if vtype == "i":
            return _InnovationVersion(
                major=int(major),
                minor=int(minor),
                sub=int(sub),
                patch=int(patch),
                release_candidate=rc,
                meta=meta,
            )
        if vtype == "p":
            return _PatchVersion(
                major=int(major),
                minor=int(minor),
                sub=int(sub),
                patch=int(patch),
                release_candidate=rc,
                meta=meta,
            )

        raise ValueError(
            f'Invalid version type "{vtype}". Cannot parse version string "{vstring}".'
        )

    @classmethod
    def _parse_daily_version(cls, vstring: str) -> _DailyVersion:
        # Match the version pattern on vstring and check if there is a match
        match = re.match("^%s$" % cls._pat_daily, vstring)
        if not match:
            raise ValueError('Invalid version string "%s"' % vstring)

        (major, minor, sub, year, month, day) = match.group(1, 2, 3, 4, 5, 6)

        if all(x is None for x in (major, minor, sub)):
            return _MasterDailyVersion(datetime.date(int(year), int(month), int(day)))

        return _StableDailyVersion(
            int(major), int(minor), int(sub), datetime.date(int(year), int(month), int(day))
        )

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}('{self}')"

    def __str__(self) -> str:
        v = self.version

        optional_rc_suffix = "" if v.release_candidate is None else f"-rc{v.release_candidate}"
        optional_meta_suffix = "" if v.meta is None else f"+{v.meta}"

        if isinstance(v, _StableVersion):
            return "%d.%d.%d%s%s" % (
                v.major,
                v.minor,
                v.sub,
                optional_rc_suffix,
                optional_meta_suffix,
            )

        if isinstance(v, (_BetaVersion, _InnovationVersion, _PatchVersion)):
            return "%d.%d.%d%s%d%s%s" % (
                v.major,
                v.minor,
                v.sub,
                v.vtype,
                v.patch,
                optional_rc_suffix,
                optional_meta_suffix,
            )

        if isinstance(v, _MasterDailyVersion):
            return v.date.strftime("%Y.%m.%d")

        if isinstance(v, _StableDailyVersion):
            return "%d.%d.%d-%s" % (v.major, v.minor, v.sub, v.date.strftime("%Y.%m.%d"))

        return assert_never(v)

    def __lt__(self, other: Version) -> bool:
        return self._cmp(other) < 0

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Version):
            return self._cmp(other) == 0
        raise ValueError('Invalid version comparison of non-version object "%s"' % other)

    def _cmp(self, other: Version) -> int:
        v = self.version
        o_v = other.version

        # Check for master daily version
        if isinstance(v, _MasterDailyVersion):
            if isinstance(o_v, _MasterDailyVersion):
                return self._cmp_date(o_v)
            return 1  # master daily > none master daily
        if isinstance(o_v, _MasterDailyVersion):
            return -1  # none master daily < master daily

        # Compare version bases
        base_cmp_result = self._cmp_version_base(o_v)
        if base_cmp_result != 0:  # different version bases
            return base_cmp_result

        # Same version base -> Check for stable daily version
        if isinstance(v, _StableDailyVersion):
            if isinstance(o_v, _StableDailyVersion):
                return self._cmp_date(o_v)
            return 1  # stable daily > none stable daily
        if isinstance(o_v, _StableDailyVersion):
            return -1  # none stable daily < stable daily

        # Compare version builds
        return self._cmp_version_build(o_v)

    def _cmp_version_base(self, o_v: _Version) -> int:
        v = self.version

        if isinstance(v, _MasterDailyVersion):
            raise ValueError('%s does not have a version base "<major>.<minor>.<sub>"' % v)
        if isinstance(o_v, _MasterDailyVersion):
            raise ValueError('%s does not have a version base "<major>.<minor>.<sub>"' % o_v)

        version_base: tuple[int, int, int, int] = (
            v.major,
            v.minor,
            v.sub,
            v.release_candidate or 0,
        )
        o_version_base: tuple[int, int, int, int] = (
            o_v.major,
            o_v.minor,
            o_v.sub,
            o_v.release_candidate or 0,
        )

        return (version_base > o_version_base) - (version_base < o_version_base)

    def _cmp_version_build(self, o_v: _Version) -> int:
        v = self.version

        # Compare vtype and patch number with tuples holding numeric values for vtype and patch
        # ([0-3], [0-9]+)
        numeric_build: tuple[int, int] = self._get_numeric_build(v)
        o_numeric_build: tuple[int, int] = self._get_numeric_build(o_v)

        return (numeric_build > o_numeric_build) - (numeric_build < o_numeric_build)

    @staticmethod
    def _get_numeric_build(v: _Version) -> tuple[int, int]:
        if isinstance(v, (_MasterDailyVersion, _StableDailyVersion)):
            raise ValueError('%s does not have a version build "<vtype><patch>"' % v)

        vtype_map: dict[str, int] = {
            "i": 0,  # innovation
            "b": 1,  # beta
            "s": 2,  # stable
            "p": 3,  # patch-level
        }

        if isinstance(v, (_StableVersion)):
            return (vtype_map["s"], 0)
        if isinstance(v, (_BetaVersion, _InnovationVersion, _PatchVersion)):
            return (vtype_map[v.vtype], v.patch)
        return None

    def _cmp_date(self, o_v: _Version) -> int:
        v = self.version

        if not isinstance(v, (_MasterDailyVersion, _StableDailyVersion)):
            raise ValueError('%s does not have a date "<year>.<month>.<day>".' % v)
        if not isinstance(o_v, (_MasterDailyVersion, _StableDailyVersion)):
            raise ValueError('%s does not have a date "<year>.<month>.<day>".' % o_v)

        return (v.date > o_v.date) - (v.date < o_v.date)

    def parse_to_int(self) -> int:
        v = self.version
        var_map = {
            # identifier: (base-val, multiplier)
            "i": (10000, 100),  # innovation
            "b": (20000, 100),  # beta
            "p": (50000, 1),  # patch-level
            "d": (90000, 0),  # daily
        }

        if isinstance(v, _MasterDailyVersion):
            val = var_map["d"][0]
            return int("%02d%02d%02d%05d" % (v.date.year, v.date.month, v.date.day, val))

        if isinstance(v, _StableDailyVersion):
            val = var_map["d"][0]
        elif isinstance(v, _StableVersion):
            val = var_map["p"][0]
        else:
            val, multiply = var_map[v.vtype]
            val += v.patch * multiply

        return int("%02d%02d%02d%05d" % (v.major, v.minor, v.sub, val))


VERSION_PATTERN = re.compile(r"^([.\-a-z]+)?(\d+)")


# Parses versions of Checkmk and converts them into comparable integers.
def parse_check_mk_version(v: str) -> int:
    """Figure out how to compare versions semantically.

    Parses versions of Checkmk and converts them into comparable integers.

    >>> p = parse_check_mk_version

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
    2022062300000

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
        return int("%02d%02d%02d%05d" % (int(major), int(minor), sub, 0))

    if len(major) == 4:
        rest = v[-3:]

    # Only add the base once, else we could do it in the loop.
    var_type, num, rest = _extract_rest(rest)
    base, multiply = var_map[var_type]
    val = base
    val += num * multiply

    while rest:
        var_type, num, rest = _extract_rest(rest)
        _, multiply = var_map[var_type]
        val += num * multiply

    return int("%02d%02d%02d%05d" % (int(major), int(minor), sub, val))


def base_version_parts(version: str) -> tuple[int, int, int]:
    match = re.match(r"(\d+).(\d+).(\d+)", version)
    if not match or len(match.groups()) != 3:
        raise ValueError(_("Unable to parse version: %r") % version)
    groups = match.groups()
    return int(groups[0]), int(groups[1]), int(groups[2])


def is_daily_build_of_master(version: str) -> bool:
    """
    >>> f = is_daily_build_of_master
    >>> f("2021.04.12")
    True
    >>> f("2023.04.12")
    True
    >>> f("2.1.0")
    False
    >>> f("2.1.0-2022.06.23")
    False

    Is not directly built from master, but a sandbox branch which is based on the master branch.
    Treat it same as a master branch.

    >>> f("2022.06.23-sandbox-lm-2.2-omd-apache")
    True
    """
    return re.match(r"\d{4}.\d{2}.\d{2}(?:-sandbox.+)?$", version) is not None


def is_same_major_version(this_version: str, other_version: str) -> bool:
    """
    Nightly branch builds e.g. 2.0.0-2022.01.01 are treated as 2.0.0.

    >>> c = is_same_major_version
    >>> c("2.0.0-2022.01.01", "2.0.0p3")
    True
    >>> c("2022.01.01", "2.0.0p3")
    True
    >>> c("2022.01.01", "1.6.0p3")
    True
    >>> c("1.6.0", "1.6.0p2")
    True
    >>> c("1.7.0", "1.6.0")
    False
    >>> c("1.6.0", "1.7.0")
    False
    >>> c("2.1.0i1", "2.1.0p2")
    True
    >>> c("2.1.0", "2.1.0")
    True
    """
    # We can not decide which is the current base version of the master daily builds. For this
    # reason we always treat them to be compatbile.
    if is_daily_build_of_master(this_version) or is_daily_build_of_master(other_version):
        return True

    return base_version_parts(this_version)[:-1] == base_version_parts(other_version)[:-1]


class VersionsCompatible:
    ...


class VersionsIncompatible:
    def __init__(self, reason: str) -> None:
        self._reason = reason

    def __str__(self) -> str:
        return self._reason


def versions_compatible(
    from_v: Version, to_v: Version, /
) -> VersionsCompatible | VersionsIncompatible:
    """Whether or not two versions are compatible (e.g. for omd update or remote automation calls)

    >>> c = versions_compatible

    Nightly build of master branch is always compatible as we don't know which major version it
    belongs to. It's also not that important to validate this case.

    >>> isinstance(c(Version("2.0.0i1"), Version("2021.12.13")), VersionsCompatible)
    True
    >>> isinstance(c(Version("2021.12.13"), Version("2.0.0i1")), VersionsCompatible)
    True
    >>> isinstance(c(Version("2021.12.13"), Version("2022.01.01")), VersionsCompatible)
    True
    >>> isinstance(c(Version("2022.01.01"), Version("2021.12.13")), VersionsCompatible)
    True

    Nightly branch builds e.g. 2.0.0-2022.01.01 are treated as 2.0.0.

    >>> isinstance(c(Version("2.0.0-2022.01.01"), Version("2.0.0p3")), VersionsCompatible)
    True
    >>> isinstance(c(Version("2.0.0p3"), Version("2.0.0-2022.01.01")), VersionsCompatible)
    True

    Same major is allowed

    >>> isinstance(c(Version("2.0.0i1"), Version("2.0.0p3")), VersionsCompatible)
    True
    >>> isinstance(c(Version("2.0.0p3"), Version("2.0.0i1")), VersionsCompatible)
    True
    >>> isinstance(c(Version("2.0.0p3"), Version("2.0.0p3")), VersionsCompatible)
    True

    Prev major to new is allowed #1

    >>> isinstance(c(Version("1.6.0i1"), Version("2.0.0")), VersionsCompatible)
    True
    >>> isinstance(c(Version("1.6.0p23"), Version("2.0.0")), VersionsCompatible)
    True
    >>> isinstance(c(Version("2.0.0p12"), Version("2.1.0i1")), VersionsCompatible)
    True

    Prepre major to new not allowed

    >>> str(c(Version("1.6.0p1"), Version("2.1.0p3")))
    'Target version too new (one major version jump at maximum).'
    >>> str(c(Version("1.6.0p1"), Version("2.1.0b1")))
    'Target version too new (one major version jump at maximum).'
    >>> str(c(Version("1.5.0i1"), Version("2.0.0")))
    'Target version too new (one major version jump at maximum).'
    >>> str(c(Version("1.4.0"), Version("2.0.0")))
    'Target version too new (one major version jump at maximum).'

    New major to old not allowed

    >>> str(c(Version("2.0.0"), Version("1.6.0p1")))
    'Target version too old (older major version is not supported).'
    >>> str(c(Version("2.1.0"), Version("2.0.0b1")))
    'Target version too old (older major version is not supported).'

    Specific patch release requirements

    >>> isinstance(c(Version("2.1.0p31"), Version("2.2.0i1")), VersionsCompatible)
    True
    >>> str(c(Version("2.1.0p30"), Version("2.2.0i1")))
    'This target version requires at least 2.1.0p31'
    """

    # Daily builds of the master branch (format: YYYY.MM.DD) are always treated to be compatbile
    if any(
        (
            is_daily_build_of_master(str(from_v)),
            is_daily_build_of_master(str(to_v)),
        )
    ):
        return VersionsCompatible()

    from_v_parts = base_version_parts(str(from_v))
    to_v_parts = base_version_parts(str(to_v))

    # Same major version is allowed
    if from_v_parts == to_v_parts:
        return VersionsCompatible()

    # Newer major to older is not allowed
    if from_v_parts > to_v_parts:
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

    if to_v_parts[0] - from_v_parts[0] > 1:
        return target_too_new  # preprev 1st number

    last_major_releases = {
        1: (1, 6, 0),
    }

    if to_v_parts[0] - from_v_parts[0] == 1 and to_v_parts[1] == 0:
        # prev major (e.g. last 1.x.0 before 2.0.0)
        if last_major_releases[from_v_parts[0]] == from_v_parts:
            return _check_minimum_patch_release(from_v, to_v)
        return target_too_new  # preprev 1st number

    if to_v_parts[0] == from_v_parts[0]:
        if to_v_parts[1] - from_v_parts[1] > 1:
            return target_too_new  # preprev in 2nd number
        if to_v_parts[1] - from_v_parts[1] == 1:
            return _check_minimum_patch_release(from_v, to_v)  # prev in 2nd number, ignoring 3rd

    # Everything else is incompatible
    return target_too_new


_REQUIRED_PATCH_RELEASES_MAP: Final = {
    # we keep a list for documentation.
    (2, 2, 0): max(
        Version("2.1.0p11"),  # ?
        Version("2.1.0p15"),  # migration for MKPs (Werk #14636)
        Version("2.1.0p17"),  # added severity_new_host_label to sample config and Werk #14938
        Version("2.1.0p19"),  # fixup of broken SNMP v3 configuration (Werk #14990)
        Version("2.1.0p20"),  # fixup of broken enabled_packages (Werk #15113)
        Version("2.1.0p23"),  # fixup of broken global settings migration (Werk #14304)
        Version("2.1.0p25"),  # fix Alternative.transform_value (CMK-12694)
        Version("2.1.0p29"),  # fix update for static_checks:cpu_load (Werk #15270)
        Version(
            "2.1.0p31"
        ),  # 15863 FIX Add default aggregation modes for some clustered services during update
    ),
}


def _check_minimum_patch_release(
    from_v: Version, to_v: Version, /
) -> VersionsCompatible | VersionsIncompatible:
    if not (
        required_patch_release := _REQUIRED_PATCH_RELEASES_MAP.get(base_version_parts(str(to_v)))
    ):
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


def get_general_version_infos() -> dict[str, Any]:
    return {
        "time": time.time(),
        "os": _get_os_info(),
        "version": __version__,
        "edition": edition().short,
        "core": _current_monitoring_core(),
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
        return "%s" % info

    if os.environ.get("OMD_ROOT"):
        disto_info = os.environ["OMD_ROOT"] + "/share/omd/distro.info"
        if os.path.exists(disto_info):
            return open(disto_info).readline().split("=", 1)[1].strip()

    return "UNKNOWN"


def _current_monitoring_core() -> str:
    return get_omd_config().get("CONFIG_CORE", "UNKNOWN")
