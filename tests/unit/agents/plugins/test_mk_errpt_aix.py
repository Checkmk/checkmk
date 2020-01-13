import os
import subprocess
import pytest
from testlib import cmk_path

PLUGIN = os.path.join(cmk_path(), 'agents', 'plugins', 'mk_errpt.aix')

ERRPT_OUTPUT = [
    u'IDENTIFIER TIMESTAMP  T C RESOURCE_NAME  DESCRIPTION',
    u'8650BE3F   0820122810 I H ent2           ETHERCHANNEL RECOVERY',
    u'F3846E13   0820122510 P H ent2           ETHERCHANNEL FAILOVER',
    u'8650BE3F   0820104410 I H ent2           ETHERCHANNEL RECOVERY',
    u'F3846E13   0820093810 P H ent2           ETHERCHANNEL FAILOVER',
    u'8650BE3F   0820090910 I H ent2           ETHERCHANNEL RECOVERY',
]

STATE_FILE_NAME = "mk_errpt_aix.last_reported"

LEGACY_STATE_FILE_NAME = "mk_logwatch_aix.last_reported"


def _prepare_mock_errpt(tmp_path, errpt_output):
    errpt_name = str(tmp_path / 'errpt')
    errpt_script = ''.join(['#!/bin/sh\n'] + ['echo "%s"\n' % line for line in errpt_output])
    with open(errpt_name, 'w') as errpt_file:
        errpt_file.write(errpt_script)
    os.chmod(errpt_name, 0o777)  # nosec


def _get_env(tmp_path):
    env = os.environ.copy()
    env.update({"PATH": '%s:%s' % (tmp_path, os.getenv("PATH")), "MK_VARDIR": str(tmp_path)})
    return env


def prepare_state(filepath, write_name, state):
    # make sure we have no left-over files
    for base_file in (STATE_FILE_NAME, LEGACY_STATE_FILE_NAME):
        try:
            (filepath / base_file).unlink()
        except OSError:
            pass

    if state is None:
        return

    with (filepath / write_name).open('w') as statefile:
        statefile.write(u"%s\n" % state)


def read_state(filepath):
    try:
        with (filepath / STATE_FILE_NAME).open() as statefile:
            new_state = statefile.read()
            assert new_state[-1] == u"\n"
            return new_state[:-1]
    except IOError:
        return None


def _format_expected(lines):
    added_prefix = ['C %s\n' % line for line in lines]
    added_header = ['<<<logwatch>>>\n', '[[[errorlog]]]\n'] + added_prefix
    return ''.join(added_header)


@pytest.mark.parametrize(
    "state_file_name,errpt_output,last_reported,expectations",
    [
        (
            STATE_FILE_NAME,
            ERRPT_OUTPUT,
            [None, u"", ERRPT_OUTPUT[3], ERRPT_OUTPUT[1], u"something else entirely"],
            [ERRPT_OUTPUT[1:], ERRPT_OUTPUT[1:], ERRPT_OUTPUT[1:3], [], ERRPT_OUTPUT[1:]],
        ),
        (
            STATE_FILE_NAME,
            ERRPT_OUTPUT[:1],  # no output, just header
            [None, u"", u"what ever"],
            [[], [], []],
        ),
        (  # legacy statefile name:
            'mk_logwatch_aix.last_reported',
            ERRPT_OUTPUT,
            [None, u"", ERRPT_OUTPUT[3], ERRPT_OUTPUT[1], u"something else entirely"],
            [ERRPT_OUTPUT[1:], ERRPT_OUTPUT[1:], ERRPT_OUTPUT[1:3], [], ERRPT_OUTPUT[1:]],
        ),
    ])
def test_mk_errpt_aix(tmp_path, state_file_name, errpt_output, last_reported, expectations):

    _prepare_mock_errpt(tmp_path, errpt_output)
    env = _get_env(tmp_path)

    for state, expected in zip(last_reported, expectations):

        prepare_state(tmp_path, state_file_name, state)

        output = subprocess.check_output(PLUGIN, env=env)
        expected = _format_expected(expected)
        assert output == expected, "expected\n  %r, but got\n  %r" % (expected, output)

        new_state = read_state(tmp_path)

        if len(errpt_output) > 1:  # we should have updated state file
            assert new_state == errpt_output[1]
        else:  # it should not have changed
            assert new_state == state
