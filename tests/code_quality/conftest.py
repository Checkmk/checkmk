#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-any-return"

import logging
import subprocess
from collections.abc import Sequence
from pathlib import Path

import pytest

from tests.code_quality.utils import ChangedFiles, GitChanges, SummaryWriter

logger = logging.getLogger(__name__)


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption("--python-files", nargs="*", default=[], help="python files to check")
    parser.addoption("--changed-files", nargs="*", default=[], help="files to check")
    parser.addoption("--test-all-files", action="store_true", help="test all files")
    parser.addoption("--git-changes", type=str, help="path to git changes file with modes")
    parser.addoption("--result-out", type=str, help="path to write condensed results to")


@pytest.fixture
def python_files(request: pytest.FixtureRequest) -> Sequence[str]:
    logger.debug("Getting python files from request: %s", request)
    test_all_files = request.config.getoption("--test-all-files")
    python_files_option = request.config.getoption("--python-files")

    if test_all_files and python_files_option:
        raise ValueError(
            "Cannot use both --test-all-files and --python-files options at the same time"
        )

    if test_all_files:
        # Get all* Python files using the find-python-files script
        # (find-python-files excludes some paths like packages)
        repo_root = Path(__file__).resolve().parent.parent.parent
        script_path = repo_root / "scripts" / "find-python-files"

        try:
            result = subprocess.run(
                [str(script_path)],
                capture_output=True,
                text=True,
                check=True,
                cwd=str(repo_root),
            )
            files = result.stdout.strip().split("\n")
            return [f for f in files if f]  # Filter out empty strings
        except subprocess.CalledProcessError as e:
            logger.error("Failed to run find-python-files script: %s", e)
            pytest.skip("Could not retrieve Python files from find-python-files script")

    if not python_files_option:
        pytest.skip()
    return python_files_option


@pytest.fixture
def changed_files(request: pytest.FixtureRequest) -> ChangedFiles:
    test_all_files = request.config.getoption("--test-all-files")
    files = request.config.getoption("--changed-files")
    if not test_all_files and not files:
        pytest.skip()
    return ChangedFiles(
        test_all_files=test_all_files, file_paths={Path("../" + f).resolve() for f in files}
    )


@pytest.fixture
def result_out_file(request: pytest.FixtureRequest) -> str | None:
    """Get the path for result output file if specified."""
    return request.config.getoption("--result-out")


@pytest.fixture
def summary_writer(request: pytest.FixtureRequest) -> SummaryWriter:
    """Create a SummaryWriter instance with automatic test module and class detection."""
    result_out_file = request.config.getoption("--result-out")

    # Extract test module name from the test file path
    test_module = request.module.__name__ if request.module else ""

    # Extract test class name if the test is in a class
    test_class = ""
    if request.cls:
        test_class = request.cls.__name__
    else:
        # If not in a class, use the function name
        test_class = request.function.__name__ if request.function else ""

    return SummaryWriter(
        result_out_file=result_out_file, test_module=test_module, test_class=test_class
    )


@pytest.fixture
def git_changes(request: pytest.FixtureRequest) -> GitChanges | None:
    """retrieve git changes:
    * default use case: from <git_changes_file> (defined in tests/Makefile)
    * local changes (for testing): if --git-changes=LOCAL
    * all git versioned files for a cleanup check: if --test-all-files
    """
    git_changes_file = request.config.getoption("--git-changes") or ""
    test_all_files = request.config.getoption("--test-all-files")
    logger.debug("--git-changes=%s, --test-all-files=%s", git_changes_file, test_all_files)

    if not git_changes_file and not test_all_files:
        logger.info("Neither --git-changes nor --test-all-files supplied")
        return None

    # now get the files
    return GitChanges.from_git_changes_file(
        file_path_or_local=git_changes_file, test_all_files=test_all_files
    )
