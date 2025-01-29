#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from contextlib import chdir
from pathlib import Path

from omdlib.global_options import GlobalOptions


def test_orig_working_directory(tmp_path: Path) -> None:
    base_path = tmp_path.joinpath("lala")
    base_path.mkdir(parents=True)
    with chdir(base_path):
        global_options = GlobalOptions.default()
    assert global_options.orig_working_directory == str(base_path)


def test_orig_working_directory_not_existing(tmp_path: Path) -> None:
    test_dir = tmp_path.joinpath("lala")
    test_dir.mkdir()
    with chdir(test_dir):
        test_dir.rmdir()
        assert not test_dir.exists()

        global_options = GlobalOptions.default()
    assert global_options.orig_working_directory == "/"
