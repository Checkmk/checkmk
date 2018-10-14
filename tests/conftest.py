# This file initializes the py.test environment
import os
import pwd
import pytest
import _pytest.monkeypatch
import sys
import glob
import testlib
import tempfile
import shutil
import errno
from collections import OrderedDict

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

test_types = OrderedDict([
    ("unit",        EXECUTE_IN_VENV),
    ("pylint",      EXECUTE_IN_VENV),
    ("docker",      EXECUTE_IN_VENV),
    ("integration", EXECUTE_IN_SITE),
    ("gui_crawl",   EXECUTE_IN_SITE),
    ("packaging",   EXECUTE_IN_VENV),
])

def pytest_addoption(parser):
    """Register the -T option to pytest"""
    parser.addoption("-T", action="store", metavar="TYPE", default=None,
        help="Run tests of the given TYPE. Available types are: %s" %
                                           ", ".join(test_types.keys()))

def pytest_configure(config):
    """Register the type marker to pytest"""
    config.addinivalue_line("markers",
        "type(TYPE): Mark TYPE of test. Available: %s" %
                                    ", ".join(test_types.keys()))


def pytest_collection_modifyitems(items):
    """Mark collected test types based on their location"""
    for item in items:
        type_marker = item.get_marker("type")
        if type_marker and type_marker.args:
            continue # Do not modify manually set marks

        file_path = "%s" % item.reportinfo()[0]
        if "tests/unit" in file_path:
            ty = "unit"
        elif "tests/git" in file_path:
            ty = "unit"
        elif "tests/packaging" in file_path:
            ty = "packaging"
        elif "tests/pylint" in file_path:
            ty = "pylint"
        elif "tests/docker" in file_path:
            ty = "docker"
        elif "tests/integration" in file_path:
            ty = "integration"
        else:
            raise Exception("Test not TYPE marked: %r" % item)

        item.add_marker(pytest.mark.type.with_args(ty))


def pytest_runtest_setup(item):
    """Skip tests of unwanted types"""
    test_type = item.get_marker("type")
    if test_type is None:
        raise Exception("Test is not TYPE marked: %s" % item)

    if not item.config.getoption("-T"):
        raise SystemExit("Please specify type of tests to be executed (py.test -T TYPE)")

    test_type_name = test_type.args[0]
    if test_type_name != item.config.getoption("-T"):
        pytest.skip("Not testing type %r" % test_type_name)


# Some cmk.* code is calling things like cmk. is_raw_edition() at import time
# (e.g. cmk_base/default_config/notify.py) for edition specific variable
# defaults. In integration tests we want to use the exact version of the
# site. For unit tests we assume we are in Enterprise Edition context.
def fake_version_and_paths():
    if is_running_as_site_user():
        return

    monkeypatch = _pytest.monkeypatch.MonkeyPatch()
    tmp_dir = tempfile.mkdtemp(prefix="pytest_cmk_")

    import cmk
    monkeypatch.setattr(cmk, "omd_version", lambda: "%s.cee" % cmk.__version__)

    monkeypatch.setattr("cmk.paths.checks_dir",         "%s/checks" % cmk_path())
    monkeypatch.setattr("cmk.paths.notifications_dir",  "%s/notifications" % cmk_path())
    monkeypatch.setattr("cmk.paths.inventory_dir",      "%s/inventory" % cmk_path())
    monkeypatch.setattr("cmk.paths.check_manpages_dir", "%s/checkman" % cmk_path())
    monkeypatch.setattr("cmk.paths.tmp_dir",            tmp_dir)
    monkeypatch.setattr("cmk.paths.precompiled_checks_dir", os.path.join(tmp_dir, "var/check_mk/precompiled_checks"))
    monkeypatch.setattr("cmk.paths.include_cache_dir",      os.path.join(tmp_dir, "check_mk/check_includes"))


# Cleanup temporary directory created above
@pytest.fixture(scope="session", autouse=True)
def cleanup_cmk():
    yield

    if is_running_as_site_user():
        return

    import cmk.paths

    if "pytest_cmk_" not in cmk.paths.tmp_dir:
        return

    try:
        shutil.rmtree(cmk.paths.tmp_dir)
    except OSError as exc:
        if exc.errno != errno.ENOENT:
            raise  # re-raise exception


def cmk_path():
    return os.path.dirname(os.path.dirname(__file__))


def cmc_path():
    return os.path.realpath(cmk_path() + "/enterprise")


def cme_path():
    return os.path.realpath(cmk_path() + "/managed")


def add_python_paths():
    # make the testlib available to the test modules
    sys.path.insert(0, os.path.dirname(__file__))
    # make the repo directory available (cmk lib)
    sys.path.insert(0, cmk_path())

    # if not running as site user, make the livestatus module available
    if not is_running_as_site_user():
        sys.path.insert(0, os.path.join(cmk_path(), "livestatus/api/python"))


def pytest_cmdline_main(config):
    """There are 2 environments for testing:

    * A real Check_MK site environment (e.g. integration tests)
    * Python virtual environment (e.g. for unit tests)

    Depending on the selected "type" marker the environment is ensured
    or switched here."""
    if not config.getoption("-T"):
        return # missing option is handled later

    context = test_types[config.getoption("-T")]
    if context == EXECUTE_IN_SITE:
        setup_site_and_switch_user()
    else:
        verify_virtualenv()


def verify_virtualenv():
    if not testlib.virtualenv_path():
        raise SystemExit("ERROR: Please load virtual environment first "
                        "(Use \"pipenv shell\" or configure direnv)")


def is_running_as_site_user():
    return pwd.getpwuid(os.getuid()).pw_name == _site_id()

def setup_site_and_switch_user():
    if is_running_as_site_user():
        return # This is executed as site user. Nothing to be done.

    sys.stdout.write("===============================================\n")
    sys.stdout.write("Setting up site '%s'\n" % _site_id())
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

    sys.stdout.write("===============================================\n")
    sys.stdout.write("Cleaning up after testing\n")
    sys.stdout.write("===============================================\n")

    #site.rm_if_not_reusing()
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

    return testlib.Site(site_id=_site_id(), version=site_version(),
                        edition=site_edition(), reuse=reuse_site(), branch=site_branch())


def _site_id():
    site_id = os.environ.get("OMD_SITE")
    if site_id == None:
        site_id = file(testlib.repo_path() + "/.site").read().strip()
        os.putenv("OMD_SITE", site_id)

    return site_id


#
# MAIN
#

add_python_paths()
fake_version_and_paths()

# Session fixtures must be in conftest.py to work properly
@pytest.fixture(scope="session", autouse=True)
def site(request):
    return _get_site_object()
