#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Check_MK's library for code used by different components of Check_MK.

This library is currently handled as internal module of Check_MK and
does not offer stable APIs. The code may change at any time."""

__version__ = "1.7.0i1"

import errno
import os
from pathlib import Path
import sys
import time
from typing import Any, Dict, Text

import six

import cmk.utils.paths
from cmk.utils.encoding import ensure_unicode
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.i18n import _
import cmk.utils.cmk_subprocess as subprocess


def omd_version():
    # type: () -> Text
    version_link = Path(cmk.utils.paths.omd_root).joinpath("version")
    return ensure_unicode(version_link.resolve().name)


def omd_site():
    # type: () -> str
    try:
        return os.environ["OMD_SITE"]
    except KeyError:
        raise MKGeneralException(
            _("OMD_SITE environment variable not set. You can "
              "only execute this in an OMD site."))


def edition_short():
    # type: () -> Text
    """Can currently either return \"cre\" or \"cee\"."""
    parts = omd_version().split(".")
    if parts[-1] == "demo":
        return six.text_type(parts[-2])

    return six.text_type(parts[-1])


def is_enterprise_edition():
    # type: () -> bool
    return edition_short() == "cee"


def is_raw_edition():
    # type: () -> bool
    return edition_short() == "cre"


def is_managed_edition():
    # type: () -> bool
    return edition_short() == "cme"


def is_demo():
    # type: () -> bool
    parts = omd_version().split(".")
    return parts[-1] == "demo"


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


def get_general_version_infos():
    # type: () -> Dict[str, Any]
    return {
        "time": time.time(),
        "os": _get_os_info(),
        "version": __version__,
        "edition": edition_short(),
        "core": _current_monitoring_core(),
        "python_version": sys.version,
        "python_paths": sys.path,
    }


def _get_os_info():
    # type: () -> Text
    if "OMD_ROOT" in os.environ:
        return open(os.environ["OMD_ROOT"] + "/share/omd/distro.info").readline().split(
            "=", 1)[1].strip()
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
    return "UNKNOWN"


def _current_monitoring_core():
    # type: () -> Text
    try:
        p = subprocess.Popen(
            ["omd", "config", "show", "CORE"],
            close_fds=True,
            stdin=open(os.devnull),
            stdout=subprocess.PIPE,
            stderr=open(os.devnull, "w"),
            encoding="utf-8",
        )
        return p.communicate()[0]
    except OSError as e:
        # Allow running unit tests on systems without omd installed (e.g. on travis)
        if e.errno != errno.ENOENT:
            raise
        return "UNKNOWN"
