import os
import platform
import pytest
import re
from remote import (actual_output, assert_subprocess, config, remote_ip,
                    remotedir, remotetest, remoteuser, sshopts, wait_agent,
                    write_config)


section = 'mrpe'
pluginname = 'check_crit.bat'
checkname = 'Dummy'
mrpedir = 'mrpe'


@pytest.fixture
def testfile():
    return os.path.basename(__file__)


@pytest.fixture
def testconfig(config):
    config.set("global", "sections", section)
    config.set("global", "crash_debug", "yes")
    config.add_section(section)
    config.set(section, 'check', '%s %s' % (checkname,
                                            os.path.join(mrpedir, pluginname)))
    return config


@pytest.fixture
def expected_output():
    drive = r'[A-Z]:%s' % re.escape(os.sep)
    return [
        re.escape(r'<<<%s>>>' % section),
        r'\(%s\) %s 2 CRIT - This check is always critical' % (pluginname,
                                                               checkname)
    ]


@pytest.fixture(autouse=True)
def manage_plugin():
    source = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), mrpedir,
        pluginname)
    targetdir = os.path.join(remotedir, mrpedir)
    targetdir_windows = targetdir.replace('/', '\\')
    if platform.system() != 'Windows':
        cmds = [[
            'ssh',
            sshopts,
            '%s@%s' % (remoteuser, remote_ip),
            'if not exist %s md %s' % (targetdir_windows, targetdir_windows)
        ], ['scp', sshopts, source,
            '%s@%s:%s' % (remoteuser, remote_ip, targetdir)]]
        for cmd in cmds:
            assert_subprocess(cmd)
    yield
    if platform.system() == 'Windows':
        os.unlink(os.path.join(targetdir, pluginname))


def test_section_mrpe(testconfig, expected_output, actual_output, testfile):
    remotetest(testconfig, expected_output, actual_output, testfile)
