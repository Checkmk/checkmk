#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"

import json
import os
import subprocess
import sys
from pathlib import Path
from unittest import mock

from git.repo import Repo

from cmk.werks.schemas.werk import Stash


def initialize_werks_project(
    path: Path,
    *,
    first_free: int,
    commit: bool = True,
) -> Repo:
    path.mkdir()
    werks = path / ".werks"
    werks.mkdir()
    (werks / "first_free").write_text(f"{first_free}\n")
    commit_option = ""
    if commit is False:
        commit_option = "create_commit = False"
    (werks / "config").write_text(f"""
editions = [("community", "COMMUNITY")]
components = [("ccc", "CCC")]
edition_components = {"{}"}
classes = [
    ("feature", "New feature", ""),
    ("fix", "Bug fix", "FIX"),
    ("security", "Security fix", "SEC"),
]
levels = [
    ("1", "Trivial change"),
    ("2", "Prominent change"),
    ("3", "Major change"),
]
compatible = [
    ("compat", "Compatible"),
    ("incomp", "Incompatible"),
]
online_url = "https://checkmk.com/werk/%d"
current_version = "0.1.0"
{commit_option}
    """)
    Repo.init(path)
    repo = Repo(path)
    (path / "README.md").write_text("# repo")
    cw = repo.config_writer()
    cw.set_value("user", "email", "git@example.com")
    cw.set_value("user", "name", "git")
    cw.release()
    repo.index.add(["README.md", ".werks/first_free"])
    repo.index.commit("initial commit")
    return repo


def call_output(*args: str, home: Path, cwd: Path) -> tuple[int, str]:
    completed = subprocess.run(
        [sys.executable, "-m", "cmk.werks", *args],
        capture_output=True,
        text=True,
        check=False,
        cwd=cwd,
        env=os.environ | {"HOME": str(home)},
    )
    return completed.returncode, completed.stdout


def write_secret(home: Path) -> Path:
    secret = home / ".config/cmk-werks/secret"
    secret.parent.mkdir(parents=True, exist_ok=True)
    secret.write_text("fake-secret", encoding="utf-8")
    return secret


def read_log(home: Path) -> list[str]:
    # every line is "<timestamp, logger and level> <the entry itself>"
    log_file = home / ".local/state/cmk-werks/werk-ids.log"
    return [line.split("[INFO] ", 1)[1] for line in log_file.read_text().splitlines()]


def write_stash(home: Path, ids: list[int]) -> Path:
    stash_file = home / ".local/state/cmk-werks/reserved-ids"
    stash_file.parent.mkdir(parents=True, exist_ok=True)
    stash_file.write_text(Stash(ids=ids).model_dump_json(by_alias=True))
    return stash_file


def latest_commit_subject(repo_path: Path) -> str:
    repo = Repo(repo_path)
    message = repo.head.commit.message
    if message is None:  # type: ignore[comparison-overlap]
        raise RuntimeError("message is none")
    if isinstance(message, bytes):
        message = message.decode("utf-8")
    return message.split("\n")[0]


def _create_werk(home: Path, repo_path: Path, title: bytes = b"some_title") -> None:
    with mock.patch.dict(os.environ, {"HOME": str(home), "EDITOR": "true"}):
        os.chdir(repo_path)
        p = subprocess.Popen(
            [sys.executable, "-m", "cmk.werks", "new"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        p.communicate(input=title + b"\nf\nc\nc\n1\nc\nk\n", timeout=30)


def test_reserve_ids_and_create_werk(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    write_secret(home)
    stash_file = write_stash(home, [11111, 11112, 11113])

    repo_path = tmp_path / "repo"
    initialize_werks_project(repo_path, first_free=11_111)

    _create_werk(home, repo_path)

    assert latest_commit_subject(repo_path) == "11111 some_title"
    assert "some_title" in (repo_path / ".werks/11111.md").read_text()
    remaining = json.loads(stash_file.read_text())["ids"]
    assert remaining == [11112, 11113]


def test_create_werk_logs_the_consumed_id(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    write_secret(home)
    write_stash(home, [11111, 11112])

    repo_path = tmp_path / "repo"
    initialize_werks_project(repo_path, first_free=11_111)

    _create_werk(home, repo_path)

    werk_file = (repo_path / ".werks/11111.md").resolve()
    assert read_log(home)[-1] == f"launcher:bazel, action:new, werk ID:11111, werk file:{werk_file}"


def test_delete_werk_returns_the_id_to_the_stash(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    write_secret(home)
    stash_file = write_stash(home, [11111, 11112])

    repo_path = tmp_path / "repo"
    initialize_werks_project(repo_path, first_free=11_111)
    _create_werk(home, repo_path)

    call_output("delete", "11111", home=home, cwd=repo_path)

    assert json.loads(stash_file.read_text())["ids"] == [11111, 11112]


def test_delete_werk_logs_the_returned_id(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    write_secret(home)
    write_stash(home, [11111, 11112])

    repo_path = tmp_path / "repo"
    initialize_werks_project(repo_path, first_free=11_111)
    _create_werk(home, repo_path)

    call_output("delete", "11111", home=home, cwd=repo_path)

    assert read_log(home)[-1] == "launcher:bazel, action:delete, werk ID:11111"


def test_commit_config(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()

    repo_path = tmp_path / "repo"
    initialize_werks_project(repo_path, first_free=1_111_111, commit=False)
    assert latest_commit_subject(repo_path) == "initial commit"

    write_secret(home)
    write_stash(home, [1111111, 1111112])

    _create_werk(home, repo_path, title=b"some_cloud_title")

    assert latest_commit_subject(repo_path) == "initial commit"
    assert "some_cloud_title" in (repo_path / ".werks/1111111.md").read_text()
