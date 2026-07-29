# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Unit tests for cmk.dev_deploy.deploy_state (state I/O, git helpers, hashing)."""

from __future__ import annotations

import hashlib
import json
import subprocess
import time
from pathlib import Path
from unittest.mock import patch

from cmk.dev_deploy.state.deploy_state import (
    build_and_save_state,
    compute_dirty_hashes,
    compute_file_hash,
    delete_state,
    DeployerState,
    DeployState,
    get_current_branch,
    get_dirty_files,
    get_head_commit,
    load_state,
    reset_git_cache,
    save_state,
    state_file_path,
    STATE_SCHEMA_VERSION,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_state(
    branch: str = "master",
    deployers: dict[str, DeployerState] | None = None,
    created_at: float = 0.0,
    diff_base_commit: str = "",
) -> DeployState:
    """Create a DeployState with sensible defaults for testing."""
    return DeployState(
        schema_version=STATE_SCHEMA_VERSION,
        branch=branch,
        deployers=deployers or {},
        created_at=created_at,
        diff_base_commit=diff_base_commit,
    )


def _make_deployer_state(
    deployer: str = "python",
    git_commit: str = "a" * 40,
    dirty_file_hashes: dict[str, str] | None = None,
    deployed_at: float = 0.0,
) -> DeployerState:
    """Create a DeployerState with sensible defaults for testing."""
    return DeployerState(
        deployer=deployer,
        git_commit=git_commit,
        dirty_file_hashes=dirty_file_hashes or {},
        deployed_at=deployed_at,
    )


def _make_mock_run(
    returncode: int = 0,
    stdout: str = "",
    stderr: str = "",
) -> object:
    """Create a callable that returns a mock CompletedProcess."""

    def _mock_run(
        cmd: list[str],
        **_kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=returncode,
            stdout=stdout,
            stderr=stderr,
        )

    return _mock_run


# ---------------------------------------------------------------------------
# state_file_path tests
# ---------------------------------------------------------------------------


class TestStateFilePath:
    """Tests for the state_file_path function."""

    def test_state_file_path_canonical(self, tmp_path: Path) -> None:
        """State file uses site name as directory and deploy_state.json as filename."""
        result = state_file_path(tmp_path)
        assert result.name == "deploy_state.json"
        assert result.parent.name == tmp_path.name
        assert "cmk-dev-deploy" in str(result)


# ---------------------------------------------------------------------------
# load_state tests
# ---------------------------------------------------------------------------


class TestLoadState:
    """Tests for the load_state function."""

    def test_load_state_missing_file(self, tmp_path: Path) -> None:
        """Returns None when the state file does not exist."""
        result = load_state(tmp_path, base_dir=tmp_path)
        assert result is None

    def test_load_state_valid_round_trip(self, tmp_path: Path) -> None:
        """Save then load yields identical fields."""
        now = time.time()
        ds = _make_deployer_state(
            deployer="python",
            git_commit="b" * 40,
            dirty_file_hashes={"cmk/foo.py": "abc123"},
            deployed_at=now,
        )
        state = _make_state(
            branch="feature/x",
            deployers={"python": ds},
            created_at=now,
            diff_base_commit="c" * 40,
        )
        save_state(state, tmp_path, base_dir=tmp_path)

        loaded = load_state(tmp_path, base_dir=tmp_path)
        assert loaded is not None
        assert loaded.schema_version == STATE_SCHEMA_VERSION
        assert loaded.branch == "feature/x"
        assert loaded.created_at == now
        assert loaded.diff_base_commit == "c" * 40
        assert "python" in loaded.deployers
        d = loaded.deployers["python"]
        assert d.deployer == "python"
        assert d.git_commit == "b" * 40
        assert d.dirty_file_hashes == {"cmk/foo.py": "abc123"}
        assert d.deployed_at == now

    def test_load_state_backend_round_trip(self, tmp_path: Path) -> None:
        """The site preparation backend is persisted and restored."""
        state = _make_state(branch="master")
        state.backend = "clone"
        save_state(state, tmp_path, base_dir=tmp_path)
        loaded = load_state(tmp_path, base_dir=tmp_path)
        assert loaded is not None
        assert loaded.backend == "clone"

    def test_load_state_uncovered_files_round_trip(self, tmp_path: Path) -> None:
        """Recorded uncovered files are persisted and restored."""
        state = _make_state(branch="master")
        state.uncovered_files = {"some/file.py": "abc123"}
        save_state(state, tmp_path, base_dir=tmp_path)
        loaded = load_state(tmp_path, base_dir=tmp_path)
        assert loaded is not None
        assert loaded.uncovered_files == {"some/file.py": "abc123"}

    def test_load_state_missing_backend_defaults_empty(self, tmp_path: Path) -> None:
        """State files written before the backend field default to empty string."""
        sf = state_file_path(tmp_path, base_dir=tmp_path)
        sf.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "schema_version": STATE_SCHEMA_VERSION,
            "branch": "master",
            "deployers": {},
            "created_at": 0.0,
            "diff_base_commit": "",
        }
        sf.write_text(json.dumps(data))
        loaded = load_state(tmp_path, base_dir=tmp_path)
        assert loaded is not None
        assert loaded.backend == ""

    def test_load_state_missing_diff_base_commit(self, tmp_path: Path) -> None:
        """State files without diff_base_commit (v2 compat) default to empty string."""
        sf = state_file_path(tmp_path, base_dir=tmp_path)
        sf.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "schema_version": STATE_SCHEMA_VERSION,
            "branch": "master",
            "deployers": {},
            "created_at": 0.0,
            # No diff_base_commit key
        }
        sf.write_text(json.dumps(data))
        loaded = load_state(tmp_path, base_dir=tmp_path)
        assert loaded is not None
        assert loaded.diff_base_commit == ""

    def test_load_state_corrupt_json(self, tmp_path: Path) -> None:
        """Returns None when the state file contains invalid JSON."""
        sf = state_file_path(tmp_path, base_dir=tmp_path)
        sf.parent.mkdir(parents=True, exist_ok=True)
        sf.write_text("{this is not valid json!!!")
        result = load_state(tmp_path, base_dir=tmp_path)
        assert result is None

    def test_load_state_wrong_schema_version(self, tmp_path: Path) -> None:
        """Returns None when schema_version does not match current version."""
        sf = state_file_path(tmp_path, base_dir=tmp_path)
        sf.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "schema_version": 999,
            "branch": "master",
            "deployers": {},
            "created_at": 0.0,
        }
        sf.write_text(json.dumps(data))
        result = load_state(tmp_path, base_dir=tmp_path)
        assert result is None

    def test_load_state_missing_fields(self, tmp_path: Path) -> None:
        """Returns None (not crash) when required fields are missing in deployer data."""
        sf = state_file_path(tmp_path, base_dir=tmp_path)
        sf.parent.mkdir(parents=True, exist_ok=True)
        # Missing "deployer" and "git_commit" in the deployer entry -> KeyError
        data = {
            "schema_version": STATE_SCHEMA_VERSION,
            "branch": "master",
            "deployers": {"python": {"bad_key": "value"}},
            "created_at": 0.0,
        }
        sf.write_text(json.dumps(data))
        result = load_state(tmp_path, base_dir=tmp_path)
        assert result is None

    def test_load_state_empty_deployers(self, tmp_path: Path) -> None:
        """Valid state with empty deployers dict loads successfully."""
        state = _make_state(branch="main", deployers={}, created_at=1.0)
        save_state(state, tmp_path, base_dir=tmp_path)
        loaded = load_state(tmp_path, base_dir=tmp_path)
        assert loaded is not None
        assert loaded.deployers == {}
        assert loaded.branch == "main"


