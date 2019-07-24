#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset: 4 -*-
from itertools import chain, repeat
import os
import platform
import pytest
import re
import sys
import time
from local import (actual_output, assert_subprocess, make_ini_config, src_exec_dir, local_test,
                   write_config)


class Globals(object):
    alone = True


@pytest.fixture
def testfile():
    return os.path.basename(__file__)


@pytest.fixture(params=[('ohm', True), ('openhardwaremonitor', True), ('ohm', False),
                        ('openhardwaremonitor', False)],
                ids=[
                    'sections=ohm', 'sections=openhardwaremonitor', 'sections=ohm_systemtime',
                    'sections=openhardwaremonitor_systemtime'
                ])
def testconfig(request, make_ini_config):
    Globals.alone = request.param[1]
    if Globals.alone:
        make_ini_config.set('global', 'sections', request.param[0])
    else:
        make_ini_config.set('global', 'sections', '%s systemtime' % request.param[0])
    make_ini_config.set('global', 'crash_debug', 'yes')
    return make_ini_config


@pytest.fixture
def wait_agent():
    def inner():
        # Wait a little so that OpenHardwareMonitorCLI.exe starts properly.
        time.sleep(5)

    return inner


@pytest.fixture
def expected_output():
    re_str = (r'^\d+,[^,]+,(\/\w+)+,(Power|Clock|Load|Data|Temperature),' r'\d+\.\d{6}')
    if not Globals.alone:
        re_str += r'|' + re.escape(r'<<<systemtime>>>') + r'|\d+'
    re_str += r'$'
    return chain(
        [re.escape(r'<<<openhardwaremonitor:sep(44)>>>'), r'Index,Name,Parent,SensorType,Value'],
        repeat(re_str))


@pytest.fixture(autouse=True)
def manage_ohm_binaries():
    if platform.system() != 'Windows':
        binaries = ['OpenHardwareMonitorCLI.exe', 'OpenHardwareMonitorLib.dll']

        sourcedir = os.path.normpath(
            os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'omd',
                         'packages', 'openhardwaremonitor'))

        targetdir = os.path.join(src_exec_dir, 'bin')
        targetdir_win = targetdir.replace('/', '\\')

        cmds = [[
            'ssh', sshopts,
            '%s@%s' % (remoteuser, remote_ip),
            'if not exist %s md %s' % (targetdir_win, targetdir_win)
        ], ['scp', sshopts] + [os.path.join(sourcedir, b) for b in binaries] +
                ['%s@%s:%s' % (remoteuser, remote_ip, targetdir)]]
        for cmd in cmds:
            assert_subprocess(cmd)
    yield
    if platform.system() != 'Windows':
        cmd = [
            'ssh', sshopts,
            '%s@%s' % (remoteuser, remote_ip),
            ' && '.join(['del %s' % '\\'.join([targetdir_win, b]) for b in binaries])
        ]
        assert_subprocess(cmd)


def test_section_openhardwaremonitor(request, testconfig, expected_output, actual_output, testfile):
    # request.node.name gives test name
    local_test(expected_output, actual_output, testfile, request.node.name)
