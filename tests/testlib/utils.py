#!/usr/bin/env python3
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
from collections.abc import Callable
from pathlib import Path

from cmk.utils.version import Edition

logger = logging.getLogger()


def repo_path() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def cmk_path() -> str:  # TODO: Use Path. Why do we need an alias?
    return str(repo_path())


def cmc_path() -> str:  # TODO: Use Path
    return str(repo_path() / "enterprise")


def cme_path() -> str:  # TODO: Use Path
    return str(repo_path() / "managed")


def cpe_path() -> str:  # TODO: Use Path
    return str(repo_path() / "plus")


def is_enterprise_repo() -> bool:
    return os.path.exists(cmc_path())


def is_managed_repo() -> bool:
    return os.path.exists(cme_path())


def is_plus_repo() -> bool:
    return os.path.exists(cpe_path())


def is_containerized() -> bool:
    return (
        os.path.exists("/.dockerenv")
        or os.path.exists("/run/.containerenv")
        or os.environ.get("CMK_CONTAINERIZED") == "TRUE"
    )


def virtualenv_path() -> Path:
    venv = subprocess.check_output(
        [str(repo_path() / "scripts/run-pipenv"), "--bare", "--venv"], encoding="utf-8"
    )
    return Path(venv.rstrip("\n"))


def find_git_rm_mv_files(dirpath: Path) -> list[str]:
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


def current_base_branch_name() -> str:
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


def get_cmk_download_credentials_file() -> str:
    return "%s/.cmk-credentials" % os.environ["HOME"]


def get_cmk_download_credentials() -> tuple[str, str]:
    credentials_file_path = get_cmk_download_credentials_file()
    try:
        with open(credentials_file_path) as credentials_file:
            username, password = credentials_file.read().strip().split(":", maxsplit=1)
            return username, password
    except OSError:
        raise Exception("Missing %s file (Create with content: USER:PASSWORD)" % credentials_file)


def get_standard_linux_agent_output() -> str:
    with (repo_path() / "tests/integration/cmk/base/test-files/linux-agent-output").open(
        encoding="utf-8"
    ) as f:
        return f.read()


def site_id() -> str:
    site_id = os.environ.get("OMD_SITE")
    if site_id is not None:
        return site_id

    branch_name = branch_from_env(current_branch_name)

    # Split by / and get last element, remove unwanted chars
    branch_part = re.sub("[^a-zA-Z0-9_]", "", branch_name.split("/")[-1])
    site_id = "int_%s" % branch_part

    os.putenv("OMD_SITE", site_id)
    return site_id


def is_running_as_site_user() -> bool:
    try:
        return pwd.getpwuid(os.getuid()).pw_name == site_id()
    except KeyError:
        # Happens when no user with current UID exists (experienced in container with not existing
        # "-u" run argument set)
        return False


def add_python_paths() -> None:
    # make the repo directory available (cmk lib)
    sys.path.insert(0, cmk_path())

    # if not running as site user, make the livestatus module available
    if not is_running_as_site_user():
        if is_enterprise_repo():
            sys.path.insert(0, os.path.join(cmc_path()))
        sys.path.insert(0, os.path.join(cmk_path(), "livestatus/api/python"))
        sys.path.insert(0, os.path.join(cmk_path(), "omd/packages/omd"))


def package_hash_path(version: str, edition: Edition) -> Path:
    return Path(f"/tmp/cmk_package_hash_{version}_{edition.name}")


def version_spec_from_env(fallback: str | None = None) -> str:
    if version := os.environ.get("VERSION"):
        return version
    if fallback:
        return fallback
    raise RuntimeError("VERSION environment variable, e.g. 2016.12.22, is missing")


def _parse_raw_edition(raw_edition: str) -> Edition:
    try:
        return Edition[raw_edition.upper()]
    except KeyError:
        for edition in Edition:
            if edition.name == raw_edition:
                return edition
    raise ValueError(f"Unknown edition: {raw_edition}")


def edition_from_env(fallback: Edition | None = None) -> Edition:
    if raw_editon := os.environ.get("EDITION"):
        return _parse_raw_edition(raw_editon)
    if fallback:
        return fallback
    raise RuntimeError("EDITION environment variable, e.g. cre or enterprise, is missing")


def branch_from_env(fallback: str | Callable[[], str] | None = None) -> str:
    if branch := os.environ.get("BRANCH"):
        return branch
    if fallback:
        return fallback if isinstance(fallback, str) else fallback()
    raise RuntimeError("BRANCH environment variable, e.g. master, is missing")