# ---------------------------------------------------------------------------
# save_state tests
# ---------------------------------------------------------------------------


class TestSaveState:
    """Tests for the save_state function."""

    def test_save_state_creates_directory(self, tmp_path: Path) -> None:
        """Save creates the state directory if it doesn't exist."""
        state = _make_state(branch="test")
        save_state(state, tmp_path, base_dir=tmp_path)
        sf = state_file_path(tmp_path, base_dir=tmp_path)
        assert sf.parent.is_dir()
        assert sf.is_file()

    def test_save_state_atomic_write(self, tmp_path: Path) -> None:
        """Save produces valid JSON with no temp files left behind."""
        state = _make_state(branch="atomic-test")
        save_state(state, tmp_path, base_dir=tmp_path)
        sf = state_file_path(tmp_path, base_dir=tmp_path)
        # Verify the file contains valid JSON
        raw = json.loads(sf.read_text())
        assert raw["branch"] == "atomic-test"
        # Verify no temp files remain
        temp_files = list(sf.parent.glob(".deploy_state_*.tmp"))
        assert temp_files == []

    def test_save_state_overwrites_existing(self, tmp_path: Path) -> None:
        """Second save overwrites first save's data."""
        state1 = _make_state(branch="first")
        save_state(state1, tmp_path, base_dir=tmp_path)
        state2 = _make_state(branch="second")
        save_state(state2, tmp_path, base_dir=tmp_path)
        loaded = load_state(tmp_path, base_dir=tmp_path)
        assert loaded is not None
        assert loaded.branch == "second"

    def test_save_state_with_dirty_hashes(self, tmp_path: Path) -> None:
        """Save preserves dirty_file_hashes through round-trip."""
        hashes = {"cmk/gui/views.py": "abc" * 20, "cmk/utils/paths.py": "def" * 20}
        ds = _make_deployer_state(dirty_file_hashes=hashes)
        state = _make_state(deployers={"python": ds})
        save_state(state, tmp_path, base_dir=tmp_path)
        loaded = load_state(tmp_path, base_dir=tmp_path)
        assert loaded is not None
        assert loaded.deployers["python"].dirty_file_hashes == hashes


