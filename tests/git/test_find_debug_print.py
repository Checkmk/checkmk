#!/usr/bin/python
# encoding: utf-8

import os
import re
import pytest
from testlib import cmk_path, cmc_path, cme_path

check_paths = [
    "bin",
    "cmk_base",
    "cmk_base/cee",
    "cmk_base/cme",
    "cmk_base/modes",
    "cmk_base/default_config",
    "lib",
    "checks",
    "inventory",
    "notifications",
    "active_checks",
    # CMC specific
    "agents/bakery",
    # TODO: Update all agent plugins to use sys.stdout.write instead of print
    "agents/plugins",
]

exclude_folders = ["plugins/build", "plugins/build_32", "chroot"]


def find_debugs(line):
    return re.match(r"(pprint\.)?pp?rint[( ]", line.lstrip())


@pytest.mark.parametrize(
    "line",
    ['  print "hello Word"', 'print("variable")', '  pprint(dict)', '  pprint.pprint(list)'])
def test_find_debugs(line):
    assert find_debugs(line)


@pytest.mark.parametrize("line", ['sys.stdout.write("message")', '# print(variable)'])
def test_find_debugs_false(line):
    assert find_debugs(line) is None


@pytest.mark.parametrize(
    'path',
    list(
        filter(os.path.exists, [
            "%s/%s" % (base_path, dir_path)
            for base_path in [cmk_path(), cmc_path(), cme_path()]
            for dir_path in check_paths
        ])))
def test_find_debug_code(path):
    scanned = 0

    for dirpath, _, filenames in os.walk(path):
        scanned += 1
        for filename in filenames:
            file_path = "%s/%s" % (dirpath, filename)
            if [folder for folder in exclude_folders if folder in file_path]:
                continue

            for nr, line in enumerate(open(file_path)):
                if nr == 0 and ("bash" in line or "php" in line):
                    break  # skip non python files

                assert not find_debugs(line), "Found \"print(...)\" call in %s:%d" % (file_path,
                                                                                      nr + 1)

    assert scanned > 0
