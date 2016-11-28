#!/usr/bin/python
# encoding: utf-8

import os
import sys
from testlib import repo_path
import testlib.pylint_cmk as pylint_cmk

def test_pylint_bakery_plugins():
    base_path = pylint_cmk.get_test_dir()

    f = file(base_path + "/cmk-bakery-plugins.py", "w")

    # add the modules
    for path in pylint_cmk.ordered_module_files():
        pylint_cmk.add_file(f, path)

    # Also add bakery plugins
    for path in pylint_cmk.check_files(os.path.realpath(repo_path()
                                       + "/../cmc/agents/bakery")):
        pylint_cmk.add_file(f, path)

    f.close()

    exit_code = pylint_cmk.run_pylint(base_path, cleanup_test_dir=True)
    assert exit_code == 0, "PyLint found an error in agent bakery plugins"
