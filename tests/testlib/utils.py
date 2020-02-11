# pylint: disable=redefined-outer-name

from __future__ import print_function

import fcntl
import os
import re
import time
import subprocess
import sys
import pwd
from contextlib import contextmanager
import logging

# Explicitly check for Python 3 (which is understood by mypy)
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


def virtualenv_path():
    venv = subprocess.check_output(
        [repo_path() + "/scripts/run-pipenv",
         str(sys.version_info[0]), "--bare", "--venv"])
    if not isinstance(venv, six.text_type):
        venv = venv.decode("utf-8")
    return Path(venv.rstrip("\n"))


def current_branch_name():
    branch_name = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    if not isinstance(branch_name, six.text_type):
        branch_name = branch_name.decode("utf-8")
    return branch_name.split("\n", 1)[0]


def current_base_branch_name():
    branch_name = current_branch_name()

    # Detect which other branch this one was created from. We do this by going back the
    # current branches git log one step by another and check which branches contain these
    # commits. Only search for our main (master + major-version) branches
    commits = subprocess.check_output(["git", "rev-list", "--max-count=30", branch_name])
    if not isinstance(commits, six.text_type):
        commits = commits.decode("utf-8")

    for commit in commits.strip().split("\n"):
        heads = subprocess.check_output(
            ["git", "branch", "--format=%(refname)", "--contains", commit])
        if not isinstance(heads, six.text_type):
            heads = heads.decode("utf-8")

        for head in heads.strip().split("\n"):
            if head == "refs/heads/master":
                return "master"

            if re.match(r"^refs/heads/[0-9]+\.[0-9]+\.[0-9]+$", head):
                return head

    logger.info("Could not determine base branch, using %s", branch_name)
    return branch_name


def get_cmk_download_credentials_file():
    return "%s/.cmk-credentials" % os.environ["HOME"]


def get_cmk_download_credentials():
    credentials_file = get_cmk_download_credentials_file()
    try:
        return tuple(open(credentials_file).read().strip().split(":"))
    except IOError:
        raise Exception("Missing %s file (Create with content: USER:PASSWORD)" % credentials_file)


def site_id():
    site_id = os.environ.get("OMD_SITE")
    if site_id is not None:
        return site_id

    branch_name = os.environ.get("BRANCH", current_branch_name())
    # Split by / and get last element, remove unwanted chars
    branch_part = re.sub("[^a-zA-Z0-9_]", "", branch_name.split("/")[-1])
    site_id = "int_%s" % branch_part

    os.putenv("OMD_SITE", site_id)
    return site_id


def is_running_as_site_user():
    return pwd.getpwuid(os.getuid()).pw_name == site_id()


def add_python_paths():
    # make the testlib available to the test modules
    sys.path.insert(0, os.path.dirname(__file__))
    # make the repo directory available (cmk lib)
    sys.path.insert(0, cmk_path())

    # if not running as site user, make the livestatus module available
    if not is_running_as_site_user():
        sys.path.insert(0, os.path.join(cmk_path(), "livestatus/api/python"))
        sys.path.insert(0, os.path.join(cmk_path(), "omd/packages/omd"))


def SiteActionLock():
    return InterProcessLock("/tmp/cmk-test-create-site")


# Used fasteners before, but that was using a file mode that made it impossible to do
# inter process locking involving different users (different sites)
@contextmanager
def InterProcessLock(filename):
    fd = None
    try:
        print("[%0.2f] Getting lock: %s" % (time.time(), filename))
        # Need to unset umask here to get the permissions we need because
        # os.open() mode is using the given mode not as absolute mode, but
        # respects the umask "mode & ~umask" (See "man 2 open").
        old_umask = os.umask(0)
        try:
            fd = os.open(filename, os.O_RDONLY | os.O_CREAT, 0o666)
        finally:
            os.umask(old_umask)

        # Handle the case where the file has been renamed/overwritten between
        # file creation and locking
        while True:
            fcntl.flock(fd, fcntl.LOCK_EX)

            try:
                fd_new = os.open(filename, os.O_RDONLY | os.O_CREAT, 0o666)
            finally:
                os.umask(old_umask)

            if os.path.sameopenfile(fd, fd_new):
                os.close(fd_new)
                break

            os.close(fd)
            fd = fd_new

        # Prevent inheritance of the FD+lock to subprocesses
        prev_flags = fcntl.fcntl(fd, fcntl.F_GETFD)
        fcntl.fcntl(fd, fcntl.F_SETFD, prev_flags | fcntl.FD_CLOEXEC)

        print("[%0.2f] Have lock: %s" % (time.time(), filename))
        yield
        fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        print("[%0.2f] Released lock: %s" % (time.time(), filename))
        if fd:
            os.close(fd)


class DummyApplication(object):  # pylint: disable=useless-object-inheritance
    def __init__(self, environ, start_response):
        self._environ = environ
        self._start_response = start_response
