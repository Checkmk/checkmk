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

import os
import sys
import pipes
import subprocess
import logging
import shutil
from pathlib import Path

# Make the testlib available
script_path = Path(__file__).resolve()
sys.path.insert(0, str(script_path.parent.parent))
# Make the repo directory available (cmk/livestatus lib)
sys.path.insert(0, str(script_path.parent.parent.parent))

from testlib.utils import is_running_as_site_user, cmk_path, current_base_branch_name
from testlib.site import get_site_factory
from testlib.version import CMKVersion

logging.basicConfig(level=logging.INFO, format='%(asctime)-15s %(filename)s %(message)s')
logger = logging.getLogger()


def main(args):
    if is_running_as_site_user():
        raise Exception()

    _centos6_mtab_fix()

    logger.info("===============================================")
    logger.info("Setting up site")
    logger.info("===============================================")

    version = os.environ.get("VERSION", CMKVersion.DAILY)
    sf = get_site_factory(prefix="int_",
                          update_from_git=version == "git",
                          install_test_python_modules=True)

    if os.environ.get("REUSE"):
        logger.info("Reuse existing site")
        site = sf.get_existing_site(current_base_branch_name())
        site.start()
    else:
        logger.info("Creating new site")
        site = sf.get_site(current_base_branch_name())

    logger.info("Site %s is ready!", site.id)

    logger.info("===============================================")
    logger.info("Switching to site context")
    logger.info("===============================================")

    try:
        return _execute_as_site_user(site, args)
    finally:
        if os.path.exists("/results"):
            shutil.rmtree("/results")
            os.mkdir("/results")
        shutil.copy(site.path("junit.xml"), "/results")
        shutil.copytree(site.path("var/log"), "/results/logs")


def _centos6_mtab_fix():
    # Workaround to fix site tmpfs unmount issue during mkbackup restore tests.
    # unmount of /opt/omd/sites/[site]/tmp does not work as site user in case
    # /etc/mtab is the symlink to /proc/mounts.
    # Don't try to move this to the Dockerfile. It does not work.
    if os.environ.get("DISTRO") == "centos-6" and Path("/.dockerenv").exists():
        mtab = Path("/etc/mtab")
        if mtab.exists():
            mtab.unlink()
        with mtab.open("w") as f, Path("/proc/mounts").open() as s:
            f.write(s.read())


def _execute_as_site_user(site, args):
    env_vars = {
        "VERSION": site.version.version_spec,
        "REUSE": "1" if site.reuse else "0",
        "BRANCH": site.version._branch,
    }
    for varname in [
            "WORKSPACE", "PYTEST_ADDOPTS", "BANDIT_OUTPUT_ARGS", "SHELLCHECK_OUTPUT_ARGS",
            "PYLINT_ARGS"
    ]:
        if varname in os.environ:
            env_vars[varname] = os.environ[varname]

    env_var_str = " ".join(["%s=%s" % (k, pipes.quote(v)) for k, v in env_vars.items()]) + " "

    cmd_parts = [
        "python3",
        site.path("local/bin/pytest"), "-T", "integration", "-p", "no:cov", "--junitxml",
        site.path("junit.xml")
    ] + args

    cmd = "cd %s && " % pipes.quote(cmk_path())
    cmd += env_var_str + subprocess.list2cmdline(cmd_parts)
    args = ["/usr/bin/sudo", "--", "/bin/su", "-l", site.id, "-c", cmd]
    logger.info("Executing: %r", subprocess.list2cmdline(args))
    return subprocess.call(args, stderr=subprocess.STDOUT)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
