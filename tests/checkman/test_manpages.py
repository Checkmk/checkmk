#!/usr/bin/python
# encoding: utf-8

import os
import sys
import subprocess
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


def test_missing_manpage(site):
    missing = []

    p = site.execute(["check_mk", "--list-checks"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    result = p.communicate()[0]
    assert p.returncode == 0

    checks = 0
    for line in result.split("\n"):
        checks += 1
        line = line.strip()
        check_name = line.split(" ", 1)[0]
        assert '(no man page present)' not in line, "Manpage missing: %s" % check_name

    if checks == 0:
        raise Exception("\"check_mk --list-checks\" Did not output a checks")
