#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=redefined-outer-name

import logging
import os
import pwd
import re
import subprocess
import sys
from pathlib import Path
from typing import List

logger = logging.getLogger()


def repo_path() -> str:
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))


def cmk_path():
    return repo_path()


def cmc_path():
    return repo_path() + "/enterprise"


def cme_path():
    return repo_path() + "/managed"


def cpe_path():
    return repo_path() + "/plus"


def is_enterprise_repo():
    return os.path.exists(cmc_path())


def is_managed_repo() -> bool:
    return os.path.exists(cme_path())


def is_plus_repo() -> bool:
    return os.path.exists(cpe_path())


def virtualenv_path() -> Path:
    venv = subprocess.check_output(
        [repo_path() + "/scripts/run-pipenv", "--bare", "--venv"], encoding="utf-8"
    )
    return Path(venv.rstrip("\n"))


def find_git_rm_mv_files(dirpath: Path) -> List[str]:
    del_files = []

    out = subprocess.check_output(
        [
            "git",
            "-C",
            str(dirpath),
            "status",
            str(dirpath),
        ],
        encoding="utf-8",
    ).split("\n")

    for line in out:
        if "deleted:" in line or "renamed:" in line:
            # Ignore files in subdirs of dirpath
            if line.split(dirpath.name)[1].count("/") > 1:
                continue

            filename = line.split("/")[-1]
            del_files.append(filename)
    return del_files


def current_branch_name() -> str:
    branch_name = subprocess.check_output(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"], encoding="utf-8"
    )
    return branch_name.split("\n", 1)[0]


def current_base_branch_name():
    branch_name = current_branch_name()

    # Detect which other branch this one was created from. We do this by going back the
    # current branches git log one step by another and check which branches contain these
    # commits. Only search for our main (master + major-version) branches
    commits = subprocess.check_output(
        ["git", "rev-list", "--max-count=30", branch_name], encoding="utf-8"
    )
    for commit in commits.strip().split("\n"):
        # Asking for remote heads here, since the git repos checked out by jenkins do not create all
        # the branches locally

        # --format=%(refname): Is not supported by all distros :(
        #
        # heads = subprocess.check_output(
        #    ["git", "branch", "-r", "--format=%(refname)", "--contains", commit])
        # if not isinstance(heads, str):
        #    heads = heads.decode("utf-8")

        # for head in heads.strip().split("\n"):
        #    if head == "refs/remotes/origin/master":
        #        return "master"

        #    if re.match(r"^refs/remotes/origin/[0-9]+\.[0-9]+\.[0-9]+$", head):
        #        return head

        lines = subprocess.check_output(
            ["git", "branch", "-r", "--contains", commit], encoding="utf-8"
        )
        for line in lines.strip().split("\n"):
            if not line:
                continue
            head = line.split()[0]

            if head == "origin/master":
                return "master"

            if re.match(r"^origin/[0-9]+\.[0-9]+\.[0-9]+$", head):
                return head[7:]

    logger.warning("Could not determine base branch, using %s", branch_name)
    return branch_name


def get_cmk_download_credentials_file():
    return "%s/.cmk-credentials" % os.environ["HOME"]


def get_cmk_download_credentials():
    credentials_file = get_cmk_download_credentials_file()
    try:
        return tuple(open(credentials_file).read().strip().split(":"))
    except IOError:
        raise Exception("Missing %s file (Create with content: USER:PASSWORD)" % credentials_file)


def get_standard_linux_agent_output():
    with Path(repo_path(), "tests/integration/cmk/base/test-files/linux-agent-output").open(
        encoding="utf-8"
    ) as f:
        return f.read()


def site_id():
    site_id = os.environ.get("OMD_SITE")
    if site_id is not None:
        return site_id

    branch_name = os.environ.get("BRANCH")
    if branch_name is None:
        branch_name = current_branch_name()

    # Split by / and get last element, remove unwanted chars
    branch_part = re.sub("[^a-zA-Z0-9_]", "", branch_name.split("/")[-1])
    site_id = "int_%s" % branch_part

    os.putenv("OMD_SITE", site_id)
    return site_id


def is_running_as_site_user():
    try:
        return pwd.getpwuid(os.getuid()).pw_name == site_id()
    except KeyError:
        # Happens when no user with current UID exists (experienced in container with not existing
        # "-u" run argument set)
        return False


def add_python_paths():
    # make the repo directory available (cmk lib)
    sys.path.insert(0, cmk_path())

    # if not running as site user, make the livestatus module available
    if not is_running_as_site_user():
        sys.path.insert(0, os.path.join(cmk_path(), "livestatus/api/python"))
        sys.path.insert(0, os.path.join(cmk_path(), "omd/packages/omd"))


def package_hash_path(version: str, edition: str) -> Path:
    return Path(f"/tmp/cmk_package_hash_{version}_{edition}")
