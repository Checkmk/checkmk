#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Starts a docker container and executes tests in it

The tests are executed in the container using the MAKE_TARGET given as first argument
to this script.

The exit code is used as exit code of this script and the resulting files are
saved in the given RESULT_PATH.

Environment variables VERSION, EDITION, BRANCH affect the package used for
the test.
"""

import argparse
import logging
import os
import sys
import tempfile
from pathlib import Path
from typing import List

# Make the tests.testlib available
sys.path.insert(0, os.path.dirname((os.path.dirname(os.path.dirname(os.path.realpath(__file__))))))

from tests.testlib.containers import execute_tests_in_container
from tests.testlib.utils import current_base_branch_name
from tests.testlib.version import CMKVersion

logging.basicConfig(level=logging.INFO, format="%(asctime)-15s %(filename)s %(message)s")
logger = logging.getLogger()


def main(raw_args):
    args = _parse_arguments(raw_args)

    distro_name = _os_environ_get("DISTRO", "ubuntu-20.04")
    docker_tag = _os_environ_get("DOCKER_TAG", "%s-latest" % current_base_branch_name())
    version_spec = _os_environ_get("VERSION", CMKVersion.GIT)
    edition = _os_environ_get("EDITION", CMKVersion.CEE)
    branch = _os_environ_get("BRANCH", current_base_branch_name())

    version = CMKVersion(version_spec, edition, branch)
    logger.info(
        "Version: %s (%s), Edition: %s, Branch: %s",
        version.version,
        version.version_spec,
        edition,
        branch,
    )

    result_path_str = _os_environ_get("RESULT_PATH", "")
    if result_path_str:
        result_path = Path(result_path_str)
    else:
        # Only create the temporary directory when RESULT_PATH not given. And keep it after the
        # script finishes. Otherwise the results are lost.
        result_path = Path(tempfile.mkdtemp(prefix="cmk-run-dockerized-"))

    result_path.mkdir(parents=True, exist_ok=True)
    logger.info("Prepared result path: %s", result_path)

    return execute_tests_in_container(
        distro_name=distro_name,
        docker_tag=docker_tag,
        command=["make", "-C", "tests", args.make_target],
        version=version,
        result_path=result_path,
        interactive=args.make_target == "debug",
    )


def _os_environ_get(key: str, default: str) -> str:
    result = os.environ.get(key, default)
    if key in os.environ:
        logger.info('environment contains "%s" => "%s"', key, result)
    else:
        logger.info('environment does not contain "%s", using default "%s"', key, result)
    return result


def _parse_arguments(args: List[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "make_target",
        metavar="MAKE_TARGET",
        help="The make target to execute in test-py3 directory",
    )

    return p.parse_args(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
