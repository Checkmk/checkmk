# This file initializes the py.test environment
import os
import sys
import glob
import pytest

def cmk_path():
    return os.path.dirname(os.path.dirname(__file__))


def cmc_path():
    return os.path.realpath(cmk_path() + "/../cmc")


def add_python_paths():
    # make python modules needed by Check_MK available. Hope it is sufficient to use
    # the OMD default version here. Otherwise we would need to get cmk-omd git and
    # load the modules from there.
    # Maybe add a check for a default version matching the current branch.
    sys.path = glob.glob("/omd/versions/default/lib/python/*.egg") \
               + [ "/omd/versions/default/lib/python" ] \
               + sys.path

    # make the testlib available to the test modules
    sys.path.insert(0, os.path.dirname(__file__))
    # make the repo directory available (cmk lib)
    sys.path.insert(0, cmk_path())

    print("Import path: %s" % " ".join(sys.path))


# Some pre-testing to ensure the developer uses the correct branches in all involved repos
def ensure_equal_branches():
    cmk_branch = os.popen("cd %s ; git rev-parse --abbrev-ref HEAD" % cmk_path()).read().strip()
    cmc_branch = os.popen("cd %s ; git rev-parse --abbrev-ref HEAD" % cmc_path()).read().strip()

    assert cmk_branch == cmc_branch, "Different branches (%s != %s)\n" % (cmk_branch, cmc_branch)

#
# Make tests classification possible to only execute in specific environments.
# For example only on the CI server.
#

def pytest_addoption(parser):
    parser.addoption("-E", action="store", metavar="NAME",
        help="only run tests matching the environment NAME.")


def pytest_configure(config):
    config.addinivalue_line("markers",
        "env(name): mark test to run only on named environment. Some long running tests "
        "are only meant to be executed on the CI server. Those tests use the "
        "\'@pytest.mark.env(\"ci-server\")' marker. If you want to execute them, add "
        "\"-E ci-server\" to the py.test command.")


def pytest_runtest_setup(item):
    envmarker = item.get_marker("env")
    if envmarker is not None:
        envname = envmarker.args[0]
        if envname != item.config.getoption("-E"):
            pytest.skip("test requires env %r" % envname)

#
# MAIN
#

add_python_paths()
ensure_equal_branches()
