#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset: 4 -*-
import contextlib
from itertools import chain, repeat
import math
import os
import platform
import re
import win32evtlog
from local import (actual_output, assert_subprocess, make_yaml_config, user_dir, local_test,
                   wait_agent, write_config, host)
import sys

import pytest

try:
    import winreg
except ImportError:
    if platform.system() == 'Windows':
        raise


class Globals(object):
    local_statefile = 'eventstate.txt'
    state_pattern = re.compile(r'^(?P<logtype>[^\|]+)\|(?P<record>\d+)$')
    section = 'logwatch'
    alone = True
    statedir = os.path.join(user_dir, 'state')
    statefile = 'eventstate_127_0_0_1.txt'  # local test uses ipv4
    testlog = 'Application'
    testsource = 'Test source'
    testeventtype = 'Warning'
    testdescription = 'Something might happen!'
    tolerance = 10
    testids = range(1, 3)


def generate_logs():
    if platform.system() == 'Windows':
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                            'SYSTEM\\CurrentControlSet\\Services\\Eventlog') as key:
            index = 0
            while True:
                try:
                    yield winreg.EnumKey(key, index)
                    index += 1
                except WindowsError:
                    break


# Windows SSH agent and COM spoil tests by omitting occasional events to
# Security and System logs. Ignore those logs as they are too unstable during a
# test run.
logs = list(l for l in generate_logs() if l != 'Security' and l != 'System')


@contextlib.contextmanager
def eventlog(logtype):
    handle = win32evtlog.OpenEventLog(host, logtype)
    try:
        yield handle
    finally:
        win32evtlog.CloseEventLog(handle)


def get_last_record(logtype):
    with eventlog(logtype) as log_handle:
        oldest = win32evtlog.GetOldestEventLogRecord(log_handle)
        total = win32evtlog.GetNumberOfEventLogRecords(log_handle)
        result = oldest + total - 1
        return result if result >= 0 else 0


def get_log_state(line):
    m = Globals.state_pattern.match(line)
    if m is None:
        return None, None
    return m.group('logtype'), int(m.group('record'))


def logtitle(log):
    return re.escape(r'[[[') + log + re.escape(r']]]')


def create_event(eventid):
    if platform.system() == 'Windows':
        cmd = [
            'eventcreate.exe', '/l', Globals.testlog, '/t', Globals.testeventtype, '/so',
            Globals.testsource, '/id',
            '%d' % eventid, '/d', Globals.testdescription
        ]
        assert_subprocess(cmd)


@pytest.fixture
def create_events():
    for i in Globals.testids:
        create_event(i)


@pytest.fixture
def testfile():
    return os.path.basename(__file__)


def setup_section(config, section, alone):
    config['global']['sections'] = section if alone else [section, "systemtime"]
    return config


@pytest.fixture(params=['alone', 'with_systemtime'])
def testconfig_sections(request, make_yaml_config):
    Globals.alone = request.param == 'alone'
    return setup_section(make_yaml_config, Globals.section, Globals.alone)


@pytest.fixture(params=['yes', 'no'], ids=['vista_api=yes', 'vista_api=no'])
def testconfig(request, testconfig_sections):
    log_files = [{Globals.testlog: 'warn'}, {'Security': 'off'}, {'System': 'off'}, {'*': 'off'}]
    testconfig_sections[Globals.section] = {'vista_api': request.param, 'logfile': log_files}

    return testconfig_sections


@pytest.fixture
def expected_output_no_events():
    if platform.system() != 'Windows':
        return

    expected = [re.escape(r'<<<%s>>>' % Globals.section), re.escape(r'[[[Application]]]')]
    if not Globals.alone:
        expected += [re.escape(r'<<<systemtime>>>'), r'\d+']
    return expected


@pytest.fixture
def expected_output_application_events():
    if platform.system() != 'Windows':
        return

    split_index = logs.index('Application') + 1
    re_str = r'|'.join([logtitle(l) for l in logs[split_index:]] +
                       [r'[CWOu\.] \w{3} \d{2} \d{2}\:\d{2}:\d{2} \d+\.\d+ .+ .+'])
    if not Globals.alone:
        re_str += r'|' + re.escape(r'<<<systemtime>>>') + r'|\d+'
    return chain([re.escape(r'<<<%s>>>' % Globals.section)],
                 [logtitle(l) for l in logs[:split_index]], [
                     r'W \w{3} \d{2} \d{2}\:\d{2}:\d{2} 0\.%d %s %s' %
                     (i, Globals.testsource.replace(' ', '_'), Globals.testdescription)
                     for i in Globals.testids
                 ], repeat(re_str))


def last_records():
    if platform.system() == 'Windows':
        return {logtype: get_last_record(logtype) for logtype in ['Application']}


@pytest.fixture
def no_statefile():
    if platform.system() == 'Windows':
        try:
            os.unlink(os.path.join(Globals.statedir, 'eventstate.txt'))
        except OSError:
            # eventstate.txt may not exist if this is the first test to be run
            pass
    yield


@pytest.fixture(params=[Globals.local_statefile, Globals.statefile])
def with_statefile(request):
    if platform.system() == 'Windows':
        try:
            os.mkdir(Globals.statedir)
        except OSError:
            pass  # Directory may already exist.
        with open(os.path.join(Globals.statedir, request.param), 'w') as statefile:
            eventstate = {logtype: get_last_record(logtype) for logtype in logs}
            for logtype, state in eventstate.items():
                statefile.write('%s|%s\r\n' % (logtype, state))
    yield


@pytest.fixture(autouse=True)
def verify_eventstate():
    yield
    if platform.system() == 'Windows':
        expected_eventstate = last_records()
        with open(os.path.join(Globals.statedir, Globals.statefile)) as statefile:
            actual_eventstate = dict(get_log_state(line) for line in statefile)
        for (expected_log,
             expected_state), (actual_log, actual_state) in zip(sorted(expected_eventstate.items()),
                                                                sorted(actual_eventstate.items())):
            assert expected_log == actual_log
            state_tolerance = 0 if expected_log == Globals.testlog else Globals.tolerance
            assert math.fabs(expected_state - actual_state) <= state_tolerance, (
                "expected state for log '%s' is %d, actual state %d, "
                'state_tolerance %d' %
                (expected_log, expected_state, actual_state, state_tolerance))


# disabled tests
@pytest.mark.usefixtures('no_statefile')
def test_section_eventlog__no_statefile__no_events(request, testconfig, expected_output_no_events,
                                                   actual_output, testfile):
    # request.node.name gives test name
    local_test(expected_output_no_events, actual_output, testfile, request.node.name)


@pytest.mark.usefixtures('with_statefile', 'create_events')
def test_section_eventlog__application_warnings(request, testconfig,
                                                expected_output_application_events, actual_output,
                                                testfile):
    # request.node.name gives test name
    local_test(expected_output_application_events, actual_output, testfile, request.node.name)
