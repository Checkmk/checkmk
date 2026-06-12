# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Unit tests for the persistent 'not covered by any deploy spec' warning."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from unittest.mock import patch

import pytest

from cmk.dev_deploy.__main__ import _warn_uncovered_files
from cmk.dev_deploy.state.deploy_state import compute_file_hash, DeployState
from cmk.dev_deploy.types import ChangeCategory, ChangeSet

_PATH = "zzz_uncovered/script.py"


@pytest.fixture(autouse=True)
def _fake_registry() -> Iterator[None]:
    """Coverage stub: cmk/ is covered, everything else is not.

    The real registry needs a fully enriched manifest; its matching is
    covered by test_registry.py.  These tests target the persistence
    logic around it.
    """

    def _uncovered(changed_files: tuple[str, ...]) -> list[str]:
        return sorted(f for f in changed_files if not f.startswith("cmk/"))

    with patch("cmk.dev_deploy.__main__.uncovered_changed_files", side_effect=_uncovered):
        yield


def _changes_with(path: str) -> ChangeSet:
    return ChangeSet(
        build_commit="a" * 40,
        files=(path,),
        categories={ChangeCategory.OTHER: (path,)},
    )


def _state_with(uncovered: dict[str, str]) -> DeployState:
    return DeployState(uncovered_files=uncovered)


def _write(repo_root: Path, relpath: str, content: str) -> Path:
    abs_path = repo_root / relpath
    abs_path.parent.mkdir(parents=True, exist_ok=True)
    abs_path.write_text(content)
    return abs_path


class TestWarnUncoveredFiles:
    def test_fresh_uncovered_file_is_recorded(self, tmp_path: Path) -> None:
        abs_path = _write(tmp_path, _PATH, "content")
        result = _warn_uncovered_files(None, _changes_with(_PATH), tmp_path)
        assert result == {_PATH: compute_file_hash(abs_path)}

    def test_recorded_entry_persists_without_new_changes(self, tmp_path: Path) -> None:
        """The warning must survive the diff base advancing past the file."""
        abs_path = _write(tmp_path, _PATH, "content")
        state = _state_with({_PATH: compute_file_hash(abs_path)})
        result = _warn_uncovered_files(state, None, tmp_path)
        assert result == {_PATH: compute_file_hash(abs_path)}

    def test_edited_recorded_file_is_dropped(self, tmp_path: Path) -> None:
        """A further edit re-enters normal change detection; the stale record goes."""
        _write(tmp_path, _PATH, "new content")
        state = _state_with({_PATH: "hash-of-old-content"})
        assert _warn_uncovered_files(state, None, tmp_path) == {}

    def test_deleted_recorded_file_is_dropped(self, tmp_path: Path) -> None:
        state = _state_with({_PATH: "some-hash"})
        assert _warn_uncovered_files(state, None, tmp_path) == {}

    def test_covered_recorded_file_is_dropped(self, tmp_path: Path) -> None:
        """A deploy spec covering the file ends the warning (cmk/ is a wheel prefix)."""
        abs_path = _write(tmp_path, "cmk/foo.py", "content")
        state = _state_with({"cmk/foo.py": compute_file_hash(abs_path)})
        assert _warn_uncovered_files(state, None, tmp_path) == {}

    def test_fresh_detection_refreshes_recorded_hash(self, tmp_path: Path) -> None:
        abs_path = _write(tmp_path, _PATH, "edited again")
        state = _state_with({_PATH: "hash-of-old-content"})
        result = _warn_uncovered_files(state, _changes_with(_PATH), tmp_path)
        assert result == {_PATH: compute_file_hash(abs_path)}

    def test_ignored_category_files_do_not_warn(self, tmp_path: Path) -> None:
        path = "werks/12345"
        _write(tmp_path, path, "werk")
        changes = ChangeSet(
            build_commit="a" * 40,
            files=(path,),
            categories={ChangeCategory.IGNORED: (path,)},
        )
        assert _warn_uncovered_files(None, changes, tmp_path) == {}
