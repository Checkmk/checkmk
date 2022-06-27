#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from tests.testlib import cmk_path

from ..conftest import ChangedFiles


def test_find_debug_code(changed_files: ChangedFiles) -> None:
    to_scan = _files_to_scan(changed_files)

    for path in to_scan:
        with path.open(encoding="utf-8") as f:
            for line in f:
                l = line.lstrip()
                assert not l.startswith("html.debug("), 'Found "html.debug(...)" call'


def _files_to_scan(changed_files: ChangedFiles):
    to_scan = [Path(cmk_path(), "web", "app", "index.wsgi")]
    for matched_file in Path(cmk_path(), "cmk", "gui").glob("**/*.py"):
        if matched_file.is_file() and changed_files.is_changed(matched_file):
            to_scan.append(matched_file)
    return to_scan
