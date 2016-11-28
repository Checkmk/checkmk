#!/usr/bin/python
# encoding: utf-8

import os
import sys
from testlib import repo_path
import testlib.pylint_cmk as pylint_cmk

def test_pylint_inventory_plugins():
    base_path = pylint_cmk.get_test_dir()

    f = file(base_path + "/cmk-inventory-plugins.py", "w")

    # add the modules
    pylint_cmk.add_file(f, repo_path() + "/cmk_base/inventory_plugins.py")

    # Now add the checks
    for path in pylint_cmk.check_files(repo_path() + "/checks"):
        pylint_cmk.add_file(f, path)

    # Now add the inventory plugins
    for path in pylint_cmk.check_files(repo_path() + "/inventory"):
        pylint_cmk.add_file(f, path)

    f.close()

    exit_code = pylint_cmk.run_pylint(base_path, cleanup_test_dir=True)
    assert exit_code == 0, "PyLint found an error in inventory plugins"
