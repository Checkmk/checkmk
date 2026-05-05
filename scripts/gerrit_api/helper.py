#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Collection of helper objects and functions."""

import re

from scripts.gerrit_api.client import ChangeDetails, GerritClient


def change_has_tests(client: GerritClient, change: ChangeDetails) -> bool:
    """Confirm whether test files are present in a change.

    By validating presence of files with prefix 'test_' within directory starting with 'tests/'.
    """

    dir_pattern = "tests/"
    file_pattern = "test_"
    return any(
        file_path
        for file_path in client.changes_api.get_files(change)
        if re.findall(dir_pattern, file_path) and re.findall(file_pattern, file_path)
    )
