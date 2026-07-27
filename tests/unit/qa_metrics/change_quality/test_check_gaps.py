#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import subprocess
from collections.abc import Callable
from types import SimpleNamespace

import psycopg
import pytest
from psycopg import errors as psycopg_errors

from cmk.werks.tool.models import Class
from tests.qa_metrics.change_quality import check_gaps, walk
from tests.qa_metrics.db import MetabasePostgres


class _FakeCursor:
    def __init__(self, rows: list[tuple[int]]) -> None:
        self._rows = rows
        self.sql: str | None = None
        self.params: tuple[object, ...] | None = None

    def __enter__(self) -> _FakeCursor:
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def execute(self, sql: str, params: tuple[object, ...]) -> None:
        self.sql = sql
        self.params = params

    def fetchall(self) -> list[tuple[int]]:
        return self._rows


class _FakeDb:
    def __init__(self, rows: list[tuple[int]]) -> None:
        self._rows = rows

    def cursor(self) -> _FakeCursor:
        return _FakeCursor(self._rows)

    def __enter__(self) -> _FakeDb:
        return self

    def __exit__(self, *_: object) -> None:
        return None


def _wire(
    monkeypatch: pytest.MonkeyPatch,
    *,
    git_werks: list[tuple[int, Class]],
    from_env: Callable[[object], object],
) -> None:
    """Stub the branch label, the ``.werks`` index, the git walk and the DB."""
    monkeypatch.setattr(check_gaps, "read_branch_version", lambda _p: "3.0.0")
    monkeypatch.setattr(
        check_gaps,
        "load_raw_files",
        lambda _p: [SimpleNamespace(id=wid, class_=cls) for wid, cls in git_werks],
    )
    # Patch the underlying module/class objects (the same ones check_gaps binds),
    # not check_gaps' re-exported names, so mypy's no-implicit-reexport is happy.
    monkeypatch.setattr(
        walk,
        "walk_werk_adds",
        lambda _r, since=None, until=None: iter(
            [SimpleNamespace(werk_id=wid) for wid, _cls in git_werks]
        ),
    )
    monkeypatch.setattr(MetabasePostgres, "from_env", classmethod(from_env))


def _db_returning(db_werk_ids: list[int]) -> Callable[[object], _FakeDb]:
    return lambda _cls: _FakeDb([(wid,) for wid in db_werk_ids])


def _db_raising(exc: Exception) -> Callable[[object], None]:
    def _raise(_cls: object) -> None:
        raise exc

    return _raise


def test_main_exit_0_when_in_sync(monkeypatch: pytest.MonkeyPatch) -> None:
    _wire(monkeypatch, git_werks=[(1, Class.FIX)], from_env=_db_returning([1]))
    assert check_gaps.main(["--repo", "/repo"]) == 0


def test_main_exit_1_on_gap(monkeypatch: pytest.MonkeyPatch) -> None:
    _wire(
        monkeypatch,
        git_werks=[(1, Class.FIX), (2, Class.FIX)],
        from_env=_db_returning([1]),
    )
    assert check_gaps.main(["--repo", "/repo"]) == 1


def test_main_ignores_non_fix_werks(monkeypatch: pytest.MonkeyPatch) -> None:
    """A feature-werk absent from the fix-only table is not a gap: the checker
    reconciles only the classes the pusher records."""
    _wire(
        monkeypatch,
        git_werks=[(1, Class.FIX), (2, Class.FEATURE)],
        from_env=_db_returning([1]),
    )
    assert check_gaps.main(["--repo", "/repo"]) == 0


def test_main_exit_0_when_db_unreachable(monkeypatch: pytest.MonkeyPatch) -> None:
    """No SQLSTATE => never reached the server (VPN down): skip, exit 0, so the
    daily cron does not alarm."""
    # A bare OperationalError has sqlstate=None -- the server was never reached.
    _wire(
        monkeypatch,
        git_werks=[(1, Class.FIX)],
        from_env=_db_raising(psycopg.OperationalError("connection failed")),
    )
    assert check_gaps.main(["--repo", "/repo"]) == 0


def test_main_exit_2_on_server_side_db_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """A server-side OperationalError (SQLSTATE set, e.g. bad credentials) is a
    real config problem, not an unreachable-host skip: exit 2."""
    # InvalidPassword is an OperationalError with sqlstate "28P01": the server
    # answered, so it's a config error, not an unreachable-host skip.
    _wire(
        monkeypatch,
        git_werks=[(1, Class.FIX)],
        from_env=_db_raising(psycopg_errors.InvalidPassword("password authentication failed")),
    )
    assert check_gaps.main(["--repo", "/repo"]) == 2


def test_main_exit_2_on_missing_branch_version(monkeypatch: pytest.MonkeyPatch) -> None:
    """A setup problem (no BRANCH_VERSION in defines.make) must exit 2, not
    escape main as an uncaught exception that Python reports as exit 1 -- which
    reads as 'gap found'."""
    monkeypatch.setattr(
        check_gaps,
        "read_branch_version",
        lambda _p: (_ for _ in ()).throw(ValueError("BRANCH_VERSION not found")),
    )
    assert check_gaps.main(["--repo", "/repo"]) == 2


def test_main_exit_2_on_git_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """A git failure (e.g. --repo is not a git repo) exits 2, not 1."""
    monkeypatch.setattr(check_gaps, "read_branch_version", lambda _p: "3.0.0")

    def _raise(_r: object, since: object = None, until: object = None) -> object:
        raise subprocess.CalledProcessError(128, ["git", "log"])

    monkeypatch.setattr(walk, "walk_werk_adds", _raise)
    assert check_gaps.main(["--repo", "/repo"]) == 2
