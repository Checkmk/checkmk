#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from pathlib import Path

import pytest

from tests.code_quality.utils import ChangedFiles


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption("--python-files", nargs="*", default=[], help="python files to check")
    parser.addoption("--changed-files", nargs="*", default=[], help="files to check")
    parser.addoption("--test-all-files", action="store_true", help="test all files")


@pytest.fixture
def python_files(request: pytest.FixtureRequest) -> Sequence[str]:
    if not (files := request.config.getoption("--python-files")):
        pytest.skip()
    return files


@pytest.fixture
def changed_files(request: pytest.FixtureRequest) -> ChangedFiles:
    test_all_files = request.config.getoption("--test-all-files")
    files = request.config.getoption("--changed-files")
    if not test_all_files and not files:
        pytest.skip()
    return ChangedFiles(
        test_all_files=test_all_files, file_paths={Path("../" + f).resolve() for f in files}
    )