# ---------------------------------------------------------------------------
# delete_state tests
# ---------------------------------------------------------------------------


class TestDeleteState:
    """Tests for the delete_state function."""

    def test_delete_state_existing_file(self, tmp_path: Path) -> None:
        """Delete removes file, subsequent load returns None."""
        state = _make_state(branch="delete-me")
        save_state(state, tmp_path, base_dir=tmp_path)
        assert state_file_path(tmp_path, base_dir=tmp_path).is_file()
        delete_state(tmp_path, base_dir=tmp_path)
        assert not state_file_path(tmp_path, base_dir=tmp_path).is_file()
        assert load_state(tmp_path, base_dir=tmp_path) is None

    def test_delete_state_missing_file(self, tmp_path: Path) -> None:
        """Delete when file doesn't exist raises no error."""
        # Ensure the directory exists but file does not
        state_file_path(tmp_path, base_dir=tmp_path).parent.mkdir(parents=True, exist_ok=True)
        delete_state(tmp_path, base_dir=tmp_path)  # Should not raise

    def test_delete_state_missing_directory(self, tmp_path: Path) -> None:
        """Delete when the state directory doesn't exist raises no error."""
        delete_state(tmp_path, base_dir=tmp_path)  # Should not raise


# ---------------------------------------------------------------------------
# compute_file_hash tests
# ---------------------------------------------------------------------------


class TestComputeFileHash:
    """Tests for the compute_file_hash function."""

    def test_compute_file_hash_known_content(self, tmp_path: Path) -> None:
        """SHA256 of file matches hashlib.sha256(content).hexdigest()."""
        content = b"hello world\nthis is a test\n"
        filepath = tmp_path / "test.txt"
        filepath.write_bytes(content)
        expected = hashlib.sha256(content).hexdigest()
        assert compute_file_hash(filepath) == expected

    def test_compute_file_hash_empty_file(self, tmp_path: Path) -> None:
        """Empty file has the SHA256 of empty bytes."""
        filepath = tmp_path / "empty.txt"
        filepath.write_bytes(b"")
        expected = hashlib.sha256(b"").hexdigest()
        assert compute_file_hash(filepath) == expected


