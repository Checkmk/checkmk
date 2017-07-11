# This file initializes the py.test environment
import os
import pwd
import pytest
import sys
import glob
import testlib


def cmk_path():
    return os.path.dirname(os.path.dirname(__file__))


def cmc_path():
    return os.path.realpath(cmk_path() + "/enterprise")


def add_python_paths():
    # make the testlib available to the test modules
    sys.path.insert(0, os.path.dirname(__file__))
    # make the repo directory available (cmk lib)
    sys.path.insert(0, cmk_path())


def pytest_cmdline_main(config):
    # Some special tests are not executed in a site environment
    if config.getoption('markexpr') in [ "packaging", "git", "html_gentest" ]:
        return

    setup_site_and_switch_user()


def setup_site_and_switch_user():
    def is_running_as_site_user():
        return pwd.getpwuid(os.getuid()).pw_name == _site_id()

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

    site.rm_if_not_reusing()
    sys.exit(exit_code)


def _get_site_object():
    def site_version():
        return os.environ.get("VERSION", testlib.CMKVersion.DAILY)

    def site_edition():
        return os.environ.get("EDITION", testlib.CMKVersion.CEE)

    def site_branch():
        return os.environ.get("BRANCH", "1.4.0")

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

# Session fixtures must be in conftest.py to work properly
@pytest.fixture(scope="session", autouse=True)
def site(request):
    return _get_site_object()
