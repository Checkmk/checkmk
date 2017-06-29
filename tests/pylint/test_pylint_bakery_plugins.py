#!/usr/bin/python
# encoding: utf-8

import os
import sys
from testlib import repo_path, cmc_path
import testlib.pylint_cmk as pylint_cmk

def test_pylint_bakery_plugins(pylint_test_dir):
    f = file(pylint_test_dir + "/cmk-bakery-plugins.py", "w")

    pylint_cmk.add_file(f, os.path.realpath(os.path.join(cmc_path(), "cmk_base/cee/agent_bakery_plugins.py")))

    # Also add bakery plugins
    for path in pylint_cmk.check_files(os.path.join(cmc_path(), "agents/bakery")):
        pylint_cmk.add_file(f, path)

    f.close()

    exit_code = pylint_cmk.run_pylint(pylint_test_dir)
    assert exit_code == 0, "PyLint found an error in agent bakery plugins"
