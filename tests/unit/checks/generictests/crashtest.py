#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
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
import pprint
import tarfile
from pathlib import Path
from typing import Any, Dict

import pytest

from tests.testlib import Check

from ..checktestlib import CheckResult
from .regression import WritableDataset
from .run import run

pytestmark = pytest.mark.checks

# FIXME automatic download crashreports to ~git/zeug_cmk/crashreports/crashdata
CRASHDATA_DIR = Path.home() / "crashdata"


class SkipReport(RuntimeError):
    pass


class CrashDataset(WritableDataset):
    def __init__(self, crash_report_fn):
        """
        Try to create a dataset like object from a crash report

        Errors that raise a SkipReport exception will result
        in a SKIP-state in the state file.
        """
        with tarfile.open(crash_report_fn, "r:gz") as tar:
            tar_entry = tar.extractfile("crash.info")
            assert tar_entry is not None
            content = tar_entry.read()
        crashinfo = json.loads(content)

        if crashinfo["crash_type"] != "check":
            raise SkipReport("crash type: %s" % crashinfo["crash_type"])

        traceback = crashinfo.get("exc_traceback", [])
        for line in traceback:
            if "/local/share/check_mk/" in line[0]:
                raise SkipReport("local check plugin")

        init_dict = {}
        full_checkname = crashinfo["details"]["check_type"]
        if full_checkname == "discovery":
            full_checkname = self._find_checkname_from_traceback(traceback)
            if not full_checkname:
                raise SkipReport("found no check plugin from traceback")

        self.full_checkname = full_checkname
        checkname = self.full_checkname.split(".", 1)[0]
        init_dict["checkname"] = checkname

        local_vars_encoded = crashinfo.get("local_vars")
        if not local_vars_encoded:
            raise SkipReport("no local_vars")

        # can't use json.loads here :-(
        exec_scope: Dict[str, Any] = {}
        exec_command = "local_vars = " + base64.b64decode(local_vars_encoded).decode("utf-8")
        try:
            exec(exec_command, exec_scope)  # pylint: disable=exec-used
        except Exception as exc:
            raise SkipReport("failed to load local_vars: %r" % exc)

        local_vars = exec_scope["local_vars"]
        if "_no_item" in local_vars:
            local_vars["item"] = local_vars["_no_item"]

        if not ("info" in local_vars or "parsed" in local_vars):
            raise SkipReport("found neither 'info' nor 'parsed'")

        init_dict["parsed"] = local_vars.get("parsed")
        init_dict["info"] = local_vars.get("info")
        self.vars = local_vars
        self.crash_id = crash_report_fn.split("/")[-1].replace(".gz", "").replace(".tar", "")
        super().__init__(init_dict)

    def _find_checkname_from_traceback(self, traceback):
        for line in traceback[::-1]:
            if "share/check_mk/checks/" in line[0]:
                return line[0].split("share/check_mk/checks/")[-1]
        return None

    def __repr__(self):
        return "CrashDataset(checkname=%r, id=%r)" % (self.checkname, self.crash_id)


class CrashReportList(list):
    """Save crash reports below $HOME/crashdata.
    Use update_crashes.py in order to read new crash reports and list them in the state file.
    Crash reports are read from state_file in order to speed up generic crash report tests"""

    def __init__(self, state_file):
        self.state_file = state_file
        with open(self.state_file) as file_:
            # A line contains: ID STATE AMOUNT I N F O
            lines = [line.strip().split() for line in file_.readlines()]

        self.state_info = [[l[0], l[1], l[2], " ".join(l[3:])] for l in lines if l]
        super().__init__(self.load())

    def load(self):
        try:
            for crashdata in self._iter_applicable_crashes():
                yield crashdata
        finally:
            with open(self.state_file, "w") as file_:
                file_.write("\n".join([" ".join(line).strip() for line in self.state_info]))

    def _iter_applicable_crashes(self):
        for cr_info in self.state_info:
            if cr_info[1] == "SKIP":
                continue

            crash_report_path = CRASHDATA_DIR / Path("%s.tar.gz" % cr_info[0])
            if not crash_report_path.exists():
                continue

            try:
                yield CrashDataset(str(crash_report_path))
            except SkipReport as exc:
                cr_info[1] = "SKIP"
                cr_info[3] = "Exception: %s" % exc


def test_crashreport(fix_plugin_legacy, crashdata) -> None:
    try:
        run(fix_plugin_legacy.check_info, crashdata)
        check = Check(crashdata.full_checkname)
        if "item" in crashdata.vars:
            item = crashdata.vars["item"]
            params = crashdata.vars.get("params", {})
            if crashdata.parsed:
                raw_result = check.run_check(item, params, crashdata.parsed)
            else:
                raw_result = check.run_check(item, params, crashdata.info)
            print(CheckResult(raw_result))
    except Exception:
        pprint.pprint(crashdata.__dict__)
        crashdata.write("/tmp")
        raise
