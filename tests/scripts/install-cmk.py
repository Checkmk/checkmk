#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Is executed in container from git top level as working directory to install
the desired Checkmk version"""

import logging
import os
import subprocess
import sys

import requests

# Make the tests.testlib available
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from tests.testlib.common.repo import add_python_paths, current_base_branch_name
from tests.testlib.package_manager import ABCPackageManager
from tests.testlib.version import CMKVersion, version_from_env

from cmk.ccc.version import Edition

logging.basicConfig(level=logging.INFO, format="%(asctime)-15s %(filename)s %(message)s")
logger = logging.getLogger()

CMK_OK = 0
CMK_DOWNLOAD_ERROR = 11
CMK_INSTALL_ERROR = 22


def main():
    add_python_paths()
    version = version_from_env(
        fallback_version_spec=CMKVersion.DAILY,
        fallback_edition=Edition.CEE,
        fallback_branch=current_base_branch_name,
    )
    logger.info(
        "Version: %s (%s), Edition: %s, Branch: %s",
        version.version,
        version.version_rc_aware,
        version.edition.long,
        version.branch,
    )

    if version.is_installed():
        logger.info("Already installed. Terminating.")
        return CMK_OK

    manager = ABCPackageManager.factory()
    try:
        manager.install(version.version_rc_aware, version.edition)
    except subprocess.CalledProcessError as excp:
        excp.add_note(f"Failed to install {version.edition} {version.version}!")
        logger.exception(excp)
        return CMK_INSTALL_ERROR
    except requests.exceptions.HTTPError as excp:
        excp.add_note(f"Failed to download {version.edition} {version.version}!")
        logger.exception(excp)
        return CMK_DOWNLOAD_ERROR

    return CMK_OK


if __name__ == "__main__":
    sys.exit(main())
