#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Is executed to initialize an integration test.

It creates the test site, prepares it for testing and executes pytest in the site
context.

The exit code is used as exit code of this script and the resulting files are
saved in the given RESULT_PATH.

Environment variables VERSION, EDITION, BRANCH affect the package used for
the test.
"""

import logging
import os
import pipes
import subprocess
import sys
from pathlib import Path

# Make the tests.testlib available
script_path = Path(__file__).resolve()
sys.path.insert(0, str(script_path.parent.parent.parent))

from tests.testlib.site import get_site_factory, Site
from tests.testlib.utils import cmk_path, is_running_as_site_user
from tests.testlib.version import CMKVersion

logging.basicConfig(level=logging.INFO, format="%(asctime)-15s %(filename)s %(message)s")
logger = logging.getLogger()


def main(args):
    if is_running_as_site_user():
        raise Exception()

    logger.info("===============================================")
    logger.info("Setting up site")
    logger.info("===============================================")

    version = os.environ.get("VERSION", CMKVersion.DAILY)
    sf = get_site_factory(
        prefix="int_", update_from_git=version == "git", install_test_python_modules=True
    )

    site = sf.get_existing_site("test")

    if os.environ.get("REUSE"):
        logger.info("Reuse previously existing site in case it exists (REUSE=1)")
        if not site.exists():
            logger.info("Creating new site")
            site = sf.get_site("test")
        else:
            logger.info("Reuse existing site")
            site.start()
    else:
        if site.exists():
            logger.info("Remove previously existing site (REUSE=0)")
            site.rm()

        logger.info("Creating new site")
        site = sf.get_site("test")

    logger.info("Site %s is ready!", site.id)

    logger.info("===============================================")
    logger.info("Switching to site context")
    logger.info("===============================================")

    try:
        return _execute_as_site_user(site, args)
    finally:
        sf.save_results()


def _execute_as_site_user(site: Site, args):
    env_vars = {
        "VERSION": site.version.version_spec,
        "EDITION": site.version.edition(),
        "REUSE": "1" if site.reuse else "0",
        "BRANCH": site.version._branch,
    }
    for varname in [
        "WORKSPACE",
        "PYTEST_ADDOPTS",
        "BANDIT_OUTPUT_ARGS",
        "SHELLCHECK_OUTPUT_ARGS",
        "PYLINT_ARGS",
        "CI",
    ]:
        if varname in os.environ:
            env_vars[varname] = os.environ[varname]

    env_var_str = " ".join(["%s=%s" % (k, pipes.quote(v)) for k, v in env_vars.items()]) + " "

    cmd_parts = [
        "python3",
        site.path("local/bin/pytest"),
        "-p",
        "no:cov",
        "--log-cli-level=DEBUG",
        "--log-cli-format=%(asctime)s %(levelname)s %(message)s",
        "--junitxml",
        site.path("junit.xml"),
        "-T",
        "integration",
    ] + args

    cmd = "cd %s && " % pipes.quote(cmk_path())
    cmd += env_var_str + subprocess.list2cmdline(cmd_parts)
    args = ["/usr/bin/sudo", "--", "/bin/su", "-l", site.id, "-c", cmd]
    logger.info("Executing: %r", subprocess.list2cmdline(args))
    return subprocess.call(args, stderr=subprocess.STDOUT)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
