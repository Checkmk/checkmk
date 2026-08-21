#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="unreachable"

import json
import os
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path

from cmk.ccc.crash_reporting import VersionInfo
from cmk.ccc.site import get_omd_config
from cmk.ccc.version import __version__, edition

#   .--general infos-------------------------------------------------------.
#   |                                      _   _        __                 |
#   |       __ _  ___ _ __   ___ _ __ __ _| | (_)_ __  / _| ___  ___       |
#   |      / _` |/ _ \ '_ \ / _ \ '__/ _` | | | | '_ \| |_ / _ \/ __|      |
#   |     | (_| |  __/ | | |  __/ | | (_| | | | | | | |  _| (_) \__ \      |
#   |      \__, |\___|_| |_|\___|_|  \__,_|_| |_|_| |_|_|  \___/|___/      |
#   |      |___/                                                           |
#   '----------------------------------------------------------------------'


def general_version_infos_from_env() -> VersionInfo:
    """Compute general version infos via subprocess

    The Checkmk site and relay both implement an executable `cmk-general-version-infos`
    to provide the necessary information.
    """
    raw_version_infos = json.loads(subprocess.check_output(["cmk-general-version-infos"]))
    return VersionInfo(
        {
            "core": raw_version_infos["core"],
            "python_version": raw_version_infos["python_version"],
            "edition": raw_version_infos["edition"],
            "python_paths": raw_version_infos["python_paths"],
            "version": raw_version_infos["version"],
            "time": raw_version_infos["time"],
            "os": raw_version_infos["os"],
        }
    )


def get_general_version_infos(omd_root: Path) -> VersionInfo:
    """Compute general information about runtime environment (Checkmk site and OS)"""
    return general_version_infos(
        edition=lambda: edition(omd_root).short,
        core=lambda: _current_monitoring_core(omd_root),
    )


def general_version_infos(edition: Callable[[], str], core: Callable[[], str]) -> VersionInfo:
    return {
        "time": time.time(),
        "os": _get_os_info(),
        "version": __version__,
        "edition": edition(),
        "core": core(),
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
