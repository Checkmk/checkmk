#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import os
import subprocess
import sys
from pathlib import Path
from unittest import mock

from git.repo import Repo

from cmk.werks.tool.cli.stash import Stash


def initialize_werks_project(
    path: Path,
    *,
    first_free: int,
    commit: bool = True,
    werk_ids_server_url: str | None = None,
) -> Repo:
    path.mkdir()
    werks = path / ".werks"
    werks.mkdir()
    (werks / "first_free").write_text(f"{first_free}\n")
    extra_options = []
    if commit is False:
        extra_options.append("create_commit = False")
    if werk_ids_server_url is not None:
        extra_options.append(f'werk_ids_server_url = "{werk_ids_server_url}"')
    extra_config = "\n".join(extra_options)
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
    ("yes", "Compatible"),
    ("no", "Incompatible"),
]
online_url = "https://checkmk.com/werk/%d"
current_version = "0.1.0"
{extra_config}
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
    # HOME and the working directory are handed to the subprocess, so the test process
    # neither has to be patched nor left in a different directory
    completed = subprocess.run(
        ["python", "-m", "cmk.werks.tool", *args],
        capture_output=True,
        text=True,
        check=False,
        cwd=cwd,
        env=os.environ | {"HOME": str(home)},
    )
    return completed.returncode, completed.stdout


def write_secret(home: Path, mode: int = 0o600) -> Path:
    secret = home / ".config/cmk-werks/secret"
    secret.parent.mkdir(parents=True, exist_ok=True)
    secret.write_text("s3cret")
    secret.chmod(mode)
    return secret


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