# ---------------------------------------------------------------------------
# compute_dirty_hashes tests (mock git subprocess)
# ---------------------------------------------------------------------------


class TestComputeDirtyHashes:
    """Tests for the compute_dirty_hashes function."""

    def test_compute_dirty_hashes_no_dirty_files(self, tmp_path: Path) -> None:
        """Returns empty dict when no dirty files."""
        with patch(
            "cmk.dev_deploy.state.deploy_state.get_dirty_files",
            return_value=[],
        ):
            result = compute_dirty_hashes(tmp_path)
        assert result == {}

    def test_compute_dirty_hashes_with_files(self, tmp_path: Path) -> None:
        """Returns SHA256 hashes for existing dirty files."""
        # Create real files
        (tmp_path / "cmk").mkdir()
        (tmp_path / "cmk" / "a.py").write_bytes(b"content_a")
        (tmp_path / "cmk" / "b.py").write_bytes(b"content_b")

        with patch(
            "cmk.dev_deploy.state.deploy_state.get_dirty_files",
            return_value=["cmk/a.py", "cmk/b.py"],
        ):
            result = compute_dirty_hashes(tmp_path)

        assert len(result) == 2
        assert result["cmk/a.py"] == hashlib.sha256(b"content_a").hexdigest()
        assert result["cmk/b.py"] == hashlib.sha256(b"content_b").hexdigest()

    def test_compute_dirty_hashes_skips_deleted(self, tmp_path: Path) -> None:
        """Deleted files (not on disk) are skipped in result."""
        # Create only one of two reported dirty files
        (tmp_path / "cmk").mkdir()
        (tmp_path / "cmk" / "exists.py").write_bytes(b"still here")

        with patch(
            "cmk.dev_deploy.state.deploy_state.get_dirty_files",
            return_value=["cmk/exists.py", "cmk/deleted.py"],
        ):
            result = compute_dirty_hashes(tmp_path)

        assert "cmk/exists.py" in result
        assert "cmk/deleted.py" not in result

    def test_compute_dirty_hashes_with_prefix_filter(self, tmp_path: Path) -> None:
        """Only files matching path_prefixes are included."""
        (tmp_path / "cmk").mkdir()
        (tmp_path / "cmk" / "a.py").write_bytes(b"content_a")
        (tmp_path / "packages").mkdir()
        (tmp_path / "packages" / "b.py").write_bytes(b"content_b")

        with patch(
            "cmk.dev_deploy.state.deploy_state.get_dirty_files",
            return_value=["cmk/a.py", "packages/b.py"],
        ):
            result = compute_dirty_hashes(tmp_path, path_prefixes=("cmk/",))

        assert "cmk/a.py" in result
        assert "packages/b.py" not in result


# ---------------------------------------------------------------------------
# build_and_save_state tests (diff base handling)
# ---------------------------------------------------------------------------

_HEAD = "d" * 40
_RUN_BASE = "b" * 40
_OLD_BASE = "c" * 40


