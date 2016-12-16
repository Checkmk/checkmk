#!/usr/bin/python
# encoding: utf-8

import os
import sys

from testlib import repo_path
import testlib.pylint_cmk as pylint_cmk

def test_pylint_misc():
    search_paths = [
        "cmk_base",
        "../cmc/cmk_base",
        "lib",
        "bin",
        "notifications",
        "agents/plugins",
        "active_checks",
        "../cmc/agents/plugins",
        "../cmc/bin",
        "../cmc/misc",
    ]

    checked, worst = 0, 0
    for rel_path in search_paths:
        path = os.path.realpath(repo_path() + "/" + rel_path)
        worst = max(worst, pylint_cmk.run_pylint(path))
        checked += 1

    assert checked > 0, "Did not find a file to check!"
    assert worst == 0, "At least one issue found"
