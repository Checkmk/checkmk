# encoding: utf-8
# pylint: disable=redefined-outer-name

from __future__ import print_function
import os
import sys
import tempfile
import shutil
import pytest  # type: ignore

from testlib import repo_path, is_enterprise_repo
import testlib.pylint_cmk as pylint_cmk
import cmk.utils.cmk_subprocess as subprocess


@pytest.fixture(scope="function")
def pylint_test_dir():
    base_path = os.environ.get("WORKDIR")
    if base_path:
        base_path += "/" + os.path.basename(sys.argv[0])
        if not os.path.exists(base_path):
            os.makedirs(base_path)
    else:
        base_path = None

    test_dir = tempfile.mkdtemp(prefix="cmk_pylint_", dir=base_path)

    print("Prepare check in %s ..." % test_dir)
    yield test_dir

    #
    # Cleanup code
    #

    print("Cleanup pylint test dir %s ..." % test_dir)
    shutil.rmtree(test_dir)


def test_pylint(pylint_test_dir):
    exit_code = pylint_cmk.run_pylint(repo_path(), _get_files_to_check(pylint_test_dir))
    assert exit_code == 0, "PyLint found an error"


def _get_files_to_check(pylint_test_dir):
    p = subprocess.Popen(
        ["%s/scripts/find-python-files" % repo_path(),
         str(sys.version_info[0])],
        stdout=subprocess.PIPE,
        encoding="utf-8",
        shell=False,
        close_fds=True,
    )

    stdout = p.communicate()[0]

    files = []
    for fname in stdout.splitlines():
        # Thin out these excludes some day...
        rel_path = fname[len(repo_path()) + 1:]

        # Can currently not be checked alone. Are compiled together below
        if rel_path.startswith("checks/") or \
           rel_path.startswith("inventory/") or \
           rel_path.startswith("agents/bakery/") or \
           rel_path.startswith("enterprise/agents/bakery/"):
            continue

        # TODO: We should also test them...
        if rel_path == "werk" \
            or rel_path.startswith("tests/") \
            or rel_path.startswith("scripts/") \
            or rel_path.startswith("agents/wnx/integration/"):
            continue

        # TODO: disable random, not that important stuff
        if rel_path.startswith("agents/windows/it/") \
            or rel_path.startswith("agents/windows/msibuild/") \
            or rel_path.startswith("doc/") \
            or rel_path.startswith("livestatus/api/python/example") \
            or rel_path.startswith("livestatus/api/python/make_"):
            continue

        files.append(fname)

    # Add the compiled files for things that are no modules yet
    open(pylint_test_dir + "/__init__.py", "w")
    _compile_check_and_inventory_plugins(pylint_test_dir)

    if is_enterprise_repo():
        _compile_bakery_plugins(pylint_test_dir)

    # Not checking compiled check, inventory, bakery plugins with Python 3
    if sys.version_info[0] == 2:
        files += [
            pylint_test_dir,
        ]

    return files


def _compile_check_and_inventory_plugins(pylint_test_dir):
    with open(pylint_test_dir + "/cmk_checks.py", "w") as f:

        # Fake data structures where checks register (See cmk/base/checks.py)
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
        pylint_cmk.add_file(f, repo_path() + "/cmk/base/check_api.py")
        pylint_cmk.add_file(f, repo_path() + "/cmk/base/inventory_plugins.py")

        # Now add the checks
        for path in pylint_cmk.check_files(repo_path() + "/checks"):
            pylint_cmk.add_file(f, path)

        # Now add the inventory plugins
        for path in pylint_cmk.check_files(repo_path() + "/inventory"):
            pylint_cmk.add_file(f, path)


def _compile_bakery_plugins(pylint_test_dir):
    with open(pylint_test_dir + "/cmk_bakery_plugins.py", "w") as f:

        pylint_cmk.add_file(
            f,
            os.path.realpath(
                os.path.join(repo_path(), "enterprise/cmk/base/cee/agent_bakery_plugins.py")))
        # This pylint warning is incompatible with our "concatenation technology".
        f.write("# pylint: disable=reimported,wrong-import-order,wrong-import-position\n")

        # Also add bakery plugins
        for path in pylint_cmk.check_files(os.path.join(repo_path(), "enterprise/agents/bakery")):
            pylint_cmk.add_file(f, path)
