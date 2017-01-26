#!/usr/bin/python
# encoding: utf-8

import os
import glob
import pytest
from testlib import cmc_path

# Mark all tests in this file to be executed in the git context
pytestmark = pytest.mark.git

precompiled_files = [
    'plugins/cmk-update-agent.exe'
]


def test_precompiled_files_present():
    for filename in precompiled_files:
        path = "%s/agents/windows/%s" % (cmc_path(), filename)
        assert os.path.exists(path)


def test_precompiled_file_ages():
    newest_source_file, newest_source_time = find_newest_source_file()

    for filename in precompiled_files:
        path = "%s/agents/windows/%s" % (cmc_path(), filename)
        commit_time = last_commit_time(path)
        assert commit_time >= newest_source_time, \
            "%s is older than source code file %s" % (path, newest_source_file)


def find_newest_source_file():
    path = "%s/agents/plugins/cmk-update-agent" % cmc_path()
    return path, last_commit_time(path)


def last_commit_time(path):
    lines = os.popen('unset GIT_DIR ; cd "%s" ; '
        'git log -n 1 --date=raw -- "%s"' % (os.path.dirname(path), path)).readlines()
    timestamp = int(lines[2].split()[1])
    return timestamp
