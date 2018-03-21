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
    # Some special tests are not executed in a site environment, but in
    # virtualenv environment. The integration tests and so on are required to
    # run in our runtime environment (the site). Things like unit tests just
    # need a similar python environment having the required modules.
    verify_virtualenv()
    #if config.getoption('markexpr') in [ "packaging", "git", "html_gentest", "unit" ]:
    #else:
    #    setup_site_and_switch_user()


def verify_virtualenv():
    if not is_running_in_virtualenv():
        raise SystemExit("ERROR: Please load virtual environment first "
                        "(Use \"pipenv shell\" or configure direnv)")


def is_running_in_virtualenv():
    return os.environ.get("VIRTUAL_ENV")


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
        return os.environ.get("BRANCH", "master")

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
