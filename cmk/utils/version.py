#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Check_MK's library for code used by different components of Check_MK.

This library is currently handled as internal module of Check_MK and
does not offer stable APIs. The code may change at any time."""

__version__ = "2.1.0i1"

import enum
import errno
import os
import re
import subprocess
import sys
import time
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict

import livestatus

import cmk.utils.paths


@lru_cache
def omd_version() -> str:
    version_link = Path(cmk.utils.paths.omd_root).joinpath("version")
    return version_link.resolve().name


@lru_cache
def edition_short() -> str:
    return str(omd_version().split(".")[-1])


def is_enterprise_edition() -> bool:
    return edition_short() == "cee"


def is_raw_edition() -> bool:
    return edition_short() == "cre"


def is_managed_edition() -> bool:
    return edition_short() == "cme"


def is_free_edition() -> bool:
    return edition_short() == "cfe"


def is_cma() -> bool:
    return os.path.exists("/etc/cma/cma.conf")


def is_daily_build() -> bool:
    # Daily build version format: YYYY.MM.DD or MAJOR.MINOR.PATCH-YYYY.MM.DD
    return "-" in __version__ or len(__version__.split(".", maxsplit=1)[0]) == 4


def edition_title():
    if is_enterprise_edition():
        return "CEE"
    if is_managed_edition():
        return "CME"
    if is_free_edition():
        return "CFE"
    return "CRE"


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
        "edition": edition_short(),
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
            for line in open(f).readlines():
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
        p = subprocess.Popen(
            ["omd", "config", "show", "CORE"],
            close_fds=True,
            stdin=open(os.devnull),
            stdout=subprocess.PIPE,
            stderr=open(os.devnull, "w"),
            encoding="utf-8",
        )
        return p.communicate()[0].rstrip()
    except OSError as e:
        # Allow running unit tests on systems without omd installed (e.g. on travis)
        if e.errno != errno.ENOENT:
            raise
        return "UNKNOWN"
