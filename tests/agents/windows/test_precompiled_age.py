#!/usr/bin/python
# encoding: utf-8

import os
import glob
from testlib import cmk_path

precompiled_files = [
    'check_mk_agent.exe',
    'check_mk_agent-64.exe',
    'check_mk_agent.unversioned.exe',
    'check_mk_agent-64.unversioned.exe',
    'install_agent-64.exe',
    'install_agent.exe',
    'check_mk_agent.msi',
]


def test_precompiled_files_present():
    for filename in precompiled_files:
        path = "%s/agents/windows/%s" % (cmk_path(), filename)
        assert os.path.exists(path)


def test_precompiled_file_ages():
    newest_source_file, newest_source_time = find_newest_source_file()

    for filename in precompiled_files:
        path = "%s/agents/windows/%s" % (cmk_path(), filename)
        commit_time = last_commit_time(path)
        assert commit_time > newest_source_time, \
            "%s is older than source code file %s" % (path, newest_source_file)


def find_newest_source_file():
    newest_path, newest_commit_time = None, 0

    for dirpath, dirnames, filenames in os.walk("%s/agents/windows" % cmk_path()):
        for filename in filenames:
            path = "%s/%s" % (dirpath, filename)

            if not filename.endswith(".cc") and not filename.endswith(".h"):
                continue

            if "/msibuild/" in path:
                continue

            commit_time = last_commit_time(path)
            if commit_time > newest_commit_time:
                newest_path, newest_commit_time = path, commit_time

    assert newest_path != None
    assert newest_commit_time != 0

    return newest_path, newest_commit_time


def last_commit_time(path):
    lines = os.popen('unset GIT_DIR ; cd "%s" ; '
        'git log -n 1 --date=raw -- "%s"' % (os.path.dirname(path), path)).readlines()
    timestamp = int(lines[2].split()[1])
    return timestamp
