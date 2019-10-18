# This file initializes the py.test environment
# pylint: disable=redefined-outer-name

from __future__ import print_function

import pytest  # type: ignore
# TODO: Can we somehow push some of the registrations below to the subdirectories?
pytest.register_assert_rewrite(
    "testlib",  #
    "unit.checks.checktestlib",  #
    "unit.checks.generictests.run")

import collections
import errno
import os
import shutil
import sys
import tempfile

# Explicitly check for Python 3 (which is understood by mypy)
if sys.version_info[0] >= 3:
    from pathlib import Path  # pylint: disable=import-error
else:
    from pathlib2 import Path  # pylint: disable=import-error

import testlib

#
# Each test is of one of the following types.
#
# The tests are marked using the marker pytest.marker.type("TYPE")
# which is added to the test automatically according to their location.
#
# With each call to py.test one type of tests needs to be selected using
# the "-T TYPE" option. Only these tests will then be executed. Tests of
# the other type will be skipped.
#

EXECUTE_IN_SITE, EXECUTE_IN_VENV = True, False

test_types = collections.OrderedDict([
    ("unit", EXECUTE_IN_VENV),
    ("pylint", EXECUTE_IN_VENV),
    ("docker", EXECUTE_IN_VENV),
    ("integration", EXECUTE_IN_SITE),
    ("gui_crawl", EXECUTE_IN_SITE),
    ("packaging", EXECUTE_IN_VENV),
    ("composition", EXECUTE_IN_VENV),
    ("agent-integration", EXECUTE_IN_VENV),
])


def pytest_addoption(parser):
    """Register the -T option to pytest"""
    options = [name for opt in parser._anonymous.options for name in opt.names()]
    # conftest.py is symlinked from enterprise/tests/conftest.py which makes it being executed
    # twice. Only register this option once.
    if "-T" in options:
        return

    parser.addoption("-T",
                     action="store",
                     metavar="TYPE",
                     default=None,
                     help="Run tests of the given TYPE. Available types are: %s" %
                     ", ".join(test_types.keys()))


def pytest_configure(config):
    """Register the type marker to pytest"""
    config.addinivalue_line(
        "markers", "type(TYPE): Mark TYPE of test. Available: %s" % ", ".join(test_types.keys()))


def pytest_collection_modifyitems(items):
    """Mark collected test types based on their location"""
    for item in items:
        type_marker = item.get_closest_marker("type")
        if type_marker and type_marker.args:
            continue  # Do not modify manually set marks

        file_path = "%s" % item.reportinfo()[0]
        if "tests-py3/unit" in file_path:
            ty = "unit"
        elif "tests-py3/git" in file_path:
            ty = "unit"
        elif "tests-py3/packaging" in file_path:
            ty = "packaging"
        elif "tests-py3/pylint" in file_path:
            ty = "pylint"
        elif "tests-py3/docker" in file_path:
            ty = "docker"
        elif "tests-py3/integration" in file_path:
            ty = "integration"
        elif "tests-py3/composition" in file_path:
            ty = "composition"
        else:
            raise Exception("Test not TYPE marked: %r" % item)

        item.add_marker(pytest.mark.type.with_args(ty))


def pytest_runtest_setup(item):
    """Skip tests of unwanted types"""
    testlib.skip_unwanted_test_types(item)


# Cleanup temporary directory created above
@pytest.fixture(scope="session", autouse=True)
def cleanup_cmk():
    yield

    if testlib.is_running_as_site_user():
        return

    import cmk.utils.paths

    if "pytest_cmk_" not in cmk.utils.paths.tmp_dir:
        return

    try:
        shutil.rmtree(cmk.utils.paths.tmp_dir)
    except OSError as exc:
        if exc.errno != errno.ENOENT:
            raise  # re-raise exception


def pytest_cmdline_main(config):
    """There are 2 environments for testing:

    * A real Check_MK site environment (e.g. integration tests)
    * Python virtual environment (e.g. for unit tests)

    Depending on the selected "type" marker the environment is ensured
    or switched here."""
    if not config.getoption("-T"):
        return  # missing option is handled later

    context = test_types[config.getoption("-T")]
    if context == EXECUTE_IN_SITE:
        setup_site_and_switch_user()
    else:
        verify_virtualenv()


def verify_virtualenv():
    if not testlib.virtualenv_path():
        raise SystemExit("ERROR: Please load virtual environment first "
                         "(Use \"pipenv shell\" or configure direnv)")


def setup_site_and_switch_user():
    if testlib.is_running_as_site_user():
        return  # This is executed as site user. Nothing to be done.

    sys.stdout.write("===============================================\n")
    sys.stdout.write("Setting up site '%s'\n" % testlib.site_id())
    sys.stdout.write("===============================================\n")

    site = _get_site_object()

    cleanup_pattern = os.environ.get("CLEANUP_OLD")
    if cleanup_pattern:
        site.cleanup_old_sites(cleanup_pattern)

    site.cleanup_if_wrong_version()
    site.create()
    #site.open_livestatus_tcp()
    site.start()
    site.prepare_for_tests()

    sys.stdout.write("===============================================\n")
    sys.stdout.write("Switching to site context\n")
    sys.stdout.write("===============================================\n")
    sys.stdout.flush()

    exit_code = site.switch_to_site_user()
    sys.exit(exit_code)


def _get_site_object():
    def site_version():
        return os.environ.get("VERSION", testlib.CMKVersion.DAILY)

    def site_edition():
        return os.environ.get("EDITION", testlib.CMKVersion.CEE)

    def site_branch():
        return os.environ.get("BRANCH", testlib.current_branch_name())

    def reuse_site():
        return os.environ.get("REUSE", "1") == "1"

    return testlib.Site(site_id=testlib.site_id(),
                        version=site_version(),
                        edition=site_edition(),
                        reuse=reuse_site(),
                        branch=site_branch())


#
# MAIN
#

testlib.add_python_paths()
testlib.fake_version_and_paths()


# Session fixtures must be in conftest.py to work properly
@pytest.fixture(scope="session", autouse=True)
def site(request):
    site_obj = _get_site_object()
    yield site_obj
    print("")
    print("Cleanup site processes after test execution...")
    site_obj.stop()
