#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Starts a docker container and executes the GUI crawl tests in it

The GUI crawl tests create a site and crawl all pages of the site to find errors.
The exit code is used as exit code of this script and the resulting files are
saved in the given RESULT_PATH.

Environment variables VERSION, EDITION, BRANCH affect the package used for
the test.
"""

import os
import sys
import logging
import tempfile
from pathlib import Path
from typing import Optional  # pylint: disable=unused-import

# Make the testlib available
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from testlib.utils import current_base_branch_name
from testlib.version import CMKVersion
from testlib.containers import execute_tests_in_container

logging.basicConfig(level=logging.INFO, format='%(asctime)-15s %(filename)s %(message)s')
logger = logging.getLogger()


def main():
    with tempfile.TemporaryDirectory(prefix="gui_crawl") as tmpdir:
        tmp_path = Path(tmpdir)

        version_spec = os.environ.get("VERSION", CMKVersion.GIT)
        edition = os.environ.get("EDITION", CMKVersion.CEE)
        branch = os.environ.get("BRANCH", current_base_branch_name())

        version = CMKVersion(version_spec, edition, branch, check_version_available=False)
        logger.info("Version: %s, Edition: %s, Branch: %s", version.version, edition, branch)

        result_path = Path(os.environ.get("RESULT_PATH", tmp_path.joinpath("results")))
        result_path.mkdir(parents=True, exist_ok=True)
        logger.info("Prepared result path: %s", result_path)

        return execute_tests_in_container(
            command=["make", "-C", "tests-py3", "test-gui-crawl"],
            version=version,
            result_path=result_path,
        )


if __name__ == "__main__":
    sys.exit(main())
