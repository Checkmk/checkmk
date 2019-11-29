#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset: 4 -*-
import os
import platform
import pytest
import re
import subprocess
from remote import (actual_output, agent_exe, config, remotetest, remotedir, wait_agent,
                    write_config)
import sys


class Globals(object):
    output_file = 'agentoutput.txt'
    only_from = None
    host = None


@pytest.fixture
def testfile():
    return os.path.basename(__file__)


@pytest.fixture(params=[None, 'MontyPython'],
                ids=['host_restriction=None', 'host_restriction=MontyPython'])
def testconfig(request, config):
    Globals.host = request.param
    section = 'check_mk'
    config.set('global', 'sections', section)
    config.set('global', 'crash_debug', 'yes')
    if request.param:
        config.set('global', 'host', request.param)
    return config


@pytest.fixture()
def testconfig_only_from(request, testconfig):
    return testconfig


@pytest.fixture(params=[['test'], ['debug'], ['file', Globals.output_file]],
                ids=['test', 'debug', 'file'])
def actual_output_no_tcp(request, write_config):
    if platform.system() == 'Windows':
        # Run agent and yield its output.
        try:
            save_cwd = os.getcwd()
            os.chdir(remotedir)
            p = subprocess.Popen([agent_exe] + request.param,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
            stdout, stderr = p.communicate()
            sys.stdout.write(stdout)
            sys.stderr.write(stderr)
            assert p.returncode == 0
            if request.param[0] == 'file':
                with open(Globals.output_file) as outfile:
                    yield outfile.readlines()
            else:
                yield stdout.splitlines()
        finally:
            try:
                os.unlink(Globals.output_file)
            except OSError:
                pass  # File may not exist
            os.chdir(save_cwd)
    else:
        # Not on Windows, test run remotely, nothing to be done.
        yield


@pytest.fixture
def expected_output():
    drive_letter = r'[A-Z]:'
    return [
        # Note: The first two lines are output with crash_debug = yes in 1.2.8
        # but no longer in 1.4.0:
        # r'<<<logwatch>>>\',
        # r'[[[Check_MK Agent]]]','
        r'<<<check_mk>>>',
        r'Version: \d+\.\d+\.\d+([bi]\d+)?(p\d+)?',
        r'BuildDate: [A-Z][a-z]{2} (\d{2}| \d) \d{4}',
        r'AgentOS: windows',
        r'Hostname: .+',
        r'Architecture: \d{2}bit',
        r'WorkingDirectory: %s%s' % (drive_letter, re.escape(remotedir)),
        r'ConfigFile: %s%s' % (drive_letter, re.escape(os.path.join(remotedir, 'check_mk.ini'))),
        r'LocalConfigFile: %s%s' %
        (drive_letter, re.escape(os.path.join(remotedir, 'check_mk_local.ini'))),
        r'AgentDirectory: %s%s' % (drive_letter, re.escape(remotedir)),
        r'PluginsDirectory: %s%s' % (drive_letter, re.escape(os.path.join(remotedir, 'plugins'))),
        r'StateDirectory: %s%s' % (drive_letter, re.escape(os.path.join(remotedir, 'state'))),
        r'ConfigDirectory: %s%s' % (drive_letter, re.escape(os.path.join(remotedir, 'config'))),
        r'TempDirectory: %s%s' % (drive_letter, re.escape(os.path.join(remotedir, 'temp'))),
        r'LogDirectory: %s%s' % (drive_letter, re.escape(os.path.join(remotedir, 'log'))),
        r'SpoolDirectory: %s%s' % (drive_letter, re.escape(os.path.join(remotedir, 'spool'))),
        r'LocalDirectory: %s%s' % (drive_letter, re.escape(os.path.join(remotedir, 'local'))),
        r'ScriptStatistics: Plugin C:0 E:0 T:0 Local C:0 E:0 T:0',
        # Note: The following three lines are output with crash_debug = yes in
        # 1.2.8 but no longer in 1.4.0:
        # r'ConnectionLog: %s%s' %
        # (drive_letter,
        #  re.escape(os.path.join(remotedir, 'log', 'connection.log'))),
        # r'CrashLog: %s%s' %
        # (drive_letter,
        #  re.escape(os.path.join(remotedir, 'log', 'crash.log'))),
        # r'SuccessLog: %s%s' %
        # (drive_letter,
        #  re.escape(os.path.join(remotedir, 'log', 'success.log'))),
        r'OnlyFrom: '
    ]


def test_section_check_mk(request, testconfig_only_from, expected_output, actual_output, testfile):
    # request.node.name gives test name
    remotetest(expected_output, actual_output, testfile, request.node.name)


def test_section_check_mk__no_tcp(request, testconfig_only_from, expected_output,
                                  actual_output_no_tcp, testfile):
    # request.node.name gives test name
    remotetest(expected_output, actual_output_no_tcp, testfile, request.node.name)
