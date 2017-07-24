#!/usr/bin/python
# encoding: utf-8

import os
import sys
import pytest

from testlib import cmk_path, cmc_path, cme_path
import testlib.pylint_cmk as pylint_cmk

# Mark all tests in this file to be pylint checks
pytestmark = pytest.mark.pylint

def test_pylint_misc():
    search_paths = [
        cmk_path() + "/cmk_base",
        cmk_path() + "/cmk_base/modes",
        cmk_path() + "/cmk_base/automations",
        cmk_path() + "/cmk_base/default_config",

        cmc_path() + "/cmk_base",
        cmc_path() + "/cmk_base/cee",
        cmc_path() + "/cmk_base/modes",
        cmc_path() + "/cmk_base/automations",
        cmc_path() + "/cmk_base/default_config",

        cme_path() + "/cmk_base/default_config",

        cmk_path() + "/lib",
        cmk_path() + "/bin",
        cmk_path() + "/notifications",
        cmk_path() + "/agents/plugins",
        cmk_path() + "/active_checks",
        cmc_path() + "/agents/plugins",
        cmc_path() + "/bin",
        cmc_path() + "/misc",
    ]

    checked, worst = 0, 0
    for path in search_paths:
        worst = max(worst, pylint_cmk.run_pylint(path))
        checked += 1

    assert checked > 0, "Did not find a file to check!"
    assert worst == 0, "At least one issue found"
