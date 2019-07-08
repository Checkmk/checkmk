#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset: 4 -*-
import ConfigParser
import contextlib
import os
import platform
import pytest
import re
import subprocess
import sys
import telnetlib  # nosec

# To use another host for running the tests, replace this IP address.
remote_ip = '10.1.2.30'
# To use another user account for running the tests, replace this username.
remoteuser = 'NetworkAdministrator'
remotedir = os.path.join(os.sep, 'Users', remoteuser, 'Tests')
sshopts = '-o StrictHostKeyChecking=no'
host = 'localhost'
port = 9999
agent_exe = os.path.join(remotedir, 'check_mk_agent-64.exe')
ini_filename = os.path.join(remotedir, 'check_mk.ini')


def run_subprocess(cmd):
    sys.stderr.write(' '.join(cmd) + '\n')
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = p.communicate()
    return (p.returncode, stdout, stderr)


def assert_subprocess(cmd):
    exit_code, stdout, stderr = run_subprocess(cmd)
    if stdout:
        sys.stdout.write(stdout)
    if stderr:
        sys.stderr.write(stderr)
    assert exit_code == 0, "'%s' failed" % ' '.join(cmd)


@pytest.fixture
def config():
    ini = IniWriter()
    ini.add_section('global')
    ini.set('global', 'port', port)
    return ini


@pytest.fixture
def write_config(testconfig):
    if platform.system() == 'Windows':
        with open(ini_filename, 'wb') as inifile:
            testconfig.write(inifile)
    yield


# Override this in test file(s) to insert a wait before contacting the agent.
@pytest.fixture
def wait_agent():
    def inner():
        pass

    return inner


@pytest.fixture
def actual_output(write_config, wait_agent):
    if platform.system() == 'Windows':
        # Run agent and yield telnet output.
        telnet, p = None, None
        try:
            save_cwd = os.getcwd()
            os.chdir(remotedir)
            p = subprocess.Popen([agent_exe, 'adhoc'])

            # Override wait_agent in tests to wait for async processes to start.
            wait_agent()

            telnet = telnetlib.Telnet(host, port)  # nosec
            yield telnet.read_all().splitlines()
        finally:
            if telnet:
                telnet.close()

            if p:
                p.terminate()

            # Possibly wait for async processes to stop.
            wait_agent()

            os.chdir(save_cwd)
    else:
        # Not on Windows, test run remotely, nothing to be done.
        yield


class DuplicateSectionError(Exception):
    """Raised when a section is multiply-created."""

    def __init__(self, section):
        super(DuplicateSectionError, self).__init__(self, 'Section %r already exists' % section)


class NoSectionError(Exception):
    """Raised when no section matches a requested option."""

    def __init__(self, section):
        super(NoSectionError, self).__init__(self, 'No section: %r' % (section))


class IniWriter(ConfigParser.RawConfigParser):
    """Writer for Windows ini files. Simplified version of RawConfigParser but
    supports multiple values for a single key."""

    def add_section(self, section):
        """Create a new section in the configuration.

        Raise DuplicateSectionError if a section by the specified name
        already exists. Raise ValueError if name is DEFAULT or any of it's
        case-insensitive variants.
        """
        if section.lower() == 'default':
            raise ValueError('Invalid section name: %s' % section)

        if section in self._sections:
            raise DuplicateSectionError(section)
        self._sections[section] = self._dict()

    def set(self, section, option, value=None):
        """Set an option."""
        try:
            sectdict = self._sections[section]
        except KeyError:
            raise NoSectionError(section)
        if option in sectdict:
            sectdict[option].append(value)
        else:
            sectdict[option] = [value]

    def write(self, filehandle):
        for section, options in self._sections.iteritems():
            filehandle.write('[%s]\r\n' % section)
            for key, values in options.iteritems():
                for value in values:
                    filehandle.write('    %s = %s\r\n' % (key, value))


def remotetest(expected_output, actual_output, testfile, testname=None, testclass=None):
    # Not on Windows: call given test remotely over ssh
    if platform.system() != 'Windows':
        cmd = [
            'ssh', sshopts,
            '%s@%s' % (remoteuser, remote_ip),
            'py.test %s%s%s' % (os.path.join(remotedir, testfile),
                                ('::%s' % testclass) if testclass else '',
                                ('::%s' % testname) if testname else '')
        ]
        assert_subprocess(cmd)
    # On Windows: verify output against expected
    else:
        comparison_data = zip(expected_output, actual_output)
        for expected, actual in comparison_data:
            if actual == 'WMItimeout':
                pytest.skip('WMI timeout, better luck next time')
            # Uncomment for debug prints:
            # if re.match(expected, actual) is None:
            #     print 'DEBUG: actual output\r\n', '\r\n'.join(actual_output)
            #     print 'DEBUG: expected output\r\n', '\r\n'.join(expected_output)
            assert re.match(expected, actual) is not None, ("expected '%s', actual '%s'" %
                                                            (expected, actual))
        try:
            assert len(actual_output) >= len(expected_output), (
                'actual output is shorter than expected:\n'
                'expected output:\n%s\nactual output:\n%s' %
                ('\n'.join(expected_output), '\n'.join(actual_output)))
            assert len(actual_output) <= len(expected_output), (
                'actual output is longer than expected:\n'
                'expected output:\n%s\nactual output:\n%s' %
                ('\n'.join(expected_output), '\n'.join(actual_output)))
        except TypeError:
            # expected_output may be an iterator without len
            assert len(actual_output) > 0, 'Actual output was empty'
