#!/usr/bin/python
# encoding: utf-8

import os
import sys
import tempfile
import shutil
import pytest

from testlib import cmk_path, cmc_path, repo_path
#from testlib import cmk_path, cmc_path, cme_path, repo_path
import testlib.pylint_cmk as pylint_cmk


@pytest.fixture(scope="function")
def pylint_test_dir():
    base_path = os.environ.get("WORKDIR")
    if base_path:
        base_path += "/" + os.path.basename(sys.argv[0])
        if not os.path.exists(base_path):
            os.makedirs(base_path)
    else:
        base_path = None

    test_dir = tempfile.mkdtemp(prefix="cmk_pylint", dir=base_path)

    print("Prepare check in %s ..." % test_dir)
    yield test_dir

    #
    # Cleanup code
    #

    print("Cleanup pylint test dir %s ..." % test_dir)
    shutil.rmtree(test_dir)


def test_pylint(pylint_test_dir):
    # Only specify the path to python packages or modules here
    modules_or_packages = [
        # OMD
        "tests-py3/pylint/conftest.py",
        "tests-py3/pylint/test_pylint.py",
#        "omd/packages/omd/omdlib",
#        "livestatus/api/python/livestatus.py",

        # Check_MK base
#        "cmk_base",
        # TODO: Check if this kind of "overlay" really works.
        # TODO: Why do we have e.g. a symlink cmk_base/cee -> enterprise/cmk_base/cee?
#        "enterprise/cmk_base/automations/cee.py",
#        "enterprise/cmk_base/cee",
#        "enterprise/cmk_base/default_config/cee.py",
#        "enterprise/cmk_base/modes/cee.py",
#        "managed/cmk_base/default_config/cme.py",

        # cmk module level
        # TODO: This checks the whole cmk hierarchy, including things like
        # cmk.gui.plugins.cron etc. Do we really want that here?
        # TODO: Funny links there, see above.
#        "cmk",
#        "enterprise/cmk/cee",

        # GUI specific
#        "web/app/index.wsgi",
#        "enterprise/cmk/gui/cee",
#        "managed/cmk/gui/cme",
    ]

    # Add the compiled files for things that are no modules yet
#    file(pylint_test_dir + "/__init__.py", "w")
#    _compile_check_and_inventory_plugins(pylint_test_dir)
#    _compile_bakery_plugins(pylint_test_dir)
#    modules_or_packages += [
#        pylint_test_dir,
#    ]

    # We use our own search logic to find scripts without python extension
#    search_paths = [
#        "omd/packages/omd.bin",
#        "bin",
#        "notifications",
#        "agents/plugins",
#        "agents/special",
#        "active_checks",
#        "enterprise/agents/plugins",
#        "enterprise/bin",
#        "enterprise/misc",
#    ]

#    for path in search_paths:
#        abs_path = cmk_path() + "/" + path
#        for fname in pylint_cmk.get_pylint_files(abs_path, "*"):
#            modules_or_packages.append(path + "/" + fname)

    exit_code = pylint_cmk.run_pylint(cmk_path(), modules_or_packages)
#    exit_code = pylint_cmk.run_pylint(cmk_path(), [])

    assert exit_code == 0, "PyLint found an error"


def _compile_check_and_inventory_plugins(pylint_test_dir):
    with open(pylint_test_dir + "/cmk_checks.py", "w") as f:

        # Fake data structures where checks register (See cmk_base/checks.py)
        f.write("""
# -*- encoding: utf-8 -*-
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
    if default_value is not None:
        node = default_value
    else:
        node = {}

    return node
""")

        # add the modules
        # These pylint warnings are incompatible with our "concatenation technology".
        f.write(
            "# pylint: disable=reimported,ungrouped-imports,wrong-import-order,wrong-import-position,redefined-outer-name\n"
        )
        pylint_cmk.add_file(f, repo_path() + "/cmk_base/check_api.py")
        pylint_cmk.add_file(f, repo_path() + "/cmk_base/inventory_plugins.py")

        # Now add the checks
        for path in pylint_cmk.check_files(repo_path() + "/checks"):
            pylint_cmk.add_file(f, path)

        # Now add the inventory plugins
        for path in pylint_cmk.check_files(repo_path() + "/inventory"):
            pylint_cmk.add_file(f, path)


def _compile_bakery_plugins(pylint_test_dir):
    with open(pylint_test_dir + "/cmk_bakery_plugins.py", "w") as f:

        pylint_cmk.add_file(
            f, os.path.realpath(os.path.join(cmc_path(), "cmk_base/cee/agent_bakery_plugins.py")))
        # This pylint warning is incompatible with our "concatenation technology".
        f.write("# pylint: disable=reimported,wrong-import-order,wrong-import-position\n")

        # Also add bakery plugins
        for path in pylint_cmk.check_files(os.path.join(cmc_path(), "agents/bakery")):
            pylint_cmk.add_file(f, path)
