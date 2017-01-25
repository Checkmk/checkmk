#!/usr/bin/python
# encoding: utf-8

import os
import sys
import pytest

from testlib import repo_path
import testlib.pylint_cmk as pylint_cmk

# Mark all tests in this file to be pylint checks
pytestmark = pytest.mark.pylint

def test_pylint_checks():
    base_path = pylint_cmk.get_test_dir()

    f = file(base_path + "/cmk-checks.py", "w")

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
    for path in pylint_cmk.check_files(os.path.realpath(repo_path()
                                       + "/../cmc/agents/bakery")):
        pylint_cmk.add_file(f, path)

    f.close()

    exit_code = pylint_cmk.run_pylint(base_path, cleanup_test_dir=True)
    assert exit_code == 0, "PyLint found an error in checks, inventory " \
                           "or agent bakery plugins"
