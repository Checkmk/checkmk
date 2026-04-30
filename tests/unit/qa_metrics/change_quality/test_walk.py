#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""End-to-end test of walk.py against a fixture git repo built in tmp_path."""

from __future__ import annotations

import os
import re
import subprocess
from datetime import date, datetime, UTC
from pathlib import Path

import pytest

from tests.qa_metrics.change_quality.walk import walk_werk_adds

_WERK_15155 = """\
Title: sap_hana_status: Handle WARNING status correctly
Class: fix
Compatible: compat
Component: checks
Date: 1678271797
Edition: cre
Knowledge: doc
Level: 1
Version: 2.3.0b1

Body.
"""

_WERK_15156 = """\
Title: another fix landing in the same commit
Class: fix
Compatible: compat
Component: checks
Date: 1678271797
Edition: cre
Knowledge: doc
Level: 1
Version: 2.3.0b1

Body.
"""


def _git_env() -> dict[str, str]:
    return {
        "PATH": os.environ.get("PATH", ""),
        "GIT_AUTHOR_NAME": "Test",
        "GIT_AUTHOR_EMAIL": "test@example.com",
        "GIT_COMMITTER_NAME": "Test",
        "GIT_COMMITTER_EMAIL": "test@example.com",
        "GIT_AUTHOR_DATE": "2023-03-08T12:00:00+0000",
        "GIT_COMMITTER_DATE": "2023-03-08T12:00:00+0000",
    }


@pytest.fixture
def fixture_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()

    subprocess.run(
        ["git", "init", "-q", "-b", "master"],
        cwd=repo,
        check=True,
        capture_output=True,
        env=_git_env(),
    )

    werks_dir = repo / ".werks"
    werks_dir.mkdir()
    (werks_dir / "15155.md").write_text(_WERK_15155)
    (werks_dir / "15156.md").write_text(_WERK_15156)
    (repo / "cmk" / "plugins" / "sap_hana" / "agent_based").mkdir(parents=True)
    (repo / "cmk" / "plugins" / "sap_hana" / "agent_based" / "sap_hana_status.py").write_text(
        "# fix\n"
    )
    (repo / "tests" / "unit" / "cmk" / "plugins" / "sap_hana").mkdir(parents=True)
    (
        repo / "tests" / "unit" / "cmk" / "plugins" / "sap_hana" / "test_sap_hana_status.py"
    ).write_text("def test_x(): pass\n")

    subprocess.run(
        ["git", "add", "."],
        cwd=repo,
        check=True,
        capture_output=True,
        env=_git_env(),
    )
    subprocess.run(
        ["git", "commit", "-m", "fix sap_hana_status\n\nChange-Id: I0123456789abcdef0123"],
        cwd=repo,
        check=True,
        capture_output=True,
        env=_git_env(),
    )
    return repo


def test_walk_yields_one_event_per_added_werk(fixture_repo: Path) -> None:
    events = list(walk_werk_adds(fixture_repo))
    werk_ids = sorted(e.werk_id for e in events)
    assert werk_ids == [15155, 15156]


def test_walk_attaches_full_files_changed(fixture_repo: Path) -> None:
    events = list(walk_werk_adds(fixture_repo))
    assert events
    files = events[0].commit.files_changed
    assert ".werks/15155.md" in files
    assert ".werks/15156.md" in files
    assert any("sap_hana_status.py" in f for f in files)
    assert any("test_sap_hana_status.py" in f for f in files)


def test_walk_extracts_commit_metadata(fixture_repo: Path) -> None:
    events = list(walk_werk_adds(fixture_repo))
    assert events
    commit = events[0].commit
    assert re.fullmatch(r"[0-9a-f]{40}", commit.sha) is not None
    assert commit.author_email == "test@example.com"
    assert commit.subject == "fix sap_hana_status"
    assert commit.gerrit_change_id == "I0123456789abcdef0123"
    assert commit.commit_time == datetime(2023, 3, 8, 12, 0, tzinfo=UTC)


def test_walk_attaches_same_commit_to_co_authored_werks(fixture_repo: Path) -> None:
    """Two werks added by one commit must report equal CommitInfo (same SHA, etc.)."""
    events = list(walk_werk_adds(fixture_repo))
    assert len(events) == 2
    assert events[0].commit == events[1].commit


def test_walk_filters_by_until(fixture_repo: Path) -> None:
    events = list(walk_werk_adds(fixture_repo, until=date(2020, 12, 31)))
    assert events == []


def test_walk_filters_by_since(fixture_repo: Path) -> None:
    events = list(walk_werk_adds(fixture_repo, since=date(2099, 1, 1)))
    assert events == []


_WERK_OLDER = """\
Title: older fix
Class: fix
Compatible: compat
Component: checks
Date: 1577836800
Edition: cre
Knowledge: doc
Level: 1
Version: 2.0.0b1

Body.
"""

_WERK_NEWER = """\
Title: newer fix
Class: fix
Compatible: compat
Component: checks
Date: 1672531200
Edition: cre
Knowledge: doc
Level: 1
Version: 2.4.0b1

Body.
"""


def _git_env_at(when: str) -> dict[str, str]:
    return {**_git_env(), "GIT_AUTHOR_DATE": when, "GIT_COMMITTER_DATE": when}


@pytest.fixture
def two_commit_repo(tmp_path: Path) -> Path:
    """Two commits at distinct dates: an older werk, then a newer one."""
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(
        ["git", "init", "-q", "-b", "master"],
        cwd=repo,
        check=True,
        capture_output=True,
        env=_git_env(),
    )
    werks_dir = repo / ".werks"
    werks_dir.mkdir()

    (werks_dir / "10000.md").write_text(_WERK_OLDER)
    subprocess.run(
        ["git", "add", "."],
        cwd=repo,
        check=True,
        capture_output=True,
        env=_git_env_at("2020-01-01T00:00:00+0000"),
    )
    subprocess.run(
        ["git", "commit", "-m", "older fix"],
        cwd=repo,
        check=True,
        capture_output=True,
        env=_git_env_at("2020-01-01T00:00:00+0000"),
    )

    (werks_dir / "20000.md").write_text(_WERK_NEWER)
    subprocess.run(
        ["git", "add", "."],
        cwd=repo,
        check=True,
        capture_output=True,
        env=_git_env_at("2023-01-01T00:00:00+0000"),
    )
    subprocess.run(
        ["git", "commit", "-m", "newer fix"],
        cwd=repo,
        check=True,
        capture_output=True,
        env=_git_env_at("2023-01-01T00:00:00+0000"),
    )
    return repo


def test_walk_yields_oldest_commit_first(two_commit_repo: Path) -> None:
    events = list(walk_werk_adds(two_commit_repo))
    assert [e.werk_id for e in events] == [10000, 20000]
    assert events[0].commit.commit_time < events[1].commit.commit_time
