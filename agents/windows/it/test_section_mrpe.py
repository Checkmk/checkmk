import os
import platform
import pytest
import re
from remote import (actual_output, assert_subprocess, config, remote_ip,
                    remotedir, remotetest, remoteuser, sshopts, wait_agent,
                    write_config)


class Globals(object):
    section = 'mrpe'
    pluginname = 'check_crit.bat'
    checkname = 'Dummy'
    mrpedir = 'mrpe'
    includedir = 'testinclude'
    cfgfile = 'test.cfg'
    newline = None


@pytest.fixture
def testfile():
    return os.path.basename(__file__)


@pytest.fixture
def testconfig(config):
    config.set("global", "sections", Globals.section)
    config.set("global", "crash_debug", "yes")
    config.add_section(Globals.section)
    if Globals.newline is None:
        config.set(Globals.section, 'check', '%s %s' %
                   (Globals.checkname,
                    os.path.join(Globals.mrpedir, Globals.pluginname)))
    else:
        config.set(Globals.section, "include",
                   os.path.join(Globals.includedir, Globals.cfgfile))
    return config


@pytest.fixture
def expected_output():
    drive = r'[A-Z]:%s' % re.escape(os.sep)
    return [
        re.escape(r'<<<%s>>>' % Globals.section),
        r'\(%s\) %s 2 CRIT - This check is always critical' %
        (Globals.pluginname, Globals.checkname)
    ]


@pytest.fixture(
    params=[None, False, True],
    ids=['direct', 'include_without_newline', 'include_with_newline'],
    autouse=True)
def manage_plugin(request):
    Globals.newline = request.param
    plugindir = (Globals.mrpedir
                 if Globals.newline is None else Globals.includedir)
    source = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        Globals.mrpedir, Globals.pluginname)
    targetdir = os.path.join(remotedir, plugindir)
    targetdir_windows = targetdir.replace('/', '\\')
    if platform.system() != 'Windows':
        cmds = [[
            'ssh', sshopts,
            '%s@%s' % (remoteuser, remote_ip),
            'if not exist %s md %s' % (targetdir_windows, targetdir_windows)
        ], [
            'scp', sshopts, source,
            '%s@%s:%s' % (remoteuser, remote_ip, targetdir)
        ]]
        for cmd in cmds:
            assert_subprocess(cmd)
    elif Globals.newline is not None:
        with open(os.path.join(targetdir, Globals.cfgfile), 'wb') as cfg:
            cfg.write("check = %s %s%s" %
                      (Globals.checkname,
                       os.path.join(targetdir_windows, Globals.pluginname),
                       "\n" if Globals.newline else ""))
    yield
    if platform.system() == 'Windows':
        os.unlink(os.path.join(targetdir, Globals.pluginname))
        if Globals.newline is not None:
            os.unlink(os.path.join(targetdir, Globals.cfgfile))


def test_section_mrpe(request, testconfig, expected_output, actual_output,
                      testfile):
    # request.node.name gives test name
    remotetest(testconfig, expected_output, actual_output, testfile,
               request.node.name)
