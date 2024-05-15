#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Is executed in container from git top level as working directory to install
the desired Checkmk version"""

import logging
import os
import sys

# Make the tests.testlib available
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from tests.testlib.utils import add_python_paths, current_base_branch_name
from tests.testlib.version import ABCPackageManager, CMKVersion, version_from_env

from cmk.utils.version import Edition

logging.basicConfig(level=logging.INFO, format="%(asctime)-15s %(filename)s %(message)s")
logger = logging.getLogger()


def main():
    add_python_paths()
    version = version_from_env(
        fallback_version_spec=CMKVersion.DAILY,
        fallback_edition=Edition.CEE,
        fallback_branch=current_base_branch_name,
    )
    logger.info(
        "Version: %s, Edition: %s, Branch: %s",
        version.version,
        version.edition.long,
        version.branch,
    )

    if version.is_installed():
        logger.info("Already installed. Terminating.")
        return 0

    manager = ABCPackageManager.factory()
    manager.install(version.version, version.edition)

    if not version.is_installed():
        logger.error("Failed not install version")
        raise Exception(f"Failed to install {version.edition} {version.version}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
