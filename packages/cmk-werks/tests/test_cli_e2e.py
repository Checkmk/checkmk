#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import os
import subprocess
from pathlib import Path
from unittest import mock

from git.repo import Repo

from cmk.werks.cli import Stash


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
editions = [("cre", "CRE")]
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


def prepare_reserved_ids(home: Path, ids: list[int]) -> Path:
    secret_file = home / ".config/cmk-werks/secret"
    secret_file.parent.mkdir(parents=True)
    secret_file.write_text("fake-secret", encoding="utf-8")
    stash_file = home / ".local/state/cmk-werks/reserved-ids"
    stash_file.parent.mkdir(parents=True)
    stash_file.write_text(Stash(ids=ids).model_dump_json(by_alias=True))
    return stash_file


def create_werk(*, title: str) -> None:
    change = Path(f"some_change{title}")
    change.write_text("smth")
    repo = Repo(".")
    repo.index.add([str(change)])
    p = subprocess.Popen(["python", "-m", "cmk.werks", "new"], stdin=subprocess.PIPE)
    stdout, stderr = p.communicate(title.encode() + b"\nf\nc\nc\n1\nc\n")
    print(stdout, stderr)
    p.wait()


def latest_commit_subject(repo_path: Path) -> str:
    repo = Repo(repo_path)
    message = repo.head.commit.message
    if message is None:
        raise RuntimeError("message is none")
    if isinstance(message, bytes):
        message = message.decode("utf-8")
    return message.split("\n")[0]


def test_reserve_ids_and_create_werk(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    stash_file = prepare_reserved_ids(home, [11111, 11112, 11113])

    repo_path = tmp_path / "repo"
    initialize_werks_project(repo_path, first_free=11_111)

    with mock.patch.dict(os.environ, {"HOME": str(home), "EDITOR": "true"}):
        os.chdir(repo_path)
        create_werk(title="some_title")

    assert latest_commit_subject(repo_path) == "11111 some_title"
    assert "some_title" in (repo_path / ".werks/11111.md").read_text()
    remaining = json.loads(stash_file.read_text())["ids"]
    assert remaining == [11112, 11113]


def test_commit_config(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    stash_file = prepare_reserved_ids(home, [1111111, 1111112])
    assert stash_file.exists()

    repo_path = tmp_path / "repo"
    initialize_werks_project(repo_path, first_free=1_111_111, commit=False)
    assert latest_commit_subject(repo_path) == "initial commit"

    with mock.patch.dict(os.environ, {"HOME": str(home), "EDITOR": "true"}):
        os.chdir(repo_path)
        create_werk(title="some_cloud_title")

    assert latest_commit_subject(repo_path) == "initial commit"
    assert "some_cloud_title" in (repo_path / ".werks/1111111.md").read_text()
