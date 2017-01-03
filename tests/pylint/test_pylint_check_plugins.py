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

    # Fake data structures where checks register (See cmk_base/checks.py)
    f.write("""
check_info                         = {}
check_includes                     = {}
precompile_params                  = {}
check_default_levels               = {}
factory_settings                   = {}
check_config_variables             = []
snmp_info                          = {}
snmp_scan_functions                = {}
active_check_info                  = {}
special_agent_info                 = {}
""")

    # add the modules
    pylint_cmk.add_file(f, repo_path() + "/cmk_base/check_api.py")

    # Now add the checks
    for path in pylint_cmk.check_files(repo_path() + "/checks"):
        pylint_cmk.add_file(f, path)

    f.close()

    exit_code = pylint_cmk.run_pylint(pylint_test_dir)
    assert exit_code == 0, "PyLint found an error in checks, inventory " \
                           "or agent bakery plugins"
