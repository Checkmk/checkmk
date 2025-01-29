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


def initialize_werks_project(path: Path, *, project: str, first_free: int) -> Repo:
    path.mkdir()
    werks = path / ".werks"
    werks.mkdir()
    (werks / "first_free").write_text(f"{first_free}\n")
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
project = "{project}"
current_version = "0.1.0"
    """)
    Repo.init(path)
    repo = Repo(path)
    (path / "README.md").write_text(f"# repo {project}")
    cw = repo.config_writer()
    cw.set_value("user", "email", "git@example.com")
    cw.set_value("user", "name", "git")
    cw.release()
    repo.index.add(["README.md", ".werks/first_free"])
    repo.index.commit("initial commit")
    repo.create_remote("origin", "some-url/check_mk")
    repo.create_head("master")

    return repo


def call(*args: str) -> None:
    # we can not call main directly, because the script was not created with that in mind
    # for example we have very sticky caches
    subprocess.check_call(["python", "-m", "cmk.werks.cli", *args])


def create_werk(*, title: str) -> None:
    change = Path(f"some_change{title}")
    change.write_text("smth")
    repo = Repo(".")
    repo.index.add([str(change)])
    p = subprocess.Popen(["python", "-m", "cmk.werks.cli", "new"], stdin=subprocess.PIPE)
    stdout, stderr = p.communicate(title.encode() + b"\nf\nc\nc\n1\nc\n")
    print(stdout, stderr)
    p.wait()


def test_reserve_ids_and_create_werk(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()

    def read_reserved_werks():
        return json.loads((home / ".cmk-werk-ids").read_text().strip())["ids_by_project"]

    cmk_repo_path = tmp_path / "repo_cmk"
    cloudmk_repo_path = tmp_path / "repo_cloudmk"

    initialize_werks_project(cmk_repo_path, project="cmk", first_free=11_111)
    initialize_werks_project(cloudmk_repo_path, project="cloudmk", first_free=1_111_111)

    with mock.patch.dict(os.environ, {"HOME": str(home), "EDITOR": "true"}):
        os.chdir(cmk_repo_path)
        call("ids", "5")
        assert (cmk_repo_path / ".werks/first_free").read_text().strip() == "11116"
        assert read_reserved_werks() == {
            "cmk": [11111, 11112, 11113, 11114, 11115],
        }

        os.chdir(cloudmk_repo_path)
        call("ids", "2")
        assert (cloudmk_repo_path / ".werks/first_free").read_text().strip() == "1111113"
        assert read_reserved_werks() == {
            "cmk": [11111, 11112, 11113, 11114, 11115],
            "cloudmk": [1111111, 1111112],
        }

        os.chdir(cmk_repo_path)
        create_werk(title="some_title")
        assert "some_title" in (cmk_repo_path / ".werks/11111").read_text()
        assert read_reserved_werks() == {
            "cmk": [11112, 11113, 11114, 11115],
            "cloudmk": [1111111, 1111112],
        }

        os.chdir(cloudmk_repo_path)
        create_werk(title="some_cloud_title")
        assert "some_cloud_title" in (cloudmk_repo_path / ".werks/1111111").read_text()
        assert read_reserved_werks() == {
            "cmk": [11112, 11113, 11114, 11115],
            "cloudmk": [1111112],
        }
