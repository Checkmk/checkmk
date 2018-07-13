#!/usr/bin/python
# encoding: utf-8

from testlib import cmk_path
import testlib.pylint_cmk as pylint_cmk

def test_pylint_web():
    exit_code = pylint_cmk.run_pylint(cmk_path(), ["web/app/index.wsgi", "cmk/gui", "enterprise/cmk/gui/cee", "managed/cmk/gui/cme"])
    assert exit_code == 0, "PyLint found an error in the web code"
