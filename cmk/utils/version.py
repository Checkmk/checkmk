#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Check_MK's library for code used by different components of Check_MK.

This library is currently handled as internal module of Check_MK and
does not offer stable APIs. The code may change at any time."""

from __future__ import annotations

__version__ = "2.1.0b6"

import datetime
import enum
import errno
import functools
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Dict, NamedTuple, Tuple, Union

import livestatus

import cmk.utils.paths
from cmk.utils.i18n import _
from cmk.utils.type_defs._misc import assert_never


class _EditionValue(NamedTuple):
    short: str
    title: str


class Edition(_EditionValue, enum.Enum):
    CRE = _EditionValue("cre", "Checkmk Raw Edition")
    CEE = _EditionValue("cee", "Checkmk Enterprise Edition")
    CPE = _EditionValue("cpe", "Checkmk Enterprise Plus Edition")
    CME = _EditionValue("cme", "Checkmk Managed Services Edition")
    CFE = _EditionValue("cfe", "Checkmk Free Edition")


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


def is_plus_edition() -> bool:
    return edition() is Edition.CPE


def is_raw_edition() -> bool:
    return edition() is Edition.CRE


def is_managed_edition() -> bool:
    return edition() is Edition.CME


def is_free_edition() -> bool:
    return edition() is Edition.CFE


def is_cma() -> bool:
    return os.path.exists("/etc/cma/cma.conf")


class TrialState(enum.Enum):
    """All possible states of the free version"""

    VALID = enum.auto()
    EXPIRED = enum.auto()
    NO_LIVESTATUS = enum.auto()  # special case, no cmc impossible to determine status


def _get_expired_status() -> TrialState:
    try:
        query = "GET status\nColumns: is_trial_expired\n"
        response = livestatus.LocalConnection().query(query)
        return TrialState.EXPIRED if response[0][0] == 1 else TrialState.VALID
    except (livestatus.MKLivestatusNotFoundError, livestatus.MKLivestatusSocketError):
        # NOTE: If livestatus is absent we assume that trial is expired.
        # Livestatus may be absent only when the cmc missing and this case for free version means
        # just expiration(impossibility to check)
        return TrialState.NO_LIVESTATUS


def _get_timestamp_trial() -> int:
    try:
        query = "GET status\nColumns: state_file_created\n"
        response = livestatus.LocalConnection().query(query)
        return int(response[0][0])
    except (livestatus.MKLivestatusNotFoundError, livestatus.MKLivestatusSocketError):
        # NOTE: If livestatus is absent we assume that trial is expired.
        # Livestatus may be absent only when the cmc missing and this case for free version means
        # just expiration(impossibility to check)
        return 0


def get_age_trial() -> int:
    return int(time.time()) - _get_timestamp_trial()


def is_expired_trial() -> bool:
    return is_free_edition() and _get_expired_status() == TrialState.EXPIRED


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
class _StableVersion(_VersionBase):
    pass


@dataclass
class _BetaVersion(_VersionBase):
    vtype = "b"
    patch: int


@dataclass
class _InnovationVersion(_VersionBase):
    vtype = "i"
    patch: int


@dataclass
class _PatchVersion(_VersionBase):
    vtype = "p"
    patch: int


@dataclass
class _MasterDailyVersion(_VersionDate):
    pass


@dataclass
class _StableDailyVersion(_VersionDate, _VersionBase):
    # Order of attributes: major, minor, sub, date
    pass


_NoneDailyVersion = Union[
    _StableVersion,
    _BetaVersion,
    _InnovationVersion,
    _PatchVersion,
]
_DailyVersion = Union[
    _MasterDailyVersion,
    _StableDailyVersion,
]
_Version = Union[
    _NoneDailyVersion,
    _DailyVersion,
]


@functools.total_ordering
class Version:
    # Regular expression patterns
    _pat_base: str = r"([1-9]?\d)\.([1-9]?\d)\.([1-9]?\d)"  # e.g. "2.1.0"
    _pat_date: str = r"([1-9]\d{3})\.([0-1]\d)\.([0-3]\d)"  # e.g. "2021.12.24"
    _pat_build: str = r"([bip])(\d+)"  # b=beta, i=innov, p=patch; e.g. "b4"
    _pat_stable: str = r"%s(?:%s)?" % (_pat_base, _pat_build)  # e.g. "2.1.0p17"
    _pat_daily: str = "(?:%s-)?%s" % (
        _pat_base,
        _pat_date,
    )  # e.g. "2.1.0-2021.12.24" also "2021.12.24"

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

    @classmethod
    def _parse_none_daily_version(cls, vstring: str) -> _NoneDailyVersion:
        # Match the version pattern on vstring and check if there is a match
        match = re.match("^%s$" % cls._pat_stable, vstring)
        if not match:
            raise ValueError('Invalid version string "%s"' % vstring)

        major, minor, sub, vtype, patch = match.group(1, 2, 3, 4, 5)

        if vtype is None and patch is None:
            return _StableVersion(int(major), int(minor), int(sub))
        if vtype == "b":
            return _BetaVersion(int(major), int(minor), int(sub), int(patch))
        if vtype == "i":
            return _InnovationVersion(int(major), int(minor), int(sub), int(patch))
        if vtype == "p":
            return _PatchVersion(int(major), int(minor), int(sub), int(patch))

        raise ValueError(
            'Invalid version type "%s". Cannot parse version string "%s".' % (vtype, vstring)
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
        return "%s('%s')" % (self.__class__.__name__, self)

    def __str__(self) -> str:
        v = self.version
        if isinstance(v, _StableVersion):
            return "%d.%d.%d" % (v.major, v.minor, v.sub)

        if isinstance(v, (_BetaVersion, _InnovationVersion, _PatchVersion)):
            return "%d.%d.%d%s%d" % (v.major, v.minor, v.sub, v.vtype, v.patch)

        if isinstance(v, _MasterDailyVersion):
            return v.date.strftime("%Y.%m.%d")

        if isinstance(v, _StableDailyVersion):
            return "%d.%d.%d-%s" % (v.major, v.minor, v.sub, v.date.strftime("%Y.%m.%d"))

        assert_never(v)

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

        version_base: Tuple[int, int, int] = (v.major, v.minor, v.sub)
        o_version_base: Tuple[int, int, int] = (o_v.major, o_v.minor, o_v.sub)

        return (version_base > o_version_base) - (version_base < o_version_base)

    def _cmp_version_build(self, o_v: _Version) -> int:
        v = self.version

        # Compare vtype and patch number with tuples holding numeric values for vtype and patch
        # ([0-3], [0-9]+)
        numeric_build: Tuple[int, int] = self._get_numeric_build(v)
        o_numeric_build: Tuple[int, int] = self._get_numeric_build(o_v)

        return (numeric_build > o_numeric_build) - (numeric_build < o_numeric_build)

    @staticmethod
    def _get_numeric_build(v: _Version) -> Tuple[int, int]:
        if isinstance(v, (_MasterDailyVersion, _StableDailyVersion)):
            raise ValueError('%s does not have a version build "<vtype><patch>"' % v)

        vtype_map: Dict[str, int] = {
            "i": 0,  # innovation
            "b": 1,  # beta
            "s": 2,  # stable
            "p": 3,  # patch-level
        }

        if isinstance(v, (_StableVersion)):
            return (vtype_map["s"], 0)
        if isinstance(v, (_BetaVersion, _InnovationVersion, _PatchVersion)):
            return (vtype_map[v.vtype], v.patch)

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

    def _extract_rest(_rest):
        for match in VERSION_PATTERN.finditer(_rest):
            _var_type = match.group(1) or "s"
            _num = match.group(2)
            return _var_type, int(_num), _rest[match.end() :]
        # Default fallback.
        return "p", 0, ""

    major, minor, rest = parts
    _, sub, rest = _extract_rest(rest)

    if len(major) == 4:
        rest = v[-3:]

    if rest.startswith("-sandbox"):
        return int("%02d%02d%02d%05d" % (int(major), int(minor), sub, 0))

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


def base_version_parts(version: str) -> Tuple[int, int, int]:
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
    """
    return re.match(r"\d{4}.\d{2}.\d{2}$", version) is not None


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


def get_general_version_infos() -> Dict[str, Any]:
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
    if os.path.exists("/etc/redhat-release"):
        return open("/etc/redhat-release").readline().strip()

    if os.path.exists("/etc/SuSE-release"):
        return open("/etc/SuSE-release").readline().strip()

    info = {}
    for f in ["/etc/os-release", "/etc/lsb-release"]:
        if os.path.exists(f):
            for line in open(f).readlines():  # pylint:disable=consider-using-with
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
    try:
        p = subprocess.Popen(  # pylint:disable=consider-using-with
            ["omd", "config", "show", "CORE"],
            close_fds=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            encoding="utf-8",
        )
        return p.communicate()[0].rstrip()
    except OSError as e:
        # Allow running unit tests on systems without omd installed (e.g. on travis)
        if e.errno != errno.ENOENT:
            raise
        return "UNKNOWN"
