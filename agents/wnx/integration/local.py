#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset: 4 -*-
import configparser
import yaml
from contextlib import contextmanager
import os
import platform
import pytest
import re
import subprocess
import sys
import shutil
import telnetlib  # nosec

port = 59999
host = 'localhost'

src_exec_dir = os.path.abspath(os.path.join(os.getcwd(), '..', '..', '..', 'artefacts'))
src_agent_exe = os.path.join(src_exec_dir, 'check_mk_agent.exe')
if not os.path.exists(src_agent_exe):
    print('File %s doesnt exist' % src_agent_exe)
    sys.exit(11)

src_main_yaml_config = os.path.join(src_exec_dir, 'check_mk.yml')
if not os.path.exists(src_main_yaml_config):
    print('Directory %s doesnt exist' % src_main_yaml_config)
    sys.exit(11)

tgt_exec_dir = os.path.join(src_exec_dir, 'tests')
shutil.rmtree(tgt_exec_dir)
shutil.copy(src_agent_exe, tgt_exec_dir)
shutil.copy(src_main_yaml_config, tgt_exec_dir)
protocol_file = os.path.join(tgt_exec_dir, "upgrade.protocol")
# block  upgrading
with open(protocol_file, 'w') as f:
    f.write("Upgraded:\n   time: '2019-05-20 18:21:53.164")

tgt_agent_exe = os.path.join(tgt_exec_dir, 'check_mk_agent.exe')
if not os.path.exists(tgt_agent_exe):
    print('File %s doesnt exist' % src_agent_exe)
    sys.exit(11)

user_dir = os.path.join(src_exec_dir, 'ProgramData', 'CheckMk', 'Agent')
yaml_config = os.path.join(user_dir, 'check_mk.yml')
if not os.path.exists(user_dir):
    print('Directory %s doesnt exist' % user_dir)
    sys.exit(11)


@contextmanager
def env_var(key, value):
    os.environ[key] = value
    yield
    del os.environ[key]


# environment variaable set
def run_subprocess(cmd):
    with env_var('CMA_TEST_DIR', tgt_exec_dir):
        sys.stderr.write(' '.join(cmd) + '\n')
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = p.communicate()

    return p.returncode, stdout, stderr


def assert_subprocess(cmd):
    exit_code, stdout, stderr = run_subprocess(cmd)

    if stdout:
        sys.stdout.write(stdout)
    if stderr:
        sys.stderr.write(stderr)
    assert exit_code == 0, "'%s' failed" % ' '.join(cmd)


def make_ini_config():
    ini = IniWriter()
    ini.add_section('global')
    ini.set('global', 'port', port)
    return ini


@pytest.fixture
def make_yaml_config():
    yml = yaml.load("""
global:
  enabled: true
  port: %d        
""" % port)
    return yml


@pytest.fixture
def write_config(testconfig):
    if platform.system() == 'Windows':
        with open(yaml_config, 'wt') as yaml_file:
            a = yaml.dump(testconfig)
            yaml_file.write(a)
    yield


# Override this in test file(s) to insert a wait before contacting the agent.
@pytest.fixture
def wait_agent():
    def inner():
        pass

    return inner


@pytest.fixture
def actual_output(write_config, wait_agent):
    if platform.system() != 'Windows':
        sys.exit(1)

    # Run agent and yield telnet output.
    telnet, p = None, None
    try:
        save_cwd = os.getcwd()
        os.chdir(src_exec_dir)
        p = subprocess.Popen([src_agent_exe, '-exec'])

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


class DuplicateSectionError(Exception):
    """Raised when a section is multiply-created."""

    def __init__(self, section):
        super(DuplicateSectionError, self).__init__(self, 'Section %r already exists' % section)


class NoSectionError(Exception):
    """Raised when no section matches a requested option."""

    def __init__(self, section):
        super(NoSectionError, self).__init__(self, 'No section: %r' % section)


class YamlWriter:
    def load_document(self, doc):
        self._doc = yaml.load(doc)


class IniWriter(configparser.RawConfigParser):
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


def localtest(expected_output, actual_output, testfile, testname=None, testclass=None):
    # Not on Windows: call given test remotely over ssh
    if platform.system() != 'Windows':
        cmd = [
            'py.test',
            '%s%s%s' % (os.path.join(src_exec_dir, testfile),
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
            assert re.match(expected,
                            actual) is not None, ("expected '%s', actual '%s'" % (expected, actual))
        try:
            assert len(actual_output) >= len(expected_output), (
                'actual output is shorter than expected:\n'
                'expected output:\n%s\nactual output:\n%s' % ('\n'.join(expected_output),
                                                              '\n'.join(actual_output)))
            assert len(actual_output) <= len(expected_output), (
                'actual output is longer than expected:\n'
                'expected output:\n%s\nactual output:\n%s' % ('\n'.join(expected_output),
                                                              '\n'.join(actual_output)))
        except TypeError:
            # expected_output may be an iterator without len
            assert len(actual_output) > 0, 'Actual output was empty'
