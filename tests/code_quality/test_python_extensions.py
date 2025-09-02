#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
import logging
import re
import warnings
from pathlib import Path

import pytest

from tests.code_quality.utils import GitChanges, SummaryWriter
from tests.testlib.common.repo import repo_path

logger = logging.getLogger(__name__)

# toggle for finding unused patterns from IGNORE_PATHS and IGNORE_SUFFIXES
CHECK_UNUSED_PATTERNS = False

# ----------------------------------------------------------------------------------------
# the following groups of files are still under discussion - and thus ignored for now
# ----------------------------------------------------------------------------------------
# toggle for ignoring executable wrapper files (short Python files that just import and call main)
# this is only relevant for
#   - added and copied files (as long as INCLUDE_MODIFIED is False)
#   - --test-all-files
IGNORE_EXECUTABLE_WRAPPERS = False
# toggle for ignoring treasures (doc/treasures)
IGNORE_TREASURES = True
# toggle for also checking modified files (only relevant with git changes)
INCLUDE_MODIFIED = False

# verbose output options
VERBOSE_NO_PYTHON = False
VERBOSE_PRINT_HEADER = False


def is_text_file(file_path: Path, blocksize: int = 512) -> bool:
    try:
        with file_path.open("rb") as f:
            block = f.read(blocksize)
        block.decode("utf-8")
        return True
    except UnicodeDecodeError:
        return False


def is_executable_wrapper(content: str) -> bool:
    """
    Detect if a Python file is a simple executable wrapper.

    These are typically short files (< 25 lines) that:
    1. Start with shebang #!/usr/bin/env python3
    2. Have a copyright header
    3. Import a main function from another module
    4. Call that main function in if __name__ == "__main__" block
    """
    lines = content.splitlines()

    # Must be reasonably short
    if len(lines) > 25:
        return False

    # Must start with python3 shebang
    if not lines or not lines[0].startswith("#!/usr/bin/env python3"):
        return False

    # Must have copyright header (look for "Copyright" in first few lines)
    has_copyright = any("Copyright" in line for line in lines[:6])
    if not has_copyright:
        return False

    # Must have import statement with "cmk" in it
    has_main_import = any("import" in line and "cmk" in line for line in lines)
    if not has_main_import:
        return False

    # Must have if __name__ == "__main__": block
    has_main_block = any('if __name__ == "__main__"' in line for line in lines)
    if not has_main_block:
        return False

    # Must call main() function in the main block
    has_main_call = any("main(" in line for line in lines)
    if not has_main_call:
        return False

    return True


def is_python_source(file_path: Path, content: str) -> bool:
    if re.match(r"^\s*#!.*python3", content):
        # starting with a shebang for Python 3
        # (that's a good starting point - these are definitely Python files)
        logger.debug("%s: shebang detected -> python", file_path)
        return True

    if not content.strip():
        # empty file -> no Python source
        if VERBOSE_NO_PYTHON:
            logger.debug("%s: empty file -> no python", file_path)
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
            logger.debug("%s: ast.parse + python keywords -> python", file_path)
            return True

        if VERBOSE_NO_PYTHON:
            logger.debug("%s: ast.parse OK, but no keywords", file_path)
        return False
    except SyntaxError:
        if VERBOSE_NO_PYTHON:
            logger.debug("%s: ast.parse failed -> no python", file_path)

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
] + ([r"doc/treasures/.*"] if IGNORE_TREASURES else [])

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


