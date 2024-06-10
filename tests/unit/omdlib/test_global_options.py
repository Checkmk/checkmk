#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
from pathlib import Path

from omdlib.global_options import _get_orig_working_directory


def test_orig_working_directory(tmp_path: Path) -> None:
    orig_wd = os.getcwd()
    try:
        base_path = tmp_path.joinpath("lala")
        base_path.mkdir(parents=True)
        os.chdir(str(base_path))
        assert _get_orig_working_directory() == str(base_path)
    finally:
        os.chdir(orig_wd)


def test_get_orig_working_directory_not_existing(tmp_path: Path) -> None:
    orig_wd = os.getcwd()
    try:
        test_dir = tmp_path.joinpath("lala")
        test_dir.mkdir()

        os.chdir(str(test_dir))
        assert os.getcwd() == str(test_dir)

        test_dir.rmdir()
        assert not test_dir.exists()

        assert _get_orig_working_directory() == "/"
    finally:
        os.chdir(orig_wd)
