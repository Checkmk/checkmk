#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Check_MK's library for code used by different components of Check_MK.

This library is currently handled as internal module of Check_MK and
does not offer stable APIs. The code may change at any time."""

__version__ = "2.0.0p23"

import errno
import enum
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Any, Dict

from six import ensure_str

import cmk.utils.paths
import livestatus
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.i18n import _
from functools import lru_cache


@lru_cache
def omd_version() -> str:
    version_link = Path(cmk.utils.paths.omd_root).joinpath("version")
    return ensure_str(version_link.resolve().name)


@lru_cache
def omd_site() -> str:
    try:
        return os.environ["OMD_SITE"]
    except KeyError:
        raise MKGeneralException(
            _("OMD_SITE environment variable not set. You can "
              "only execute this in an OMD site."))


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
                    info[k.strip()] = v.strip().strip("\"")
            break

    if "PRETTY_NAME" in info:
        return info["PRETTY_NAME"]

    if info:
        return "%s" % info

    if os.environ.get("OMD_ROOT"):
        disto_info = os.environ['OMD_ROOT'] + "/share/omd/distro.info"
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