class TestBuildAndSaveStateDiffBase:
    """diff_base_commit handling, especially on partial failure."""

    def _build_and_load(
        self,
        tmp_path: Path,
        *,
        previous_state: DeployState | None,
        all_succeeded: bool,
        run_diff_base: str | None = None,
    ) -> DeployState:
        no_dirty: dict[str, dict[str, str]] = {
            n: {} for n in ("install_spec", "config_spec", "wheel_spec")
        }
        with (
            patch(
                "cmk.dev_deploy.state.deploy_state.get_head_commit",
                return_value=_HEAD,
            ),
            patch(
                "cmk.dev_deploy.state.deploy_state.get_dirty_files",
                return_value=[],
            ),
        ):
            build_and_save_state(
                tmp_path,
                tmp_path,
                "master",
                successful_deployers={"install_spec", "wheel_spec"},
                previous_state=previous_state,
                run_diff_base=run_diff_base,
                deployer_dirty_hashes=no_dirty,
                all_succeeded=all_succeeded,
                base_dir=tmp_path,
            )
        loaded = load_state(tmp_path, base_dir=tmp_path)
        assert loaded is not None
        return loaded

    def test_success_advances_diff_base_to_head(self, tmp_path: Path) -> None:
        loaded = self._build_and_load(
            tmp_path, previous_state=None, all_succeeded=True, run_diff_base=_RUN_BASE
        )
        assert loaded.diff_base_commit == _HEAD

    def test_partial_failure_without_previous_state_keeps_run_diff_base(
        self, tmp_path: Path
    ) -> None:
        """First deploy after a fresh clone: a failed step must stay re-detectable.

        Advancing to HEAD here silently dropped the failed deployer's
        changes -- the next run reported "All deployers up to date".
        """
        loaded = self._build_and_load(
            tmp_path, previous_state=None, all_succeeded=False, run_diff_base=_RUN_BASE
        )
        assert loaded.diff_base_commit == _RUN_BASE
        # Only the successful deployers get fresh state entries.
        assert set(loaded.deployers) == {"install_spec", "wheel_spec"}
        assert loaded.deployers["install_spec"].git_commit == _HEAD

    def test_partial_failure_prefers_run_diff_base_over_previous_state(
        self, tmp_path: Path
    ) -> None:
        """The base actually used for detection wins over a stale state value."""
        previous = _make_state(diff_base_commit=_OLD_BASE)
        loaded = self._build_and_load(
            tmp_path, previous_state=previous, all_succeeded=False, run_diff_base=_RUN_BASE
        )
        assert loaded.diff_base_commit == _RUN_BASE

    def test_partial_failure_falls_back_to_previous_state(self, tmp_path: Path) -> None:
        """Callers without a run diff base keep the previous state's base."""
        previous = _make_state(diff_base_commit=_OLD_BASE)
        loaded = self._build_and_load(tmp_path, previous_state=previous, all_succeeded=False)
        assert loaded.diff_base_commit == _OLD_BASE

    def test_partial_failure_without_any_base_falls_back_to_head(self, tmp_path: Path) -> None:
        """No run base and no previous state (site without COMMIT file)."""
        loaded = self._build_and_load(tmp_path, previous_state=None, all_succeeded=False)
        assert loaded.diff_base_commit == _HEAD


# ---------------------------------------------------------------------------
# git helper tests (mock subprocess)
# ---------------------------------------------------------------------------


class TestGetCurrentBranch:
    """Tests for the get_current_branch function."""

    def test_get_current_branch_normal(self, tmp_path: Path) -> None:
        """Returns branch name when git succeeds."""
        with patch(
            "cmk.dev_deploy.state.deploy_state.subprocess.run",
            _make_mock_run(returncode=0, stdout="master\n"),
        ):
            result = get_current_branch(tmp_path)
        assert result == "master"

    def test_get_current_branch_detached(self, tmp_path: Path) -> None:
        """Returns empty string when HEAD is detached."""
        with patch(
            "cmk.dev_deploy.state.deploy_state.subprocess.run",
            _make_mock_run(returncode=0, stdout="HEAD\n"),
        ):
            result = get_current_branch(tmp_path)
        assert result == ""

    def test_get_current_branch_error(self, tmp_path: Path) -> None:
        """Returns empty string on subprocess failure."""
        with patch(
            "cmk.dev_deploy.state.deploy_state.subprocess.run",
            _make_mock_run(returncode=1, stderr="fatal: error"),
        ):
            result = get_current_branch(tmp_path)
        assert result == ""


class TestGetHeadCommit:
    """Tests for the get_head_commit function."""

    def test_get_head_commit_normal(self, tmp_path: Path) -> None:
        """Returns stripped commit hash on success."""
        commit = "abc123" + "0" * 34
        with patch(
            "cmk.dev_deploy.state.deploy_state.subprocess.run",
            _make_mock_run(returncode=0, stdout=f"{commit}\n"),
        ):
            result = get_head_commit(tmp_path)
        assert result == commit

    def test_get_head_commit_error(self, tmp_path: Path) -> None:
        """Returns empty string on subprocess failure."""
        with patch(
            "cmk.dev_deploy.state.deploy_state.subprocess.run",
            _make_mock_run(returncode=1, stderr="fatal: not a git repo"),
        ):
            result = get_head_commit(tmp_path)
        assert result == ""


