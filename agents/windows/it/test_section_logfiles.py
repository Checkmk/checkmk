import io
import os
import platform
import re
import sys

import pytest
from remote import (actual_output, config, remotedir, remotetest,
                    run_subprocess, wait_agent, write_config)

section = 'logfiles'
testlog1 = os.path.join(remotedir, 'test1.log')
testlog2 = os.path.join(remotedir, 'test2.log')
testentry1 = 'foobar'
testentry2 = 'error'
state_pattern = re.compile(
    r'^(?P<logfile>[^\|]+)\|(?P<inode>\d+)\|(?P<size>\d+)\|(?P<offset>\d+)')
fileid_pattern = re.compile(r'^.*\:\s*(?P<fileid>0x[0-9a-fA-F]+)')

# ugly hacks to get to know the config param and utf encoding in use:


class Globals(object):
    config_param_in_use = None
    utf_encoding = None


def get_log_state(line):
    m = state_pattern.match(line)
    if m is None:
        return None, (None, None, None)
    return m.group('logfile'), (int(m.group('inode')), int(m.group('size')),
                                int(m.group('offset')))


# stat.st_inode remains 0 on Windows -> need to hack the fileid with fsutil
def get_fileid(filename):
    cmd = ['fsutil', 'file', 'queryfileid', filename]
    exit_code, stdout, stderr = run_subprocess(cmd)
    if stdout:
        sys.stdout.write(stdout)
    if stderr:
        sys.stderr.write(stderr)
    assert exit_code == 0, "'%s' failed" % ' '.join(cmd)
    m = fileid_pattern.match(stdout)
    assert m is not None, "'%s' does not match fileid pattern" % stdout
    return int(m.group('fileid'), base=16)


def get_file_state(filename):
    stat = os.stat(filename)
    # stat.st_inode remains 0 on Windows -> need to hack the fileid with fsutil
    return get_fileid(filename), stat.st_size, stat.st_size


def logtitle(log):
    return re.escape(r'[[[%s]]]' % log)


@pytest.fixture
def testfile():
    return os.path.basename(__file__)


@pytest.fixture(params=['default', 'from_start', 'rotated', 'nocontext'])
def testconfig(request, config):
    config.set("global", "sections", section)
    config.set("global", "crash_debug", "yes")
    config.add_section(section)
    Globals.config_param_in_use = request.param
    tag = '' if request.param == 'default' else '%s ' % request.param
    config.set(section, "textfile", "%s%s|%s%s" % (tag, testlog1, tag,
                                                   testlog2))
    return config


@pytest.fixture(params=[
    'no_glob', 'star_begin', 'star_end', 'star_middle', 'question_begin',
    'question_end', 'question_middle'
])
def testconfig_glob(request, testconfig):
    entry = {
        'no_glob': testentry2,
        'star_begin': '*' + testentry2[2:],
        'star_end': testentry2[:3] + '*',
        'star_middle': testentry2[:2] + '*' + testentry2[-1:],
        'question_begin': '?' + testentry2[1:],
        'question_end': testentry2[:-1] + '?',
        'question_middle': testentry2[:2] + '?' + testentry2[3:]
    }[request.param]
    testconfig.set(section, "crit", entry)
    return testconfig


@pytest.fixture
def expected_output_no_statefile():
    expected_output = [re.escape(r'<<<logwatch>>>'), logtitle(testlog1)]
    if Globals.config_param_in_use == 'from_start':
        expected_output += [r'\. %s' % testentry1, r'C %s' % testentry2]
    expected_output.append(logtitle(testlog2))
    if Globals.config_param_in_use == 'from_start':
        expected_output += [r'\. %s' % testentry1, r'C %s' % testentry2]
    return expected_output


@pytest.fixture
def expected_output_with_statefile():
    expected_output = [re.escape(r'<<<logwatch>>>'), logtitle(testlog1)]
    if Globals.config_param_in_use != 'nocontext':
        expected_output.append(r'\. %s' % testentry1)
    expected_output += [r'C %s' % testentry2, logtitle(testlog2)]
    if Globals.config_param_in_use != 'nocontext':
        expected_output.append(r'\. %s' % testentry1)
    expected_output.append(r'C %s' % testentry2)
    return expected_output


@pytest.fixture
def no_statefile():
    if platform.system() == 'Windows':
        try:
            os.unlink(os.path.join(remotedir, 'state', 'logstate.txt'))
        except OSError:
            # logstate.txt may not exist if this is the first test to be run
            pass
    yield


@pytest.fixture
def with_statefile():
    if platform.system() == 'Windows':
        # simulate new log entries by setting file size & offset
        # to 0 (utf-8) or 2 (utf-16)
        filesize = 2 if Globals.utf_encoding == 'utf-16' else 0
        with open(os.path.join(remotedir, 'state', 'logstate.txt'),
                  'w') as statefile:
            for logfile in [testlog1, testlog2]:
                fileid = get_fileid(logfile)
                file_state = [
                    str(item)
                    for item in [logfile, fileid, filesize, filesize]
                ]
                statefile.write('%s\r\n' % '|'.join(file_state))
    yield


@pytest.fixture(autouse=True)
def verify_logstate():
    yield
    if platform.system() == 'Windows':
        expected_logstate = {
            logfile: get_file_state(logfile)
            for logfile in [testlog1, testlog2]
        }
        with open(os.path.join(remotedir, 'state',
                               'logstate.txt')) as statefile:
            actual_logstate = dict(get_log_state(line) for line in statefile)
        for (expected_log, expected_state), (actual_log, actual_state) in zip(
                sorted(expected_logstate.items()),
                sorted(actual_logstate.items())):
            assert expected_log == actual_log
            assert expected_state[0] == actual_state[0], (
                "expected file id for log '%s' is %d but actual file id %d" %
                (expected_log, expected_state[0], actual_state[0]))
            assert expected_state[1] == actual_state[1], (
                "expected file size for log '%s' is %d but actual file size %d"
                % (expected_log, expected_state[1], actual_state[1]))
            assert expected_state[2] == actual_state[2], (
                "expected offset for log '%s' is %d but actual offset number %d"
                % (expected_log, expected_state[2], actual_state[2]))


@pytest.fixture(params=['utf-8', 'utf-16'], autouse=True)
def manage_logfiles(request):
    Globals.utf_encoding = request.param
    if platform.system() == 'Windows':
        for log in [testlog1, testlog2]:
            with io.open(log, 'w', encoding=request.param) as logfile:
                for entry in [unicode(testentry1), unicode(testentry2)]:
                    logfile.write('%s\r\n' % entry)
    yield
    if platform.system() == 'Windows':
        for log in [testlog1, testlog2]:
            os.unlink(log)


@pytest.mark.usefixtures("no_statefile")
def test_section_logfiles__new_file(request, testconfig_glob,
                                    expected_output_no_statefile,
                                    actual_output, testfile):
    # request.node.name gives test name
    remotetest(testconfig_glob, expected_output_no_statefile, actual_output,
               testfile, request.node.name)


@pytest.mark.usefixtures("with_statefile")
def test_section_logfiles__new_entries_in_log(request, testconfig_glob,
                                              expected_output_with_statefile,
                                              actual_output, testfile):
    # request.node.name gives test name
    remotetest(testconfig_glob, expected_output_with_statefile, actual_output,
               testfile, request.node.name)
