#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset: 4 -*-
from builtins import range
from builtins import object
try:
    # Use iter version of filter
    from future_builtins import filter
except ImportError:
    # Python 3 compatibility tweak
    pass
import os
import platform
import pytest
from local import (actual_output, make_yaml_config, local_test, run_subprocess, write_config,
                   main_exe)
import sys


class Globals(object):
    param = None


@pytest.fixture
def testfile():
    return os.path.basename(__file__)


@pytest.fixture
def testconfig(make_yaml_config):
    if Globals.param[0] == 'showconfig':
        make_yaml_config['zzz'] = {
            'enabled': 'yes',
            'timeout': 60,
        }
        make_yaml_config['_xxx'] = {
            'enabled': 'yes',
            'timeout': 60,
        }
    return make_yaml_config


@pytest.fixture
def actual_output(request, write_config):
    if platform.system() == 'Windows':
        # Run agent and yield its output.
        try:
            exit_code, _stdout, _stderr = run_subprocess([main_exe] + Globals.param)
            if _stdout:
                sys.stdout.write(_stdout.decode(encoding='cp1252'))
            if _stderr:
                sys.stderr.write(_stderr.decode(encoding='cp1252'))
            expected_code = 2 if Globals.param[0] == 'bad' else 0
            assert expected_code == exit_code
            # Usage is written to stderr, actual cmd output to stdout.
            work_load = _stdout.decode(encoding='cp1252')
            yield work_load.splitlines()
        finally:
            pass
    else:
        # Not on Windows, test run remotely, nothing to be done.
        yield


def output_usage():
    return [
        r'Normal Usage:',
        r'\.?',
    ]


def output_bad_usage():
    r = output_usage()
    r.insert(0, r'Provided Parameter "bad" is not allowed')
    return r


@pytest.fixture
def expected_output(request, testconfig):
    return {
        'version': [r'Check_MK Agent version \d+\.\d+\.\d+([bi]\d+)?(p\d+)?'],
        'showconfig': [
            r'# Environment Variables:',
            r'# MK_LOCALDIR=\.?',
            r'# MK_STATEDIR=\.?',
            r'# MK_PLUGINSDIR=\.?',
            r'# MK_TEMPDIR=\.?',
            r'# MK_LOGDIR=\.?',
            r'# MK_CONFDIR=\.?',
            r'# MK_SPOOLDIR=\.?',
            r'# MK_INSTALLDIR=\.?',
            r'# MK_MSI_PATH=\.?',
            r'# Loaded Config Files:',
            r'# system: \.?',
            r'# bakery: \.?',
            r'# user  : \.?',
            r'\.?',
            r'\.?',
            r'\.?',
            r'\.?',
            r'\.?',
            r'\.?',
            r'\.?',
            r'\.?',
            r'\.?',
            r'\.?',
            r'\.?',
            r'\.?',
            r'\.?',
            r'\.?',
            r'\.?',
            r'\.?',
            r'\.?',
            r'\.?',
            r'\.?',
            r'\.?',
            r'\.?',
            r'\.?',
            r'\.?',
            r'\.?',
            r'\.?',
            r'\.?',
            r'\.?',
            r'\.?',
            r'\.?',
            r'\.?',
            r'\.?',
            r'\.?',
            r'\.?',
            r'\.?',
            r'\.?',
            r'\.?',
        ],
        'help': output_usage(),
        'bad': output_bad_usage()
    }[Globals.param[0]]


@pytest.fixture(
    # Note: param 'adhoc' is tested in all section tests
    #       params 'test' and 'debug' are tested in section check_mk tests
    params=[['version'], ['showconfig'], ['help'], ["bad"]],
    ids=['version', 'showconfig', 'help', 'bad'],
    autouse=True)
def pre_test(request):
    Globals.param = request.param
    yield


@pytest.fixture(autouse=True)
def post_test():
    yield


def test_agent_start_parameters(request, testconfig, expected_output, actual_output, testfile):
    # request.node.name gives test name
    expected_work = expected_output
    if len(expected_work) < len(actual_output):
        missing = len(actual_output) - len(expected_work)
        expected_work.extend([r'\.?' for i in range(missing)])
    local_test(expected_output, actual_output, testfile, request.node.name)
