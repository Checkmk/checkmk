#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Create a ntop mkp

This script creates a mkp from all ntop relevant files, which will be excluded
from the enterprise builds.

"""

import json
from pathlib import Path
from subprocess import check_output
from typing import BinaryIO, cast

import cmk.utils.version as cmk_version
from cmk.utils import packaging

REPO_PATH = Path(__file__).resolve().parent.parent
GIT_HASH_SHORT = check_output(["git", "rev-parse", "--short", "HEAD"], encoding="utf-8").strip()
ENTERPRISE_PREFIX = "enterprise/cmk/gui/cee/"
with open(REPO_PATH / "buildscripts" / "scripts" / "lib" / "ntop_rules.json") as json_file:
    MKP_ABLE_NTOP_FILES = json.load(json_file)["mkp-able_ntop_files"]
NTOP_PACKAGE_INFO: packaging.PackageInfo = {
    "title": "Checkmk ntop integration",
    "name": "ntop",
    "description": (
        "This package ships extensions for the Checkmk user interface to make information from "
        "your ntop installations available in the Checkmk user interface. This includes ntop "
        "specific views and dashlets."
    ),
    "version": "1.0",
    "version.packaged": cmk_version.__version__,
    "version.min_required": cmk_version.__version__,
    "version.usable_until": None,
    "author": "tribe29 GmbH",
    "download_url": "https://checkmk.com/",
    "files": {
        "web": [ntop_file.replace(ENTERPRISE_PREFIX, "") for ntop_file in MKP_ABLE_NTOP_FILES]
    },
}

TARFILENAME = packaging.format_file_name(name="ntop", version=NTOP_PACKAGE_INFO["version"])

with Path(TARFILENAME).open("wb") as f:
    packaging.write_file(
        NTOP_PACKAGE_INFO,
        cast(BinaryIO, f),
        package_parts=packaging.get_repo_ntop_parts,
        config_parts=lambda: [],
    )
