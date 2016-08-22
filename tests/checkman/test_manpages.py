#!/usr/bin/python
# encoding: utf-8

import os
import sys
from testlib import cmk_path


def test_manpage_files():
    os.chdir(cmk_path())

    checkend_manpages = 0
    for f in os.listdir("%s/checkman" % cmk_path()):
        if f[0] == ".":
            continue
        _check_manpage(f)
        checkend_manpages += 1

    assert checkend_manpages > 0


def _check_manpage(name):
    found_catalog = False
    for line in open("%s/checkman/%s" % (cmk_path(), name)):
        if line.startswith("catalog: "):
            found_catalog = True

    assert found_catalog, "Did not find \"catalog:\" header in manpage \"%s\"" % name


def test_manpage_list():
    result = os.popen("cd %s ; ./check_mk --list-man 2>&1" % cmk_path()).read()
    assert result != ""
    assert not "ERROR" in result, "Manpage list broken \"./check_mk --list-man\": %s\"" % result
    assert type(eval(result)) == dict


def test_missing_manpage():
    missing = []

    checks = 0
    for line in os.popen('cd %s ; ./check_mk --list-checks' % cmk_path()).readlines():
        checks += 1
        line = line.strip()
        check_name = line.split(" ", 1)[0]
        assert '(no man page present)' not in line, "Manpage missing: %s" % check_name

    if checks == 0:
        raise Exception("\"./check_mk --list-checks\" Did not output a checks")
