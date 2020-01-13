# encoding: utf-8

import os
import re
import logging
import pytest  # type: ignore
from testlib import cmk_path, cmc_path, cme_path

LOGGER = logging.getLogger()

check_paths = [
    "bin",
    # TODO: Why don't we check the whole cmk module?
    "cmk/base",
    "cmk/base/cee",
    "cmk/base/cme",
    "cmk/base/modes",
    "cmk/base/default_config",
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
exclude_files = ["bin/mkeventd_open514", "bin/mkevent"]


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

            if file_path.endswith((".pyc", ".whl", ".tar.gz")):
                continue

            if os.path.relpath(file_path, cmk_path()) in exclude_files:
                continue

            LOGGER.info("Checking file %s", file_path)
            for nr, line in enumerate(open(file_path)):
                if nr == 0 and ("bash" in line or "php" in line):
                    break  # skip non python files

                assert not find_debugs(line), "Found \"print(...)\" call in %s:%d" % (file_path,
                                                                                      nr + 1)

    assert scanned > 0
