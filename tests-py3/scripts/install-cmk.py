#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Is executed in container from git top level as working directory to install
the desired Checkmk version"""

import os
import sys
import logging

# Make the testlib available
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from testlib.utils import (
    current_base_branch_name,
    add_python_paths,
)
from testlib.version import CMKVersion

logging.basicConfig(level=logging.INFO, format='%(asctime)-15s %(filename)s %(message)s')
logger = logging.getLogger()


def main():
    add_python_paths()

    version_spec = os.environ.get("VERSION", CMKVersion.DAILY)
    edition = os.environ.get("EDITION", CMKVersion.CEE)
    branch = os.environ.get("BRANCH", current_base_branch_name())

    logger.info("Version: %s, Edition: %s, Branch: %s", version_spec, edition, branch)
    version = CMKVersion(version_spec, edition, branch)

    if version.is_installed():
        logger.info("Version %s is already installed. Terminating.")
        return 0

    version.install()
    return 0


if __name__ == "__main__":
    sys.exit(main())
