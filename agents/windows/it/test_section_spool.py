import os
import platform
import pytest
import re
from remote import (actual_output, config, remotetest, remotedir, wait_agent,
                    write_config)


class Globals(object):
    section = 'spool'
    test_message = "Test message"
    outdated = False


@pytest.fixture
def testfile():
    return os.path.basename(__file__)


@pytest.fixture
def testconfig(config):
    config.set("global", "sections", Globals.section)
    config.set("global", "crash_debug", "yes")
    return config


@pytest.fixture
def expected_output():
    return [] if Globals.outdated else [r'%s' % Globals.test_message]


@pytest.fixture(
    params=['yes', 'no'], ids=['outdated', 'not_outdated'], autouse=True)
def manage_spoolfile(request):
    Globals.outdated = request.param == 'yes'
    testfile = '0testfile' if request.param == 'yes' else 'testfile'
    filename = os.path.join(remotedir, Globals.section, testfile)
    if platform.system() == 'Windows':
        spooldir = os.path.join(remotedir, Globals.section)
        try:
            os.mkdir(spooldir)
        except OSError:
            pass  # Directory may already exist.
        with open(filename, 'w') as f:
            f.write('%s' % Globals.test_message)
        # Hack the modification time 2 s back in time
        stat = os.stat(filename)
        times = stat.st_atime, stat.st_mtime - 2
        os.utime(filename, times)

    yield

    if platform.system() == 'Windows':
        os.unlink(filename)


def test_section_spool(request, testconfig, expected_output, actual_output,
                       testfile):
    # request.node.name gives test name
    remotetest(testconfig, expected_output, actual_output, testfile,
               request.node.name)
