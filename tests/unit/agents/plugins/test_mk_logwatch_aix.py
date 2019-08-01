import os
import subprocess
import pytest
from testlib import cmk_path

PLUGIN = os.path.join(cmk_path(), 'agents', 'plugins', 'mk_logwatch.aix')

ERRPT_OUTPUT = [
    'IDENTIFIER TIMESTAMP  T C RESOURCE_NAME  DESCRIPTION',
    '8650BE3F   0820122810 I H ent2           ETHERCHANNEL RECOVERY',
    'F3846E13   0820122510 P H ent2           ETHERCHANNEL FAILOVER',
    '8650BE3F   0820104410 I H ent2           ETHERCHANNEL RECOVERY',
    'F3846E13   0820093810 P H ent2           ETHERCHANNEL FAILOVER',
    '8650BE3F   0820090910 I H ent2           ETHERCHANNEL RECOVERY',
]


def _prepare_mock_errpt(tmp_path, errpt_output):
    errpt_name = str(tmp_path.joinpath('errpt'))
    errpt_script = ''.join(['#!/bin/sh\n'] + ['echo "%s"\n' % line for line in errpt_output])
    with open(errpt_name, 'w') as errpt_file:
        errpt_file.write(errpt_script)
    os.chmod(errpt_name, 0o777)  # nosec


def _get_env(tmp_path):
    env = os.environ.copy()
    env.update({"PATH": '%s:%s' % (tmp_path, os.getenv("PATH")), "MK_VARDIR": str(tmp_path)})
    return env


class StateFile(object):
    def __init__(self, tmp_path):
        super(StateFile, self).__init__()
        self.name = str(tmp_path.joinpath('mk_logwatch_aix.last_reported'))

    def set(self, state):
        if state is None:
            try:
                os.remove(self.name)
            except OSError:
                pass
            return
        with open(self.name, 'w') as statefile:
            statefile.write("%s\n" % state)

    def content(self):
        try:
            content = open(self.name).read()
            # ends with newline
            assert content[-1] == '\n'
            return content[:-1]
        except IOError:
            return None


def _format_expected(lines):
    added_prefix = ['C %s\n' % line for line in lines]
    added_header = ['<<<logwatch>>>\n', '[[[errorlog]]]\n'] + added_prefix
    return ''.join(added_header)


@pytest.mark.parametrize(
    "errpt_output,last_reported,expectations",
    [
        (
            ERRPT_OUTPUT,
            [None, "", ERRPT_OUTPUT[3], ERRPT_OUTPUT[1], "something else entirely"],
            [ERRPT_OUTPUT[1:], ERRPT_OUTPUT[1:], ERRPT_OUTPUT[1:3], [], ERRPT_OUTPUT[1:]],
        ),
        (
            ERRPT_OUTPUT[:1],  # no output, just header
            [None, "", "what ever"],
            [[], [], []],
        ),
    ])
def test_mk_logwatch_aix(tmp_path, errpt_output, last_reported, expectations):

    _prepare_mock_errpt(tmp_path, errpt_output)
    env = _get_env(tmp_path)
    statefile = StateFile(tmp_path)

    for state, expected in zip(last_reported, expectations):

        statefile.set(state)

        output = subprocess.check_output(PLUGIN, env=env)

        assert output == _format_expected(expected)
        if len(errpt_output) > 1:  # we should have updated state file
            assert statefile.content() == errpt_output[1]
        else:  # it should not have changed
            assert statefile.content() == state
