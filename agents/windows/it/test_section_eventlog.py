import contextlib
from itertools import chain, repeat
import os
import platform
import re
from remote import (actual_output, assert_subprocess, config, host, remote_ip,
                    remotedir, remotetest, remoteuser, wait_agent,
                    write_config)
import sys

import pytest

try:
    import win32evtlog
    import _winreg
except ImportError:
    if platform.system() == 'Windows':
        raise

state_pattern = re.compile(r'^(?P<logtype>[^\|]+)\|(?P<record>\d+)$')
section = 'logwatch'
testlog = 'Application'
testsource = 'Test source'
testeventtype = 'Warning'
testdescription = 'Something might happen!'
testids = range(1, 3)


def generate_logs():
    if platform.system() == 'Windows':
        with _winreg.OpenKey(
                _winreg.HKEY_LOCAL_MACHINE,
                "SYSTEM\\CurrentControlSet\\Services\\Eventlog") as key:
            index = 0
            while True:
                try:
                    yield _winreg.EnumKey(key, index)
                    index += 1
                except WindowsError:
                    break


logs = list(generate_logs())


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
    m = state_pattern.match(line)
    if m is None:
        return None, None
    return m.group('logtype'), int(m.group('record'))


def logtitle(log):
    return re.escape(r'[[[') + log + re.escape(r']]]')


def create_event(eventid):
    if platform.system() == 'Windows':
        cmd = [
            'eventcreate.exe', '/l', testlog, '/t', testeventtype, '/so',
            testsource, '/id',
            '%d' % eventid, '/d', testdescription
        ]
        assert_subprocess(cmd)


@pytest.fixture
def create_events():
    for i in testids:
        create_event(i)


@pytest.fixture
def testfile():
    return os.path.basename(__file__)


@pytest.fixture(params=['yes', 'no'], ids=['vista_api=yes', 'vista_api=no'])
def testconfig(request, config):
    config.set("global", "sections", section)
    config.set("global", "crash_debug", "yes")
    config.add_section(section)
    config.set(section, "vista_api", request.param)
    config.set(section, "logfile %s" % testlog, "warn")

    return config


@pytest.fixture
def expected_output_no_events():
    if platform.system() == 'Windows':
        return [re.escape(r'<<<%s>>>' % section)] + [logtitle(l) for l in logs]


@pytest.fixture
def expected_output_application_events():
    if platform.system() == 'Windows':
        split_index = logs.index('Application') + 1
        return chain(
            [re.escape(r'<<<%s>>>' % section)],
            [logtitle(l) for l in logs[:split_index]], [
                r'W \w{3} \d{2} \d{2}\:\d{2}:\d{2} 0\.%d %s %s' %
                (i, testsource.replace(' ', '_'), testdescription)
                for i in testids
            ],
            repeat(r'|'.join(
                [logtitle(l) for l in logs[split_index:]] +
                [r'[CWOu\.] \w{3} \d{2} \d{2}\:\d{2}:\d{2} \d+\.\d+ .+ .+'])))


def last_records():
    if platform.system() == 'Windows':
        return {logtype: get_last_record(logtype) for logtype in logs}


@pytest.fixture
def no_statefile():
    if platform.system() == 'Windows':
        try:
            os.unlink(os.path.join(remotedir, 'state', 'eventstate.txt'))
        except OSError:
            # eventstate.txt may not exist if this is the first test to be run
            pass
    yield


@pytest.fixture
def with_statefile():
    if platform.system() == 'Windows':
        statedir = os.path.join(remotedir, 'state')
        try:
            os.mkdir(statedir)
        except OSError:
            pass  # Directory may already exist.
        with open(os.path.join(statedir, 'eventstate.txt'), 'w') as statefile:
            eventstate = {
                logtype: get_last_record(logtype)
                for logtype in logs
            }
            for logtype, state in eventstate.items():
                statefile.write("%s|%s\r\n" % (logtype, state))
    yield


@pytest.fixture(autouse=True)
def verify_eventstate():
    yield
    if platform.system() == 'Windows':
        expected_eventstate = last_records()
        with open(os.path.join(remotedir, 'state',
                               'eventstate.txt')) as statefile:
            actual_eventstate = dict(get_log_state(line) for line in statefile)
        for (expected_log, expected_state), (actual_log, actual_state) in zip(
                sorted(expected_eventstate.items()),
                sorted(actual_eventstate.items())):
            assert expected_log == actual_log
            assert expected_state == actual_state, (
                "expected state for log '%s' is %d, actual state %d" %
                (expected_log, expected_state, actual_state))


@pytest.mark.usefixtures("no_statefile")
def test_section_eventlog__no_statefile__no_events(request, testconfig,
                                                   expected_output_no_events,
                                                   actual_output, testfile):
    # request.node.name gives test name
    remotetest(testconfig, expected_output_no_events, actual_output, testfile,
               request.node.name)


@pytest.mark.usefixtures("with_statefile", "create_events")
def test_section_eventlog__application_warnings(
        request, testconfig, expected_output_application_events, actual_output,
        testfile):
    # request.node.name gives test name
    remotetest(testconfig, expected_output_application_events, actual_output,
               testfile, request.node.name)
