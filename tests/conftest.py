# This file initializes the py.test environment
# pylint: disable=redefined-outer-name

import pytest
# TODO: Can we somehow push some of the registrations below to the subdirectories?
pytest.register_assert_rewrite(
    "testlib",  #
    "unit.checks.checktestlib",  #
    "unit.checks.generictests.run")

import _pytest.monkeypatch
import re
import collections
import errno
import os
import pwd
import shutil
import sys
import tempfile
from pathlib2 import Path
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
    ("agent-integration", EXECUTE_IN_VENV),
    ("integration", EXECUTE_IN_SITE),
    ("gui_crawl", EXECUTE_IN_SITE),
    ("packaging", EXECUTE_IN_VENV),
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
        elif "tests/agent-integration" in file_path:
            ty = "agent-integration"
        elif "tests/integration" in file_path:
            ty = "integration"
        else:
            raise Exception("Test not TYPE marked: %r" % item)

        item.add_marker(pytest.mark.type.with_args(ty))


def pytest_runtest_setup(item):
    """Skip tests of unwanted types"""
    testlib.skip_unwanted_test_types(item)


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

    monkeypatch.setattr("cmk.utils.paths.checks_dir", "%s/checks" % cmk_path())
    monkeypatch.setattr("cmk.utils.paths.notifications_dir", "%s/notifications" % cmk_path())
    monkeypatch.setattr("cmk.utils.paths.inventory_dir", "%s/inventory" % cmk_path())
    monkeypatch.setattr("cmk.utils.paths.check_manpages_dir", "%s/checkman" % cmk_path())
    monkeypatch.setattr("cmk.utils.paths.web_dir", "%s/web" % cmk_path())
    monkeypatch.setattr("cmk.utils.paths.omd_root", tmp_dir)
    monkeypatch.setattr("cmk.utils.paths.tmp_dir", os.path.join(tmp_dir, "tmp/check_mk"))
    monkeypatch.setattr("cmk.utils.paths.var_dir", os.path.join(tmp_dir, "var/check_mk"))
    monkeypatch.setattr("cmk.utils.paths.precompiled_checks_dir",
                        os.path.join(tmp_dir, "var/check_mk/precompiled_checks"))
    monkeypatch.setattr("cmk.utils.paths.include_cache_dir",
                        os.path.join(tmp_dir, "tmp/check_mk/check_includes"))
    monkeypatch.setattr("cmk.utils.paths.check_mk_config_dir",
                        os.path.join(tmp_dir, "etc/check_mk/conf.d"))
    monkeypatch.setattr("cmk.utils.paths.main_config_file",
                        os.path.join(tmp_dir, "etc/check_mk/main.mk"))
    monkeypatch.setattr("cmk.utils.paths.default_config_dir", os.path.join(tmp_dir, "etc/check_mk"))
    monkeypatch.setattr("cmk.utils.paths.piggyback_dir", Path(tmp_dir) / "var/check_mk/piggyback")
    monkeypatch.setattr("cmk.utils.paths.piggyback_source_dir",
                        Path(tmp_dir) / "var/check_mk/piggyback_sources")
    monkeypatch.setattr("cmk.utils.paths.htpasswd_file", os.path.join(tmp_dir, "etc/htpasswd"))


# Cleanup temporary directory created above
@pytest.fixture(scope="session", autouse=True)
def cleanup_cmk():
    yield

    if is_running_as_site_user():
        return

    import cmk.utils.paths

    if "pytest_cmk_" not in cmk.utils.paths.tmp_dir:
        return

    try:
        shutil.rmtree(cmk.utils.paths.tmp_dir)
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
        sys.path.insert(0, os.path.join(cmk_path(), "omd/packages/omd"))


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


def is_running_as_site_user():
    return pwd.getpwuid(os.getuid()).pw_name == _site_id()


def setup_site_and_switch_user():
    if is_running_as_site_user():
        return  # This is executed as site user. Nothing to be done.

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
    sys.exit(exit_code)


def _get_site_object():
    def site_version():
        return os.environ.get("VERSION", testlib.CMKVersion.DAILY)

    def site_edition():
        return os.environ.get("EDITION", testlib.CMKVersion.CEE)

    def site_branch():
        return os.environ.get("BRANCH") or testlib.current_branch_name()

    def reuse_site():
        return os.environ.get("REUSE", "1") == "1"

    return testlib.Site(site_id=_site_id(),
                        version=site_version(),
                        edition=site_edition(),
                        reuse=reuse_site(),
                        branch=site_branch())


def _site_id():
    site_id = os.environ.get("OMD_SITE")
    if site_id is not None:
        return site_id

    branch_name = os.environ.get("BRANCH") or testlib.current_branch_name()
    # Split by / and get last element, remove unwanted chars
    branch_part = re.sub("[^a-zA-Z0-9_]", "", branch_name.split("/")[-1])
    site_id = "int_%s" % branch_part

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
    site_obj = _get_site_object()
    yield site_obj
    print ""
    print "Cleanup site processes after test execution..."
    site_obj.stop()