def test_python_files_have_py_extension(
    git_changes: GitChanges | None, summary_writer: SummaryWriter
) -> None:
    """
    Test to ensure all Python source files have a .py (or other allowed) extension.
    Scans for Python source files without allowed extension and reports them

    Configuration:
        * IGNORE_EXECUTABLE_WRAPPERS: When True (default), skips short executable
          wrapper files that just import and call a main() function from another module.
          These are typically legitimate executables that don't need .py extensions.

    this test can be executed as follows:
        * from the CI for changes of the change under review:
            pytest --git-changes=CHANGES_FILE
        * for local execution or testing:
            pytest --git-changes=LOCAL  # only check changed files
            pytest --test-all-files     # check all files in the repository
    """

    if git_changes:
        # Use git changes - only check added files (and possibly modified files)
        file_candidates = (
            list(git_changes.added | git_changes.modified)
            if INCLUDE_MODIFIED
            else list(git_changes.added)
        )
        logger.info("Using git changes - checking %d files", len(file_candidates))
        if git_changes.added:
            logger.info("Added files: %d", len(git_changes.added))
        if INCLUDE_MODIFIED and git_changes.modified:
            logger.info("Modified files: %d", len(git_changes.modified))
        if git_changes.removed:
            logger.info("Removed files: %d (not checked)", len(git_changes.removed))
    else:
        pytest.skip("No files supplied -- either run with or --git-changes or --test-all-files ")

    logger.info("Scanning %d files...", len(file_candidates))
    logger.info("Allowed Python extensions: %s", ", ".join(PYTHON_SUFFIXES))

    mismatches = []
    patterns_matched = set()
    # -------------------------------------------------------------
    # scan files
    # -------------------------------------------------------------
    base_dir: Path = repo_path()
    for file_path in file_candidates:
        logger.debug("Checking file: %s", file_path)
        if not file_path.is_file() or file_path.is_symlink():
            logger.debug("Skipping (not a file or is a symlink): %s", file_path)
            continue

        # -------------------------------------------------------------
        # Phase 1: sort out as many files by path/extension
        # -------------------------------------------------------------
        # Skip files that already have a .py extension or other non-python extensions
        if file_path.suffix in PYTHON_SUFFIXES or file_path.suffix in IGNORE_SUFFIXES:
            if CHECK_UNUSED_PATTERNS:
                patterns_matched.add(file_path.suffix)
            logger.debug("Skipping file (ignored extension): %s", file_path)
            continue

        rel_path = file_path.relative_to(base_dir)
        if any(re.match(pattern, str(rel_path)) for pattern in IGNORE_PATHS):
            if CHECK_UNUSED_PATTERNS:
                patterns_matched.update(
                    {pattern for pattern in IGNORE_PATHS if re.match(pattern, str(rel_path))}
                )
            logger.debug("Skipping file (ignored path): %s", file_path)
            continue

        # -------------------------------------------------------------
        # Phase 2: simple file content evaluation
        # -------------------------------------------------------------
        # Only consider text files.
        if not is_text_file(file_path):
            logger.debug("Skipping file (not a text file): %s", file_path)
            continue

        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception:
            logger.debug("Error reading file: %s", file_path)
            continue

        # -------------------------------------------------------------
        # Phase 3: evaluate complete content (parse python)
        # -------------------------------------------------------------
        # as this is more resource intensive, this should be at the end
        if is_python_source(rel_path, content):
            # Check if it's an executable wrapper and should be ignored
            if IGNORE_EXECUTABLE_WRAPPERS and is_executable_wrapper(content):
                logger.debug("Skipping executable wrapper file: %s", rel_path)
                continue
            # Record relative path for reporting.
            mismatches.append(str(rel_path))
            logger.debug("Found Python source file without .py extension: %s", rel_path)

            if VERBOSE_PRINT_HEADER:
                logger.info("%s has %d lines of Python source", rel_path, content.count("\n") + 1)
                logger.info("head -3 %s:\n%s\n", file_path, "\n".join(content.splitlines()[:3]))
        else:
            logger.debug("File is not a Python source file: %s", rel_path)

    # -------------------------------------------------------------
    # post-processing
    # -------------------------------------------------------------
    if CHECK_UNUSED_PATTERNS:
        ignore_paths_unused = [ignp for ignp in IGNORE_PATHS if ignp not in patterns_matched]
        ignore_suffixes_unused = [igns for igns in IGNORE_SUFFIXES if igns not in patterns_matched]

        if ignore_paths_unused:
            logger.info("unused in IGNORE_PATHS:")
            for pattern in ignore_paths_unused:
                logger.info(" - %s", pattern)
        else:
            logger.info("OK: All entries from IGNORE_PATHS are used.")

        if ignore_suffixes_unused:
            logger.info("unused in IGNORE_SUFFIXES:")
            for suffix in ignore_suffixes_unused:
                logger.info(" - %s", suffix)
        else:
            logger.info("OK: All entries from IGNORE_SUFFIXES are used.")

    # -------------------------------------------------------------
    # report findings and write summary
    # -------------------------------------------------------------
    if mismatches:
        msg = (
            f"Found {len(mismatches)} Python source file(s) without a '.py' extension:\n"
            + "See https://wiki.lan.checkmk.net/x/jStSCQ\n"
            + "\n".join(f" -- {rel_path}" for rel_path in sorted(mismatches))
        )
        summary_writer.write_summary(msg)
        pytest.fail(msg)
    else:
        msg = f"No mismatches found in {len(file_candidates)} files."
        summary_writer.write_summary(msg)
