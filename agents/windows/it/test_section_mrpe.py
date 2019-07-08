#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset: 4 -*-
import os
import platform
import pytest
import re
from remote import (actual_output, assert_subprocess, config, remote_ip, remotedir, remotetest,
                    remoteuser, sshopts, wait_agent, write_config)


class Globals(object):
    section = 'mrpe'
    alone = True
    pluginname = 'check_crit.bat'
    param = 'foobar'
    checkname = 'Dummy'
    mrpedir = 'mrpe'
    includedir = 'test include'  # space in directory name!
    cfgfile = 'test.cfg'
    newline = -1


@pytest.fixture
def testfile():
    return os.path.basename(__file__)


@pytest.fixture(params=['alone', 'with_systemtime'])
def testconfig(request, config):
    Globals.alone = request.param == 'alone'
    if Globals.alone:
        config.set('global', 'sections', Globals.section)
    else:
        config.set('global', 'sections', '%s systemtime' % Globals.section)
    config.set('global', 'crash_debug', 'yes')
    config.add_section(Globals.section)
    if Globals.newline < 0:
        config.set(Globals.section, 'check',
                   '%s %s' % (Globals.checkname, os.path.join(Globals.mrpedir, Globals.pluginname)))
    else:
        config.set(Globals.section, 'include', os.path.join(Globals.includedir, Globals.cfgfile))
    return config


@pytest.fixture
def expected_output():
    drive = r'[A-Z]:%s' % re.escape(os.sep)
    expected = [
        re.escape(r'<<<%s>>>' % Globals.section),
        r'\(%s\) %s 2 CRIT - This check is always critical' %
        (Globals.pluginname, Globals.checkname)
    ]
    if not Globals.alone:
        expected += [re.escape(r'<<<systemtime>>>'), r'\d+']
    return expected


@pytest.fixture(params=[-1, 0, 1, 2],
                ids=[
                    'direct', 'include_without_newline', 'include_with_newline',
                    'include_with_newline_forward_slash'
                ],
                autouse=True)
def manage_plugin(request):
    Globals.newline = request.param
    plugindir = (Globals.mrpedir if Globals.newline < 0 else Globals.includedir)
    source = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          Globals.mrpedir, Globals.pluginname)
    targetdir = os.path.join(remotedir, plugindir)
    targetdir_windows = targetdir.replace('/', '\\')
    if platform.system() != 'Windows':
        cmds = [[
            'ssh', sshopts,
            '%s@%s' % (remoteuser, remote_ip),
            'if not exist "%s" md "%s"' % (targetdir_windows, targetdir_windows)
        ], ['scp', sshopts, source,
            '%s@%s:"%s"' % (remoteuser, remote_ip, targetdir)]]
        for cmd in cmds:
            assert_subprocess(cmd)
    elif Globals.newline >= 0:
        with open(os.path.join(targetdir, Globals.cfgfile), 'wb') as cfg:
            path = os.path.join(targetdir_windows, Globals.pluginname)
            if Globals.newline == 2:
                path = path.replace('\\', '/')
            cfg.write('check = %s "%s"%s' %
                      (Globals.checkname, path, '\n' if Globals.newline > 0 else ""))
    yield
    if platform.system() == 'Windows':
        os.unlink(os.path.join(targetdir, Globals.pluginname))
        if Globals.newline >= 0:
            os.unlink(os.path.join(targetdir, Globals.cfgfile))


def test_section_mrpe(request, testconfig, expected_output, actual_output, testfile):
    # request.node.name gives test name
    remotetest(expected_output, actual_output, testfile, request.node.name)
