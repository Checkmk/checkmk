#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
import logging
import re
import subprocess
import warnings
from collections.abc import Sequence
from pathlib import Path

import pytest

from tests.testlib.common.repo import repo_path

LOGGER = logging.getLogger(__name__)

# toggle for finding unused patterns from IGNORE_PATHS and IGNORE_SUFFIXES
CHECK_UNUSED_PATTERNS = False

# verbose output options
VERBOSE_NO_PYTHON = False
VERBOSE_PRINT_HEADER = False

#
LOG_FINDINGS_INFO = True


def is_text_file(file_path: Path, blocksize: int = 512) -> bool:
    try:
        with file_path.open("rb") as f:
            block = f.read(blocksize)
        block.decode("utf-8")
        return True
    except UnicodeDecodeError:
        return False


def is_python_source(file_path: Path, content: str) -> bool:
    if re.match(r"^\s*#!.*python3", content):
        # starting with a shebang for Python 3
        # (that's a good starting point - these are definitely Python files)
        LOGGER.debug("%s: shebang detected -> python", file_path)
        return True

    if not content.strip():
        # empty file -> no Python source
        if VERBOSE_NO_PYTHON:
            LOGGER.debug("%s: empty file -> no python", file_path)
        return False

    try:
        # Try to parse the content as Python source code.
        # If it raises a SyntaxError, it's not valid Python code.
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            ast.parse(content)

        # "valid in python" still might lead to a lot of false positives
        # (like a text file with "hello" in it)
        if re.search("import |def |class |print", content):
            # if it contains import, def, or class, it's likely Python code
            LOGGER.debug("%s: ast.parse + python keywords -> python", file_path)
            return True

        if VERBOSE_NO_PYTHON:
            LOGGER.debug("%s: ast.parse OK, but no keywords", file_path)
        return False
    except SyntaxError:
        if VERBOSE_NO_PYTHON:
            LOGGER.debug("%s: ast.parse failed -> no python", file_path)

    return False


# paths ignored for this test (specific files or regex match pattern) -- relative to the repo root
IGNORE_PATHS = [
    r".*BUILD$",
    r".*WORKSPACE$",
    r".*README$",
    r"agents/modules/windows/BUILD_NUM$",
    r"\.site$",
    r".*\.gitignore$",
    r".*\.gitkeep$",
    r".*\.keep$",
    r".*\.editorconfig$",
    r".*\.bazelignore$",
    r".*\.prettierignore$",
    r".*\.prettierrc$",
    r"tests/unit/cmk/utils/prediction/test-files/.*",
    r".*test_data/.*",
    r"\.werks/first_free",
    r"agents/wnx/scripts/os_setup/msvc/vs-.*",
    # todo: discuss with CI team if we should ignore these
    r"bazel/.*",
    r"locale/.*",
]

PYTHON_SUFFIXES = [
    # python extension
    ".py",
    ".pyi",
    ".wsgi",
    ".typed",
]

IGNORE_SUFFIXES = [
    # non-python stuff
    ".bazel",
    ".bzl",
    ".cab",
    ".cap",
    ".cfg",
    ".cfg-sample",
    ".conf",
    ".dat",
    ".dict",
    ".html",
    ".in",
    ".json",
    ".lock",
    ".lock",
    ".map",
    ".marker",
    ".md",
    ".mk",
    ".output",
    ".php",
    ".ps1",
    ".state",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
]


# test can't yet be switched on (clean existing files first).
# In order to see results, LOG_FINDINGS_INFO must be set to True
@pytest.mark.xfail(reason="Starting off with 147 files - yet to be initially cleaned -> CMK-25064")
def test_python_files_have_py_extension(python_files: Sequence[str]) -> None:
    """
    Test to ensure all Python source files have a .py (or other allowed) extension.
    Scans for Python source files without allowed extension and reports them
    """
    base_dir: Path = repo_path()
    if python_files == ["*"]:
        # get all files in the repository, but only focus on files in version control
        file_candidates = [
            base_dir / f
            for f in subprocess.check_output(
                ["git", "ls-files"], cwd=base_dir, text=True
            ).splitlines()
        ]
    else:
        # use supplied files
        file_candidates = [Path(f) for f in python_files]

    LOGGER.info("Scanning %d files...", len(file_candidates))
    LOGGER.info("Allowed Python extensions: %s", ", ".join(PYTHON_SUFFIXES))

    mismatches = []
    patterns_matched = set()
    # -------------------------------------------------------------
    # scan files
    # -------------------------------------------------------------
    for file_path in file_candidates:
        if not file_path.is_file():
            continue

        # -------------------------------------------------------------
        # Phase 1: sort out as many files by path/extension
        # -------------------------------------------------------------
        # Skip files that already have a .py extension or other non-python extensions
        if file_path.suffix in PYTHON_SUFFIXES or file_path.suffix in IGNORE_SUFFIXES:
            if CHECK_UNUSED_PATTERNS:
                patterns_matched.add(file_path.suffix)
            continue

        rel_path = file_path.relative_to(base_dir)
        if any(re.match(pattern, str(rel_path)) for pattern in IGNORE_PATHS):
            if CHECK_UNUSED_PATTERNS:
                patterns_matched.update(
                    {pattern for pattern in IGNORE_PATHS if re.match(pattern, str(rel_path))}
                )
            continue

        # -------------------------------------------------------------
        # Phase 2: simple file content evaluation
        # -------------------------------------------------------------
        # Only consider text files.
        if not is_text_file(file_path):
            continue

        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception:
            continue

        # -------------------------------------------------------------
        # Phase 3: evaluate complete content (parse python)
        # -------------------------------------------------------------
        # as this is more resource intensive, this should be at the end
        if is_python_source(rel_path, content):
            # Record relative path for reporting.
            mismatches.append(str(rel_path))

            if VERBOSE_PRINT_HEADER:
                LOGGER.debug("head -3 %s:\n%s\n", file_path, "\n".join(content.splitlines()[:3]))

    # -------------------------------------------------------------
    # post-processing
    # -------------------------------------------------------------
    if CHECK_UNUSED_PATTERNS:
        ignore_paths_unused = [ignp for ignp in IGNORE_PATHS if ignp not in patterns_matched]
        ignore_suffixes_unused = [igns for igns in IGNORE_SUFFIXES if igns not in patterns_matched]

        if ignore_paths_unused:
            LOGGER.info("unused in IGNORE_PATHS:")
            for pattern in ignore_paths_unused:
                LOGGER.info(" - %s", pattern)
        else:
            LOGGER.info("OK: All entries from IGNORE_PATHS are used.")

        if ignore_suffixes_unused:
            LOGGER.info("unused in IGNORE_SUFFIXES:")
            for suffix in ignore_suffixes_unused:
                LOGGER.info(" - %s", suffix)
        else:
            LOGGER.info("OK: All entries from IGNORE_SUFFIXES are used.")

    # -------------------------------------------------------------
    # report findings
    # -------------------------------------------------------------
    if mismatches:
        msg = (
            f"Found {len(mismatches)} Python source file(s) without a '.py' extension:\n"
            + "See https://wiki.lan.checkmk.net/x/IoVWBg#PythonFiles\n"
            + "\n".join(f" -- {rel_path}" for rel_path in sorted(mismatches))
        )
        if LOG_FINDINGS_INFO:
            LOGGER.info(msg)
        pytest.fail(msg)
    else:
        LOGGER.info("No mismatches found in %d files.", len(file_candidates))
