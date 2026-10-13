#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path
from typing import Protocol

from git.objects.blob import Blob
from git.objects.tree import Tree

type RepoFiles = Path | Tree
"""The root of a working copy, or the tree of a git commit"""


def read_repo_file(repo: RepoFiles, path: str) -> bytes | None:
    """The content of the file at path relative to the repository root, None if it is missing"""
    if isinstance(repo, Path):
        try:
            return (repo / path).read_bytes()
        except FileNotFoundError:
            return None
    try:
        blob = repo[path]
    except KeyError:
        return None
    return blob.data_stream.stream.read() if isinstance(blob, Blob) else None


class Flavor(Protocol):
    """The repository specific parts of handling werks"""

    @property
    def name(self) -> str: ...

    @property
    def version_regex(self) -> str:
        """Valid versions of a werk"""
        ...

    @property
    def branch_regex(self) -> str:
        """Branches collected for the website"""
        ...

    def read_current_version(self, repo: RepoFiles) -> str | None:
        """The version a werk without a version will be released with"""
        ...

    def cleanup_branch_name(self, branch_name: str) -> str:
        """The release a branch belongs to"""
        ...

    def adapt_werk_string(self, werk_string: str, werk_id: int) -> str:
        """Fixes up werks that are broken on released branches"""
        ...


def current_version(flavor: Flavor, repo_root: Path) -> str:
    if (version := flavor.read_current_version(repo_root)) is None:
        raise RuntimeError(f"Could not determine the current version of {repo_root}")
    return version
