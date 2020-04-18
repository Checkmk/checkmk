#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=redefined-outer-name

from __future__ import print_function

import logging
import os
import pwd
import re
import subprocess
import sys
from typing import Optional  # pylint: disable=unused-import

if sys.version_info[0] >= 3:
    from pathlib import Path  # pylint: disable=import-error
else:
    from pathlib2 import Path  # pylint: disable=import-error

import six

logger = logging.getLogger()


def repo_path():
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))


def cmk_path():
    return repo_path()


def cmc_path():
    return repo_path() + "/enterprise"


def cme_path():
    return repo_path() + "/managed"


def is_enterprise_repo():
    return os.path.exists(cmc_path())


def is_managed_repo():
    return os.path.exists(cme_path())


def virtualenv_path(version=None):
    # type: (Optional[int]) -> Path
    if version is None:
        version = sys.version_info[0]

    venv = subprocess.check_output(
        [repo_path() + "/scripts/run-pipenv",
         str(version), "--bare", "--venv"])
    return Path(six.ensure_str(venv).rstrip("\n"))


def current_branch_name():
    # type: () -> str
    branch_name = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    return six.ensure_str(branch_name).split("\n", 1)[0]


def current_base_branch_name():
    branch_name = current_branch_name()

    # Detect which other branch this one was created from. We do this by going back the
    # current branches git log one step by another and check which branches contain these
    # commits. Only search for our main (master + major-version) branches
    commits = subprocess.check_output(["git", "rev-list", "--max-count=30", branch_name])
    for commit in six.ensure_str(commits).strip().split("\n"):
        # Asking for remote heads here, since the git repos checked out by jenkins do not create all
        # the branches locally

        # --format=%(refname): Is not supported by all distros :(
        #
        #heads = subprocess.check_output(
        #    ["git", "branch", "-r", "--format=%(refname)", "--contains", commit])
        #if not isinstance(heads, six.text_type):
        #    heads = heads.decode("utf-8")

        #for head in heads.strip().split("\n"):
        #    if head == "refs/remotes/origin/master":
        #        return "master"

        #    if re.match(r"^refs/remotes/origin/[0-9]+\.[0-9]+\.[0-9]+$", head):
        #        return head

        lines = subprocess.check_output(["git", "branch", "-r", "--contains", commit])
        for line in six.ensure_str(lines).strip().split("\n"):
            if not line:
                continue
            head = line.split()[0]

            if head == "origin/master":
                return "master"

            if re.match(r"^origin/[0-9]+\.[0-9]+\.[0-9]+$", head):
                return head

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
    with Path(repo_path(), "tests-py3/integration/cmk/base/test-files/linux-agent-output").open(
            encoding="utf-8") as f:
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
    # make the testlib available to the test modules
    sys.path.insert(0, os.path.dirname(__file__))
    # make the repo directory available (cmk lib)
    sys.path.insert(0, cmk_path())

    # if not running as site user, make the livestatus module available
    if not is_running_as_site_user():
        sys.path.insert(0, os.path.join(cmk_path(), "livestatus/api/python"))
        sys.path.insert(0, os.path.join(cmk_path(), "omd/packages/omd"))


class DummyApplication(object):  # pylint: disable=useless-object-inheritance
    def __init__(self, environ, start_response):
        self._environ = environ
        self._start_response = start_response
