#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import os
import re
from pathlib import Path

import pytest

from tests.testlib.utils import repo_path

from ..conftest import ChangedFiles

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
    # TODO: Update all agent plugins to use sys.stdout.write instead of print
    "agents/plugins",
]

exclude_folders = ["plugins/build", "plugins/build_32", "chroot"]
exclude_files = ["bin/mkeventd_open514", "bin/mkevent"]


def find_debugs(line: str) -> re.Match[str] | None:
    return re.match(r"(pprint\.)?pp?rint[( ]", line.lstrip())


@pytest.mark.parametrize(
    "line", ['  print "hello Word"', 'print("variable")', "  pprint(dict)", "  pprint.pprint(list)"]
)
def test_find_debugs(changed_files: ChangedFiles, line: str) -> None:
    assert find_debugs(line)


@pytest.mark.parametrize("line", ['sys.stdout.write("message")', "# print(variable)"])
def test_find_debugs_false(changed_files: ChangedFiles, line: str) -> None:
    assert find_debugs(line) is None


@pytest.mark.parametrize(
    "path",
    [p for dir_path in check_paths for p in [repo_path() / dir_path] if p.exists()],
)
def test_find_debug_code(changed_files: ChangedFiles, path: str) -> None:
    scanned = 0

    for dirpath, _, filenames in os.walk(path):
        scanned += 1
        for filename in filenames:
            file_path = f"{dirpath}/{filename}"

            if not changed_files.is_changed(Path(file_path)):
                continue

            if [folder for folder in exclude_folders if folder in file_path]:
                continue

            if file_path.endswith((".pyc", ".whl", ".tar.gz", ".swp")):
                continue

            if os.path.relpath(file_path, repo_path()) in exclude_files:
                continue

            try:
                with open(file_path) as file:
                    for nr, line in enumerate(file.readlines()):
                        if nr == 0 and ("bash" in line or "php" in line):
                            break  # skip non python files

                        assert not find_debugs(line), 'Found "print(...)" call in %s:%d' % (
                            file_path,
                            nr + 1,
                        )
            except UnicodeDecodeError:
                LOGGER.warning("Could not read %r due to UnicodeDecodeError", file_path)

    assert scanned > 0
