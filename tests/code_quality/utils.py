#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
import subprocess
from collections.abc import Collection
from dataclasses import dataclass
from pathlib import Path
from typing import NamedTuple

from tests.testlib.common.repo import repo_path

logger = logging.getLogger(__name__)


class ChangedFiles(NamedTuple):
    test_all_files: bool
    file_paths: Collection[Path]

    def is_changed(self, path: Path) -> bool:
        return self.test_all_files or path in self.file_paths


@dataclass
class GitChanges:
    # TODO: merge this with ChangedFiles
    added: set[Path]
    modified: set[Path]
    removed: set[Path]

    def is_added(self, path: Path) -> bool:
        return path in self.added

    def is_modified(self, path: Path) -> bool:
        return path in self.modified

    def is_removed(self, path: Path) -> bool:
        return path in self.removed

    def is_changed(self, path: Path) -> bool:
        return path in self.added or path in self.modified or path in self.removed

    @classmethod
    def from_git_changes_file(
        cls, file_path_or_local: Path | str, test_all_files: bool = False
    ) -> "GitChanges":
        """Parse a git diff-tree --name-status output file and create GitChanges instance.

        Args:
            file_path_or_local: Either a Path to a git changes file, or the string "LOCAL"
                               to get current local changes (staged, unstaged, and untracked files),
                               or "" (which needs to be combined with test_all_files=True)
            test_all_files: If True, get all files from git ls-files and put them in added set.
        """
        added = set()
        modified = set()
        removed = set()
        base_dir = repo_path()

        if file_path_or_local == "LOCAL":
            logger.info("Getting local git changes")
            # Get current local changes (staged, unstaged, and untracked)
            try:
                # First get staged changes
                staged_result = subprocess.run(
                    ["git", "diff", "--name-status", "--cached"],
                    capture_output=True,
                    text=True,
                    check=True,
                    cwd=base_dir,
                )
                # Then get unstaged changes
                unstaged_result = subprocess.run(
                    ["git", "diff", "--name-status"],
                    capture_output=True,
                    text=True,
                    check=True,
                    cwd=base_dir,
                )
                # Get untracked files using git status --porcelain
                untracked_result = subprocess.run(
                    ["git", "status", "--porcelain", "--untracked-files=all"],
                    capture_output=True,
                    text=True,
                    check=True,
                    cwd=base_dir,
                )
                # Process untracked files (those with ?? status) and convert to diff format
                untracked_content = ""
                for line in untracked_result.stdout.split("\n"):
                    if line.startswith("??"):
                        file_path = line[3:]  # Remove "?? " prefix
                        untracked_content += f"A\t{file_path}\n"

                # Combine all changes
                content = (
                    staged_result.stdout + unstaged_result.stdout + untracked_content
                ).strip()
                logger.debug(
                    "Local git changes:\nStaged:\n%s\nUnstaged:\n%s\nUntracked:\n%s",
                    staged_result.stdout,
                    unstaged_result.stdout,
                    untracked_content,
                )
            except subprocess.CalledProcessError:
                # If no changes, return empty sets
                content = ""
        elif file_path_or_local != "":
            logger.info("Reading git changes from file: %s", file_path_or_local)
            file_path_obj = Path(file_path_or_local)
            content = file_path_obj.read_text().strip() if file_path_obj.exists() else ""
        else:
            content = ""

        if content:
            for line in content.split("\n"):
                if not line.strip():
                    continue
                parts = line.split("\t", 1)
                if len(parts) != 2:
                    continue
                status, file_path_str = parts

                if status == "A":
                    file_path_obj = base_dir / file_path_str
                    added.add(file_path_obj)
                elif status == "M":
                    file_path_obj = base_dir / file_path_str
                    modified.add(file_path_obj)
                elif status == "D":
                    file_path_obj = base_dir / file_path_str
                    removed.add(file_path_obj)
                elif status == "C":
                    # C: copied - treat as added
                    file_path_obj = base_dir / file_path_str
                    added.add(file_path_obj)
                elif status.startswith("R"):
                    # R: renamed - format is "old_path    new_path"
                    # Add old_path to removed and new_path to added
                    if "\t" in file_path_str:
                        old_path, new_path = file_path_str.split("\t", 1)
                        old_file_path_obj = base_dir / old_path
                        new_file_path_obj = base_dir / new_path
                        removed.add(old_file_path_obj)
                        added.add(new_file_path_obj)
                    else:
                        # Fallback if format is unexpected - treat as added only
                        file_path_obj = base_dir / file_path_str
                        added.add(file_path_obj)
                elif status == "T":
                    # T: typechange - treat as modified
                    file_path_obj = base_dir / file_path_str
                    modified.add(file_path_obj)
                else:
                    # Unknown status - map to added and log warning
                    file_path_obj = base_dir / file_path_str
                    logger.warning(
                        "Unknown git status code '%s' for file %s, treating as added",
                        status,
                        file_path_str,
                    )
                    added.add(file_path_obj)
        else:
            logger.info("No changes detected")

        # If test_all_files is True, add all files from git ls-files to the added set
        if test_all_files:
            logger.info("Getting all files from git ls-files for test-all-files mode")
            try:
                result = subprocess.run(
                    ["git", "ls-files"], capture_output=True, text=True, cwd=base_dir, check=True
                )
                all_files = [base_dir / f for f in result.stdout.strip().split("\n") if f.strip()]
                added.update(all_files)
                logger.info(
                    "%d files have been simulated as being added from git ls-files", len(all_files)
                )
            except subprocess.CalledProcessError as e:
                logger.error("Failed to get files from git ls-files: %s", e)

        return cls(added=added, modified=modified, removed=removed)


class SummaryWriter:
    """Class for writing test summaries to both logging and result files."""

    def __init__(
        self, result_out_file: str | None = None, test_module: str = "", test_class: str = ""
    ):
        self.result_out_file = result_out_file
        self.test_module = test_module
        self.test_class = test_class
        self.logger = logging.getLogger(__name__)

    def write_summary(self, summary: str) -> None:
        """
        Write a multiline summary string to both logging.info and result output file.

        Args:
            summary: The multiline summary string to write
        """
        # Prepend test module and class information
        header = f"== {self.test_module}::{self.test_class} =="
        full_summary = f"{header}\n{summary}"

        # Always write to logging.info
        self.logger.info(full_summary)

        # Write to result file if specified
        if self.result_out_file:
            self._write_to_file(full_summary)

    def _write_to_file(self, content: str) -> None:
        """Write content to the result output file, ensuring the file and directory exist."""
        if not self.result_out_file:
            return
        try:
            result_path = Path(self.result_out_file)
            result_path.parent.mkdir(parents=True, exist_ok=True)

            with result_path.open("w", encoding="utf-8") as f:
                f.write(content)
                f.write("\n")

            self.logger.debug("Results written to: %s", self.result_out_file)
        except Exception as e:
            self.logger.warning("Failed to write results to %s: %s", self.result_out_file, e)