def test_create_werk_consumes_a_reserved_id(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    write_secret(home)
    stash_file = write_stash(home, [11111, 11112, 11113])

    repo_path = tmp_path / "repo"
    initialize_werks_project(repo_path, first_free=11_111)

    with mock.patch.dict(os.environ, {"HOME": str(home), "EDITOR": "true"}):
        os.chdir(repo_path)
        p = subprocess.Popen(
            [sys.executable, "-m", "cmk.werks.tool", "new"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        p.communicate(input=b"some_title\nf\nc\nc\n1\nc\nk\n", timeout=30)

    assert latest_commit_subject(repo_path) == "11111 some_title"
    assert "some_title" in (repo_path / ".werks/11111.md").read_text()
    remaining = json.loads(stash_file.read_text())["ids"]
    assert remaining == [11112, 11113]


def test_commit_config(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()

    repo_path = tmp_path / "repo"
    initialize_werks_project(repo_path, first_free=1_111_111, commit=False)
    assert latest_commit_subject(repo_path) == "initial commit"

    write_secret(home)
    write_stash(home, [1111111, 1111112])

    with mock.patch.dict(os.environ, {"HOME": str(home), "EDITOR": "true"}):
        os.chdir(repo_path)
        p = subprocess.Popen(
            [sys.executable, "-m", "cmk.werks.tool", "new"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        p.communicate(input=b"some_cloud_title\nf\nc\nc\n1\nc\nk\n", timeout=30)

    assert latest_commit_subject(repo_path) == "initial commit"
    assert "some_cloud_title" in (repo_path / ".werks/1111111.md").read_text()


def test_status_reports_a_missing_secret(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    repo_path = tmp_path / "repo_cmk"
    initialize_werks_project(repo_path, first_free=11_111)

    returncode, output = call_output("status", home=home, cwd=repo_path)

    assert returncode == 1
    assert "WERK IDS" in output
    # without a secret there is nothing to authenticate with, so no request is made
    assert "not checked, no secret" in output
    assert "werk init" in output
    # the output is meant to be pasted into tickets and chats
    assert str(home) not in output
    assert "$HOME/.config/cmk-werks/secret" in output


def test_ids_runs_status(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    repo_path = tmp_path / "repo_cmk"
    initialize_werks_project(repo_path, first_free=11_111)

    # invocations from the days of manual reservation, arguments and all, end up in 'status'
    returncode, output = call_output("ids", "10", "--no-commit", home=home, cwd=repo_path)

    assert returncode == 1
    assert "WERK IDS" in output


def test_status_reports_an_unreachable_server(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    repo_path = tmp_path / "repo_cmk"
    # port 1 refuses immediately, so the probe neither hangs nor depends on the VPN
    initialize_werks_project(
        repo_path,
        first_free=11_111,
        werk_ids_server_url="http://127.0.0.1:1",
    )
    write_secret(home)

    returncode, output = call_output("status", home=home, cwd=repo_path)

    assert returncode == 1
    assert "unreachable" in output
    assert "none reserved and the server is unavailable" in output


def test_status_reports_both_stash_files_instead_of_bailing_out(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    repo_path = tmp_path / "repo_cmk"
    initialize_werks_project(
        repo_path,
        first_free=11_111,
        werk_ids_server_url="http://127.0.0.1:1",
    )
    write_secret(home)
    (home / ".cmk-werk-ids").write_text(json.dumps({"ids_by_project": {"cmk": [11_111]}}))
    write_stash(home, [11_112])

    # every other command bails out in this state; status still prints the whole picture
    returncode, output = call_output("status", home=home, cwd=repo_path)

    assert returncode == 1
    assert "two stash files" in output
    assert "exists next to the current stash file" in output


def test_status_exits_zero_when_there_is_nothing_to_report(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    repo_path = tmp_path / "repo_cmk"
    initialize_werks_project(
        repo_path,
        first_free=11_111,
        werk_ids_server_url="http://127.0.0.1:1",
    )
    write_secret(home)
    write_stash(home, [11_111])

    # an unreachable server is no problem as long as there are reserved IDs left
    returncode, output = call_output("status", home=home, cwd=repo_path)

    assert returncode == 0
    assert "✓ none found" in output


def test_status_exits_zero_for_a_setup_that_is_not_migrated_yet(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    repo_path = tmp_path / "repo_cmk"
    initialize_werks_project(
        repo_path,
        first_free=11_111,
        werk_ids_server_url="http://127.0.0.1:1",
    )
    (home / ".cmk-werk-ids").write_text(json.dumps({"ids_by_project": {"cmk": [11_111]}}))

    returncode, output = call_output("status", "--json", home=home, cwd=repo_path)

    document = json.loads(output)
    assert returncode == 0
    assert document["setup"] == {"state": "legacy", "active_stash": "legacy_stash"}
    assert [problem["severity"] for problem in document["problems"]] == ["warning"]


def test_status_json_is_machine_readable(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    repo_path = tmp_path / "repo_cmk"
    initialize_werks_project(
        repo_path,
        first_free=11_111,
        werk_ids_server_url="http://127.0.0.1:1",
    )
    write_secret(home)
    write_stash(home, [11_111])

    returncode, output = call_output("status", "--json", home=home, cwd=repo_path)

    # stdout must be nothing but the document, so `werk status --json | jq` works
    document = json.loads(output)
    assert returncode == 0
    assert document["schema_version"] == 1
    assert document["setup"] == {"state": "server", "active_stash": "reserved_ids"}
    assert document["server"]["status"] == "unreachable"
    assert document["reserved_ids"]["count"] == 1
    assert document["reserved_ids"]["next_id"] == 11_111
    assert document["problems"] == []


def test_status_json_reports_problems_and_exits_non_zero(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    repo_path = tmp_path / "repo_cmk"
    initialize_werks_project(
        repo_path,
        first_free=11_111,
        werk_ids_server_url="http://127.0.0.1:1",
    )
    write_secret(home, mode=0o644)

    returncode, output = call_output("status", "--json", home=home, cwd=repo_path)

    document = json.loads(output)
    assert returncode == 1
    items = [problem["item"] for problem in document["problems"]]
    assert "secret" in items
    # the fix is meant to be copied, and it carries a path
    assert document["problems"][0]["fix"] == "chmod 600 $HOME/.config/cmk-werks/secret"
    # every problem points at a key of the document itself
    for item in items:
        assert item in document
