"""Script to run generic tests on crash reports

This is actually a script, but we need all the test magic,
so call it as a test.

To run generic tests on crash reports, call it with a state
file as option:

  py.test -T unit tests/unit/checks/generictests/crashtest.py \
  --crashstates ~/tmp/my_crash_states

Be aware: This will alter the provided file!

There should be a state file in ~/git/zeug_cmk/crashtest/.

The state file should be a list of lines with the following
words in it:
 CRASH_REPORT_FILE STATE COMMENT
Where:
 * CRASH_REPORT_FILE is  the path of a crash report (.tar.gz,
   either absolute or relative to the state file itself)
 * STATE is an arbitrary word; is it is 'SKIP' the
   corresponding crash report is skipped
 * The rest of the line is ignored, and can be used for comments

The scrip will then start running generic tests on all datasets
created from crash reports, starting from the bottom (so you can
append new files)

Note that this will only work, if the crash report contains the
local variables 'parsed' or 'info'.
"""
import base64
import json
import os
import tarfile
import pytest

import generictests
from checktestlib import CheckResult

pytestmark = pytest.mark.checks


class SkipReport(RuntimeError):
    pass


class CrashDataset(object):
    def __init__(self, crash_report_fn):
        '''
        Try to create a dataset like object from a crash report

        Errors that raise a SkipReport exception will result
        in a SKIP-state in the state file.
        '''
        with tarfile.open(crash_report_fn, "r:gz") as tar:
            content = tar.extractfile('crash.info').read()
        crashinfo = json.loads(content)

        if crashinfo['crash_type'] != 'check':
            raise SkipReport("crash type: %s" % crashinfo['crash_type'])
        self.full_checkname = crashinfo['details']['check_type']
        self.checkname = self.full_checkname.split('.', 1)[0]

        local_vars_encoded = crashinfo.get('local_vars')
        if not local_vars_encoded:
            raise SkipReport("no local_vars")

        # can't use json.loads here :-(
        exec_scope = {}
        exec_command = 'local_vars = ' + base64.b64decode(local_vars_encoded)
        try:
            exec (exec_command, exec_scope)  # pylint: disable=exec-used
        except Exception as exc:
            raise SkipReport("failed to load local_vars: %r" % exc)

        local_vars = exec_scope['local_vars']
        if '_no_item' in local_vars:
            local_vars['item'] = local_vars['_no_item']

        if not ('info' in local_vars or 'parsed' in local_vars):
            raise SkipReport("found neither 'info' nor 'parsed'")

        self.parsed = local_vars.get('parsed')
        self.info = local_vars.get('info')
        self.vars = local_vars
        self.crash_id = crash_report_fn[-20:-7]

    def __repr__(self):
        return 'CrashDataset(checkname=%r, id=%r)' % (self.checkname, self.crash_id)


class CrashReportList(list):
    def __init__(self, statefile):
        self.statefile = statefile
        with open(self.statefile) as file_:
            lines = [l.strip() for l in file_.read().splitlines() if l.strip()]
        words = (line.split() for line in lines)
        self.state_info = [w + ([''] * max(2, 2 - len(w))) for w in words]
        self.dir = os.path.abspath(os.path.dirname(statefile))
        super(CrashReportList, self).__init__(self.load())

    def _iter_applicable_crashes(self):
        for item in self.state_info:
            if item[1] == 'SKIP':
                continue
            crash_report_fn = os.path.join(self.dir, item[0])
            try:
                yield CrashDataset(crash_report_fn)
            except SkipReport as exc:
                item[1] = 'SKIP (%s)' % exc

    def load(self):
        try:
            for crashdata in self._iter_applicable_crashes():
                yield crashdata
        finally:
            with open(self.statefile, 'w') as file_:
                lines = (' '.join(words).strip() for words in self.state_info)
                file_.write('\n'.join(lines))


def test_crashreport(check_manager, crashdata):

    generictests.run(check_manager, crashdata)

    if 'item' in crashdata.vars:
        item = crashdata.vars['item']
        params = crashdata.vars.get('params', {})
        check = check_manager.get_check(crashdata.full_checkname)
        if crashdata.parsed:
            raw_result = check.run_check(item, params, crashdata.parsed)
        else:
            raw_result = check.run_check(item, params, crashdata.info)
        print(CheckResult(raw_result))
