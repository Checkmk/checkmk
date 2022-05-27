#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import os
from typing import Sequence

from tests.testlib import cmk_path

LOGGER = logging.getLogger()

ignored_files = [
    "cmk/notification_plugins/ilert.py",
    "notifications/ilert",
    "cmk/notification_plugins/signl4.py",
    "notifications/signl4",
    "omd/packages/maintenance/merge-crontabs",
]

gpl_files = ["enterprise/cmk/cee/dcd/plugins/connectors/example_connector.py"]

enterprise_paths = [
    "enterprise/",
    "managed/",
    "plus/",
]

enterprise_files = [
    "cmk/base/automations/cee.py",
    "cmk/base/modes/cee.py",
    "cmk/base/default_config/cee.py",
    "cmk/base/default_config/cme.py",
]


def needs_enterprise_license(path: str) -> bool:
    if path in gpl_files:
        return False

    if any(p for p in enterprise_paths if path.startswith(p)):
        return True

    return path in enterprise_files


def get_file_header(path: str, lenght=30) -> str:
    with open(path, "r") as file:
        head = [file.readline() for x in range(lenght)]
        return "\n".join(head)


def test_license_headers(python_files: Sequence[str]) -> None:
    wrong_enterprise_headers = []
    wrong_gpl_headers = []

    for path in python_files:
        abs_path = os.path.realpath(path)
        rel_path = os.path.relpath(abs_path, cmk_path())

        if rel_path.startswith("tests") or rel_path in ignored_files:
            continue

        if needs_enterprise_license(rel_path):
            header = get_file_header(abs_path, lenght=30)
            if "Checkmk Enterprise License" not in header:
                wrong_enterprise_headers.append(rel_path)
        else:
            header = get_file_header(abs_path, lenght=25)
            if "GNU General Public" not in header:
                wrong_gpl_headers.append(rel_path)

    assert len(wrong_enterprise_headers) == 0, (
        f"The following files {wrong_enterprise_headers} should have "
        "Checkmk Enterprise License. It's either missing or not spelled correctly."
    )
    assert len(wrong_gpl_headers) == 0, (
        f"The following files {wrong_gpl_headers} should have "
        "GNU General Public License. It's either missing or not spelled correctly."
    )
