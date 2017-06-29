#!/usr/bin/python
# encoding: utf-8

import os
import sys
import pytest

from testlib import repo_path, cmc_path
import testlib.pylint_cmk as pylint_cmk

# Mark all tests in this file to be pylint checks
pytestmark = pytest.mark.pylint

def test_pylint_checks(pylint_test_dir):
    f = file(pylint_test_dir + "/cmk-checks.py", "w")

    # add the modules
    for path in pylint_cmk.ordered_module_files():
        pylint_cmk.add_file(f, path)

    # Now add the checks
    for path in pylint_cmk.check_files(repo_path() + "/checks"):
        pylint_cmk.add_file(f, path)

    # Also add inventory plugins
    for path in pylint_cmk.check_files(repo_path() + "/inventory"):
        pylint_cmk.add_file(f, path)

    # Also add bakery plugins
    for path in pylint_cmk.check_files(cmc_path() + "/agents/bakery"):
        pylint_cmk.add_file(f, path)

    f.close()

    exit_code = pylint_cmk.run_pylint(pylint_test_dir)
    assert exit_code == 0, "PyLint found an error in checks, inventory " \
                           "or agent bakery plugins"
