#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import subprocess
from pathlib import Path
from typing import NamedTuple

import pytest
from register import cmd_result, cmk_branch, commit_id, split_source_name


@pytest.mark.parametrize(
    "source, expected",
    [
        pytest.param(
            "artifacts.lan.tribe29.com:4000/debian:latest",
            ("artifacts.lan.tribe29.com:4000", "debian", ["latest"]),
            id="registry and tag",
        ),
        pytest.param("debian:buster-slim", ("", "debian", ["buster-slim"]), id="tag only"),
        pytest.param("debian", ("", "debian", ["latest"]), id="defaults to latest"),
        pytest.param(
            "artifacts.lan.tribe29.com:4000/hadolint/hadolint",
            ("artifacts.lan.tribe29.com:4000/hadolint", "hadolint", ["latest"]),
            id="nested repository",
        ),
    ],
)
def test_source_name_is_split_into_registry_image_and_tags(
    source: str, expected: tuple[str, str, list[str]]
) -> None:
    assert split_source_name(source) == expected


def test_cmd_result_drops_empty_lines() -> None:
    assert cmd_result("printf 'a\\n\\nb\\n'") == ["a", "b"]


class _GitRepo(NamedTuple):
    path: Path
    head: str
    """The full hash of the checked out commit"""


@pytest.fixture(name="git_repo")
def fixture_git_repo(tmp_path: Path) -> _GitRepo:
    """A repository whose local commit sits on top of origin/2.4.0, one commit off master:

        base -- on 2.4.0 -- local (HEAD)
          \\
           origin/master, origin/2.5.0, origin/2.3.0, ...
    """

    def git(*args: str) -> str:
        return subprocess.run(
            ["git", "-C", str(tmp_path), *args], check=True, capture_output=True, text=True
        ).stdout.strip()

    def commit(message: str) -> None:
        git(
            "-c",
            "user.name=t",
            "-c",
            "user.email=t@example.com",
            "commit",
            "-q",
            "--allow-empty",
            "-m",
            message,
        )

    git("init", "-q", "-b", "master")
    git("config", "core.abbrev", "7")
    commit("base")
    for branch in ("master", "2.5.0", "2.3.0", "2.2.0", "2.1.0", "2.0.0", "1.6.0", "1.5.0"):
        git("update-ref", f"refs/remotes/origin/{branch}", "HEAD")
    commit("on 2.4.0")
    git("update-ref", "refs/remotes/origin/2.4.0", "HEAD")
    commit("local")
    return _GitRepo(tmp_path, git("rev-parse", "HEAD"))


def test_commit_id_is_the_abbreviated_head_hash(git_repo: _GitRepo) -> None:
    assert commit_id(str(git_repo.path)) == git_repo.head[:7]


def test_cmk_branch_is_the_closest_upstream_branch(git_repo: _GitRepo) -> None:
    assert cmk_branch(str(git_repo.path)) == "2.4.0"
