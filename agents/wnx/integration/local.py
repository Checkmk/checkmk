#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset: 4 -*-
import configparser
import yaml
from contextlib import contextmanager
import os
import platform
import pytest
import re
import time
import subprocess
import sys
import shutil
import telnetlib  # nosec


def get_main_exe_name(base_dir):
    return os.path.join(base_dir, 'check_mk_agent.exe')


def get_main_yaml_name(base_dir):
    return os.path.join(base_dir, 'check_mk.yml')


def get_user_yaml_name(base_dir):
    return os.path.join(base_dir, 'check_mk.user.yml')


def get_main_plugins_name(base_dir):
    return os.path.join(base_dir, 'plugins')


def create_protocol_file(base_dir):
    protocol_file = os.path.join(base_dir, 'upgrade.protocol')
    # block  upgrading
    with open(protocol_file, 'w') as f:
        f.write("Upgraded:\n   time: '2019-05-20 18:21:53.164")


def make_clean_dir(dir_to_create_and_clean):
    try:
        shutil.rmtree(dir_to_create_and_clean)
    except OSError:
        print("Folder doesn't exist")

    if not os.path.exists(dir_to_create_and_clean):
        os.mkdir(dir_to_create_and_clean)

    if not os.path.exists(dir_to_create_and_clean):
        print('Cannot create path %s' % dir_to_create_and_clean)
        sys.exit(13)


def create_and_fill_root_dir(root_work_dir, artefacts_dir):
    make_clean_dir(root_work_dir)

    # filling
    for foo in [get_main_exe_name, get_main_yaml_name]:
        src = foo(artefacts_dir)
        shutil.copy(src, root_work_dir)

    shutil.copytree(get_main_plugins_name(artefacts_dir), get_main_plugins_name(root_work_dir))
    create_protocol_file(root_work_dir)
    # checking
    tgt_agent_exe = get_main_exe_name(root_work_dir)
    if not os.path.exists(tgt_agent_exe):
        print('File %s doesnt exist' % src_agent_exe)
        sys.exit(11)


def make_user_dir(base_dir):
    u_dir = os.path.join(base_dir, 'ProgramData', 'checkmk', 'agent')
    try:
        os.makedirs(u_dir)
    except OSError:
        print('Probably folders exist')
    if not os.path.exists(u_dir):
        print('Directory %s doesnt exist' % u_dir)
        sys.exit(11)
    return u_dir


port = 59999
host = 'localhost'

src_exec_dir = os.path.abspath(os.path.join(os.getcwd(), '..', '..', '..', 'artefacts'))
src_agent_exe = get_main_exe_name(src_exec_dir)
if not os.path.exists(src_agent_exe):
    print('File %s doesnt exist' % src_agent_exe)
    sys.exit(11)

src_main_yaml_config = get_main_yaml_name(src_exec_dir)
if not os.path.exists(src_main_yaml_config):
    print('Directory %s doesnt exist' % src_main_yaml_config)
    sys.exit(11)

# root dir
root_dir = os.path.join(src_exec_dir, 'tests')
create_and_fill_root_dir(root_dir, src_exec_dir)

# user dir
user_dir = make_user_dir(root_dir)

# names
user_yaml_config = get_user_yaml_name(user_dir)
main_exe = get_main_exe_name(root_dir)


@contextmanager
def env_var(key, value):
    os.environ[key] = value
    yield
    del os.environ[key]


# environment variable set
def run_subprocess(cmd):
    with env_var('CMA_TEST_DIR', root_dir):
        sys.stderr.write(' '.join(cmd) + '\n')
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = p.communicate(timeout=10)

    return p.returncode, stdout, stderr


def run_agent(cmd):
    with env_var('CMA_TEST_DIR', root_dir):
        p = subprocess.Popen([cmd, 'exec'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    return p


def assert_subprocess(cmd):
    exit_code, stdout, stderr = run_subprocess(cmd)

    if stdout:
        sys.stdout.write(stdout)
    if stderr:
        sys.stderr.write(stderr)
    assert exit_code == 0, "'%s' failed" % ' '.join(cmd)


@pytest.fixture
def make_yaml_config():
    yml = yaml.safe_load("""
global:
  enabled: true
  logging:
    debug: true
  port: %d
""" % port)
    return yml


@pytest.fixture
def write_config(testconfig):
    if platform.system() == 'Windows':
        with open(user_yaml_config, 'wt') as yaml_file:
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
        p = run_agent(main_exe)

        # Override wait_agent in tests to wait for async processes to start.
        wait_agent()

        for _ in range(0, 5):
            try:
                telnet = telnetlib.Telnet(host, port)  # nosec
                break
            except Exception as error:
                # print('No connect, waiting for agent')
                time.sleep(1)

        if telnet is None:
            raise ConnectionRefusedError("can't connect")

        result = telnet.read_all().decode(encoding='cp1252')

        yield result.splitlines()
    finally:
        if telnet:
            telnet.close()

        if p:
            p.terminate()

        # hammer kill of the process, terminate may be too long
        subprocess.call("taskkill /F /IM check_mk_agent.exe")

        # Possibly wait for async processes to stop.
        wait_agent()


class DuplicateSectionError(Exception):
    """Raised when a section is multiply-created."""
    def __init__(self, section):
        super(DuplicateSectionError, self).__init__(self, 'Section %r already exists' % section)


class NoSectionError(Exception):
    """Raised when no section matches a requested option."""
    def __init__(self, section):
        super(NoSectionError, self).__init__(self, 'No section: %r' % section)


class YamlWriter(object):
    def __init__(self):
        self._doc = None

    def load_document(self, doc):
        self._doc = yaml.safe_load(doc)


def local_test(expected_output, actual_output, testfile, test_name=None, test_class=None):
    comparison_data = zip(expected_output, actual_output)
    for expected, actual in comparison_data:
        if actual == 'WMItimeout':
            pytest.skip('WMI timeout, better luck next time')
        # Uncomment for debug prints:
        # if re.match(expected, actual) is None:
        #    print("ups: %s" % actual)
        #     print( 'DEBUG: actual output\r\n', '\r\n'.join(actual_output))
        #     print('DEBUG: expected output\r\n', '\r\n'.join(expected_output))
        # print("EXPECTED: %s\n ACTUAL  : %s\n" % (expected, actual))

        assert re.match(expected,
                        actual) is not None, "\nExpected '%s'\nActual   '%s'" % (expected, actual)
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