# ---------------------------------------------------------------------------
# get_dirty_files tests (mock subprocess)
# ---------------------------------------------------------------------------


_UNTRACKED = "cmk.dev_deploy.state.deploy_state.query_untracked_files"


class TestGetDirtyFiles:
    """Tests for the get_dirty_files function."""

    def test_get_dirty_files_normal(self, tmp_path: Path) -> None:
        """Returns list of dirty file paths."""
        with (
            patch(
                "cmk.dev_deploy.state.deploy_state.subprocess.run",
                _make_mock_run(returncode=0, stdout="cmk/a.py\ncmk/b.py\n"),
            ),
            patch(_UNTRACKED, return_value=[]),
        ):
            result = get_dirty_files(tmp_path)
        assert result == ["cmk/a.py", "cmk/b.py"]

    def test_get_dirty_files_empty(self, tmp_path: Path) -> None:
        """Returns empty list when no dirty files."""
        with (
            patch(
                "cmk.dev_deploy.state.deploy_state.subprocess.run",
                _make_mock_run(returncode=0, stdout=""),
            ),
            patch(_UNTRACKED, return_value=[]),
        ):
            result = get_dirty_files(tmp_path)
        assert result == []

    def test_get_dirty_files_error(self, tmp_path: Path) -> None:
        """Returns empty list on subprocess failure."""
        with (
            patch(
                "cmk.dev_deploy.state.deploy_state.subprocess.run",
                _make_mock_run(returncode=1, stderr="fatal"),
            ),
            patch(_UNTRACKED, return_value=[]),
        ):
            result = get_dirty_files(tmp_path)
        assert result == []

    def test_get_dirty_files_includes_untracked(self, tmp_path: Path) -> None:
        """New files that were never ``git add``-ed count as dirty.

        Regression: they are invisible to ``git diff``, so a deployer whose
        only change is a new file would never redeploy.
        """
        with (
            patch(
                "cmk.dev_deploy.state.deploy_state.subprocess.run",
                _make_mock_run(returncode=0, stdout="cmk/a.py\n"),
            ),
            patch(_UNTRACKED, return_value=["packages/cmk-frontend-vue/src/NewApp.vue"]),
        ):
            result = get_dirty_files(tmp_path)
        assert result == ["cmk/a.py", "packages/cmk-frontend-vue/src/NewApp.vue"]

    def test_get_dirty_files_deduplicates(self, tmp_path: Path) -> None:
        """A path reported by both git commands appears once.

        ``git rm --cached`` leaves a file listed as deleted by ``git diff
        HEAD`` and as untracked by ``git ls-files --others``.
        """
        with (
            patch(
                "cmk.dev_deploy.state.deploy_state.subprocess.run",
                _make_mock_run(returncode=0, stdout="cmk/a.py\n"),
            ),
            patch(_UNTRACKED, return_value=["cmk/a.py"]),
        ):
            result = get_dirty_files(tmp_path)
        assert result == ["cmk/a.py"]

    def test_compute_dirty_hashes_covers_untracked(self, tmp_path: Path) -> None:
        """Untracked files reach compute_dirty_hashes and its prefix filter."""
        (tmp_path / "pkg").mkdir()
        (tmp_path / "pkg" / "new.vue").write_text("content")
        (tmp_path / "elsewhere.txt").write_text("content")
        with (
            patch(
                "cmk.dev_deploy.state.deploy_state.subprocess.run",
                _make_mock_run(returncode=0, stdout=""),
            ),
            patch(_UNTRACKED, return_value=["pkg/new.vue", "elsewhere.txt"]),
        ):
            assert set(compute_dirty_hashes(tmp_path)) == {"pkg/new.vue", "elsewhere.txt"}
            assert set(compute_dirty_hashes(tmp_path, path_prefixes=("pkg/",))) == {"pkg/new.vue"}


