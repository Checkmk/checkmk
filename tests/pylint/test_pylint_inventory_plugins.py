#!/usr/bin/python
# encoding: utf-8

import os
import sys
from testlib import repo_path
import testlib.pylint_cmk as pylint_cmk

def test_pylint_inventory_plugins(pylint_test_dir):
    f = file(pylint_test_dir + "/cmk-inventory-plugins.py", "w")

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

inv_info   = {} # Inventory plugins
inv_export = {} # Inventory export hooks

def inv_tree_list(path):
    return inv_tree(path, [])

def inv_tree(path, default_value=None):
    if default_value != None:
        node = default_value
    else:
        node = {}

    return node
""")

    # add the modules
    pylint_cmk.add_file(f, repo_path() + "/cmk_base/check_api.py")

    # add the modules
    pylint_cmk.add_file(f, repo_path() + "/cmk_base/inventory_plugins.py")

    # Now add the checks
    for path in pylint_cmk.check_files(repo_path() + "/checks"):
        pylint_cmk.add_file(f, path)

    # Now add the inventory plugins
    for path in pylint_cmk.check_files(repo_path() + "/inventory"):
        pylint_cmk.add_file(f, path)

    f.close()

    exit_code = pylint_cmk.run_pylint(pylint_test_dir)
    assert exit_code == 0, "PyLint found an error in inventory plugins"