# ---------------------------------------------------------------------------
# Per-cycle git memo tests
# ---------------------------------------------------------------------------


def _counting_run(stdout: str) -> tuple[object, list[list[str]]]:
    """Return a subprocess.run stand-in plus the list it records commands in."""
    calls: list[list[str]] = []

    def _run(cmd: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(cmd)
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout=stdout, stderr="")

    return _run, calls


class TestGitCache:
    """The git queries a deploy cycle repeats are answered once."""

    def test_repeated_queries_run_git_once(self, tmp_path: Path) -> None:
        run, calls = _counting_run("cmk/a.py\n")
        with patch("cmk.dev_deploy.state.deploy_state.subprocess.run", run):
            assert get_dirty_files(tmp_path) == ["cmk/a.py"]
            assert get_dirty_files(tmp_path) == ["cmk/a.py"]
            assert get_dirty_files(tmp_path) == ["cmk/a.py"]
        assert len(calls) == 1

    def test_untracked_query_runs_once_per_cycle(self, tmp_path: Path) -> None:
        """The added `ls-files` costs one query per cycle, not one per caller."""
        calls: list[Path] = []

        def _query(repo_root: Path) -> list[str]:
            calls.append(repo_root)
            return ["new.vue"]

        with (
            patch(
                "cmk.dev_deploy.state.deploy_state.subprocess.run",
                _make_mock_run(returncode=0, stdout=""),
            ),
            patch(_UNTRACKED, _query),
        ):
            assert get_dirty_files(tmp_path) == ["new.vue"]
            assert get_dirty_files(tmp_path) == ["new.vue"]
        assert calls == [tmp_path]

    def test_reset_re_reads_the_working_tree(self, tmp_path: Path) -> None:
        run, calls = _counting_run("cmk/a.py\n")
        with patch("cmk.dev_deploy.state.deploy_state.subprocess.run", run):
            get_dirty_files(tmp_path)
            reset_git_cache()
            get_dirty_files(tmp_path)
        assert len(calls) == 2

    def test_another_repository_re_reads(self, tmp_path: Path) -> None:
        run, calls = _counting_run("cmk/a.py\n")
        with patch("cmk.dev_deploy.state.deploy_state.subprocess.run", run):
            get_dirty_files(tmp_path)
            get_dirty_files(tmp_path / "elsewhere")
        assert len(calls) == 2

    def test_head_and_branch_are_separate_queries(self, tmp_path: Path) -> None:
        run, calls = _counting_run("main\n")
        with patch("cmk.dev_deploy.state.deploy_state.subprocess.run", run):
            get_head_commit(tmp_path)
            get_current_branch(tmp_path)
            get_head_commit(tmp_path)
            get_current_branch(tmp_path)
        assert [cmd[1:3] for cmd in calls] == [["rev-parse", "HEAD"], ["rev-parse", "--abbrev-ref"]]

    def test_overlapping_prefixes_hash_each_file_once(self, tmp_path: Path) -> None:
        (tmp_path / "cmk").mkdir()
        (tmp_path / "cmk" / "a.py").write_text("content")
        hashed: list[Path] = []

        def _hash(path: Path) -> str:
            hashed.append(path)
            return "deadbeef"

        with (
            patch(
                "cmk.dev_deploy.state.deploy_state.get_dirty_files",
                return_value=["cmk/a.py"],
            ),
            patch("cmk.dev_deploy.state.deploy_state.compute_file_hash", _hash),
        ):
            first = compute_dirty_hashes(tmp_path, path_prefixes=("cmk/",))
            second = compute_dirty_hashes(tmp_path, path_prefixes=("cmk/a",))
        assert first == second == {"cmk/a.py": "deadbeef"}
        assert hashed == [tmp_path / "cmk" / "a.py"]
