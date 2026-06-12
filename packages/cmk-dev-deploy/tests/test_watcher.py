# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Unit tests for cmk.dev_deploy.watcher (content hashing, heartbeat, watch loop)."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Helpers for subprocess mocking
# ---------------------------------------------------------------------------


def _make_subprocess_mock(
    *,
    unstaged: str = "",
    staged: str = "",
    untracked: str = "",
) -> object:
    """Create a callable that mimics subprocess.run for the 3 git commands.

    Routes based on command arguments:
    - ``git diff --name-only <base>`` -> unstaged
    - ``git diff --name-only --staged`` -> staged
    - ``git ls-files --others --exclude-standard`` -> untracked
    """

    def _mock_run(
        cmd: list[str],
        **_kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        if "ls-files" in cmd:
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout=untracked, stderr="")
        if "--staged" in cmd:
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout=staged, stderr="")
        # Default: unstaged diff
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout=unstaged, stderr="")

    return _mock_run


# ---------------------------------------------------------------------------
# TestGetContentHash
# ---------------------------------------------------------------------------


class TestGetContentHash:
    """Tests for _get_content_hash(): content-aware change detection."""

    def test_returns_hex_digest_for_dirty_files(self, tmp_path: Path) -> None:
        """Hash of 2 dirty files is a 32-char hex string (MD5 hex digest)."""
        from cmk.dev_deploy.watcher import _get_content_hash

        (tmp_path / "a.py").write_text("hello")
        (tmp_path / "b.py").write_text("world")

        mock_run = _make_subprocess_mock(unstaged="a.py\nb.py\n")
        with patch("cmk.dev_deploy.watcher.subprocess.run", side_effect=mock_run):
            with patch("cmk.dev_deploy.watcher._get_untracked_files", return_value=""):
                result = _get_content_hash("HEAD", tmp_path)

        assert isinstance(result, str)
        assert len(result) == 32
        assert all(c in "0123456789abcdef" for c in result)

    def test_same_content_produces_same_hash(self, tmp_path: Path) -> None:
        """Identical file content on two calls produces the same hash."""
        from cmk.dev_deploy.watcher import _get_content_hash

        (tmp_path / "a.py").write_text("hello")

        mock_run = _make_subprocess_mock(unstaged="a.py\n")
        with patch("cmk.dev_deploy.watcher.subprocess.run", side_effect=mock_run):
            with patch("cmk.dev_deploy.watcher._get_untracked_files", return_value=""):
                hash1 = _get_content_hash("HEAD", tmp_path)
                hash2 = _get_content_hash("HEAD", tmp_path)

        assert hash1 == hash2

    def test_different_content_produces_different_hash(self, tmp_path: Path) -> None:
        """CORE BUG FIX: same filename list, different content = different hash.

        This is the central test for the content-hash bug fix. The old
        _get_diff_hash only hashed filenames, so re-editing an already-dirty
        file would not trigger a deploy. The new _get_content_hash hashes
        file contents, so content changes are always detected.
        """
        from cmk.dev_deploy.watcher import _get_content_hash

        (tmp_path / "a.py").write_text("version 1")

        mock_run = _make_subprocess_mock(unstaged="a.py\n")
        with patch("cmk.dev_deploy.watcher.subprocess.run", side_effect=mock_run):
            with patch("cmk.dev_deploy.watcher._get_untracked_files", return_value=""):
                hash1 = _get_content_hash("HEAD", tmp_path)

                # Change content without changing filename list
                (tmp_path / "a.py").write_text("version 2")
                hash2 = _get_content_hash("HEAD", tmp_path)

        assert hash1 != hash2

    def test_deleted_file_uses_sentinel(self, tmp_path: Path) -> None:
        """A file in git diff that does not exist on disk does not crash."""
        from cmk.dev_deploy.watcher import _get_content_hash

        # "missing.py" does NOT exist on disk
        mock_run = _make_subprocess_mock(unstaged="missing.py\n")
        with patch("cmk.dev_deploy.watcher.subprocess.run", side_effect=mock_run):
            with patch("cmk.dev_deploy.watcher._get_untracked_files", return_value=""):
                result = _get_content_hash("HEAD", tmp_path)

        assert isinstance(result, str)
        assert len(result) == 32

    def test_deleted_file_changes_hash(self, tmp_path: Path) -> None:
        """Deleting a dirty file changes the hash (deletion is detected)."""
        from cmk.dev_deploy.watcher import _get_content_hash

        (tmp_path / "a.py").write_text("content")

        mock_run = _make_subprocess_mock(unstaged="a.py\n")
        with patch("cmk.dev_deploy.watcher.subprocess.run", side_effect=mock_run):
            with patch("cmk.dev_deploy.watcher._get_untracked_files", return_value=""):
                hash_with_file = _get_content_hash("HEAD", tmp_path)

                # Delete the file
                (tmp_path / "a.py").unlink()
                hash_without_file = _get_content_hash("HEAD", tmp_path)

        assert hash_with_file != hash_without_file

    def test_includes_untracked_files(self, tmp_path: Path) -> None:
        """Untracked file content changes are detected in the hash."""
        from cmk.dev_deploy.watcher import _get_content_hash

        (tmp_path / "new_file.py").write_text("initial")

        mock_run = _make_subprocess_mock(unstaged="")
        with patch("cmk.dev_deploy.watcher.subprocess.run", side_effect=mock_run):
            with patch(
                "cmk.dev_deploy.watcher._get_untracked_files",
                return_value="new_file.py\n",
            ):
                hash1 = _get_content_hash("HEAD", tmp_path)

                (tmp_path / "new_file.py").write_text("changed")
                hash2 = _get_content_hash("HEAD", tmp_path)

        assert hash1 != hash2

    def test_empty_diff_returns_stable_hash(self, tmp_path: Path) -> None:
        """When all git commands return empty stdout, hash is stable across calls."""
        from cmk.dev_deploy.watcher import _get_content_hash

        mock_run = _make_subprocess_mock(unstaged="", staged="", untracked="")
        with patch("cmk.dev_deploy.watcher.subprocess.run", side_effect=mock_run):
            with patch("cmk.dev_deploy.watcher._get_untracked_files", return_value=""):
                hash1 = _get_content_hash("HEAD", tmp_path)
                hash2 = _get_content_hash("HEAD", tmp_path)

        assert hash1 == hash2
        assert len(hash1) == 32

    def test_subprocess_timeout_returns_empty_string(self, tmp_path: Path) -> None:
        """TimeoutExpired from subprocess.run returns empty string."""
        from cmk.dev_deploy.watcher import _get_content_hash

        with patch(
            "cmk.dev_deploy.watcher.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd=["git"], timeout=5),
        ):
            result = _get_content_hash("HEAD", tmp_path)

        assert result == ""

    def test_oserror_returns_empty_string(self, tmp_path: Path) -> None:
        """OSError from subprocess.run returns empty string."""
        from cmk.dev_deploy.watcher import _get_content_hash

        with patch(
            "cmk.dev_deploy.watcher.subprocess.run",
            side_effect=OSError("git not found"),
        ):
            result = _get_content_hash("HEAD", tmp_path)

        assert result == ""

    def test_sorted_deduplication(self, tmp_path: Path) -> None:
        """Same filename in both unstaged and staged is deduplicated; hash is deterministic."""
        from cmk.dev_deploy.watcher import _get_content_hash

        (tmp_path / "a.py").write_text("content")

        # "a.py" appears in both unstaged and staged
        mock_run = _make_subprocess_mock(unstaged="a.py\n", staged="a.py\n")
        with patch("cmk.dev_deploy.watcher.subprocess.run", side_effect=mock_run):
            with patch("cmk.dev_deploy.watcher._get_untracked_files", return_value=""):
                hash1 = _get_content_hash("HEAD", tmp_path)
                hash2 = _get_content_hash("HEAD", tmp_path)

        assert hash1 == hash2
        assert len(hash1) == 32

    def test_file_read_oserror_uses_error_sentinel(self, tmp_path: Path) -> None:
        """OSError during file read uses ERROR sentinel instead of crashing."""
        from cmk.dev_deploy.watcher import _get_content_hash

        (tmp_path / "locked.py").write_text("content")

        mock_run = _make_subprocess_mock(unstaged="locked.py\n")
        original_read_bytes = Path.read_bytes

        def _mock_read_bytes(self: Path) -> bytes:
            if self.name == "locked.py":
                raise PermissionError("Permission denied")
            return original_read_bytes(self)

        with patch("cmk.dev_deploy.watcher.subprocess.run", side_effect=mock_run):
            with patch("cmk.dev_deploy.watcher._get_untracked_files", return_value=""):
                with patch.object(Path, "read_bytes", _mock_read_bytes):
                    result = _get_content_hash("HEAD", tmp_path)

        assert isinstance(result, str)
        assert len(result) == 32


# ---------------------------------------------------------------------------
# TestWatchLoopHeartbeat
# ---------------------------------------------------------------------------


class TestWatchLoopHeartbeat:
    """Tests for the heartbeat counter in watch_loop()."""

    def _make_site(self) -> MagicMock:
        """Create a mock SiteInfo."""
        site = MagicMock()
        site.name = "test_site"
        site.root = Path("/omd/sites/test")
        site.build_commit = "abc123"
        return site

    def test_heartbeat_emitted_after_60_idle_polls(self) -> None:
        """Heartbeat is emitted once after 60 consecutive idle polls."""
        from cmk.dev_deploy.watcher import watch_loop

        site = self._make_site()
        sleep_count = 0

        def mock_sleep(_seconds: float) -> None:
            nonlocal sleep_count
            sleep_count += 1
            # After 61 sleeps (to allow the 60th idle poll to happen + 1 more),
            # stop the loop
            if sleep_count > 60:
                raise KeyboardInterrupt

        with (
            patch(
                "cmk.dev_deploy.watcher._get_content_hash",
                return_value="stable_hash",
            ),
            patch(
                "cmk.dev_deploy.watcher._get_state_diff_base",
                return_value="abc123",
            ),
            patch("cmk.dev_deploy.watcher.time.sleep", side_effect=mock_sleep),
            patch("cmk.dev_deploy.watcher.output") as mock_output,
        ):
            result = watch_loop(
                site,
                Path("/repo"),
                lambda: MagicMock(exit_code=0),
                supervisor=None,
            )

        assert result == 0
        mock_output.print_watch_heartbeat.assert_called_once_with(60)

    def test_heartbeat_resets_on_change(self) -> None:
        """Heartbeat counter resets when a change is detected before reaching 60."""
        from cmk.dev_deploy.watcher import watch_loop

        site = self._make_site()
        call_count = 0
        sleep_count = 0

        def mock_get_content_hash(_base: str | None, _root: Path) -> str:
            nonlocal call_count
            call_count += 1
            # Initial hash (call 1), then 59 idle polls (calls 2-60),
            # then change on call 61 (triggers deploy).
            # After deploy, re-hash calls return stable hash.
            if call_count <= 60:
                return "hash1"
            if call_count == 61:
                return "hash2"  # Change detected
            return "hash_post_deploy"

        deploy_result = MagicMock()
        deploy_result.exit_code = 0
        deploy_result.all_skipped = False
        deploy_result.services_restarted = 0
        deploy_result.deployed = ("python",)
        deploy_result.skipped = ()
        deploy_result.skipped_reasons = {}

        def mock_sleep(_seconds: float) -> None:
            nonlocal sleep_count
            sleep_count += 1
            if sleep_count > 65:
                raise KeyboardInterrupt

        with (
            patch(
                "cmk.dev_deploy.watcher._get_content_hash",
                side_effect=mock_get_content_hash,
            ),
            patch(
                "cmk.dev_deploy.watcher._get_state_diff_base",
                return_value="abc123",
            ),
            patch("cmk.dev_deploy.watcher.time.sleep", side_effect=mock_sleep),
            patch("cmk.dev_deploy.watcher.time.monotonic", side_effect=[0.0, 1.0]),
            patch("cmk.dev_deploy.watcher.output") as mock_output,
        ):
            result = watch_loop(
                site,
                Path("/repo"),
                lambda: deploy_result,
                supervisor=None,
            )

        assert result == 0
        # Heartbeat should NOT have been called -- counter reset at 59 polls
        mock_output.print_watch_heartbeat.assert_not_called()

    def test_no_heartbeat_before_60_polls(self) -> None:
        """No heartbeat is emitted if fewer than 60 idle polls occur."""
        from cmk.dev_deploy.watcher import watch_loop

        site = self._make_site()
        sleep_count = 0

        def mock_sleep(_seconds: float) -> None:
            nonlocal sleep_count
            sleep_count += 1
            if sleep_count > 58:
                raise KeyboardInterrupt

        with (
            patch(
                "cmk.dev_deploy.watcher._get_content_hash",
                return_value="stable_hash",
            ),
            patch(
                "cmk.dev_deploy.watcher._get_state_diff_base",
                return_value="abc123",
            ),
            patch("cmk.dev_deploy.watcher.time.sleep", side_effect=mock_sleep),
            patch("cmk.dev_deploy.watcher.output") as mock_output,
        ):
            result = watch_loop(
                site,
                Path("/repo"),
                lambda: MagicMock(exit_code=0),
                supervisor=None,
            )

        assert result == 0
        mock_output.print_watch_heartbeat.assert_not_called()


# ---------------------------------------------------------------------------
# TestWatchLoopMidDeployEdits
# ---------------------------------------------------------------------------


def _cycle_result(exit_code: int = 0) -> object:
    from cmk.dev_deploy.types import DeployCycleResult

    return DeployCycleResult(
        exit_code=exit_code,
        deployed=("wheels",),
        skipped=(),
        skipped_reasons={},
        services_restarted=0,
        all_skipped=False,
    )


def _run_watch_loop(hash_sequence: list[str], deploy_fn: MagicMock) -> None:
    """Drive watch_loop with a scripted _get_content_hash sequence.

    The loop is terminated by raising KeyboardInterrupt once the
    sequence is exhausted (clean shutdown path, exit code 0).
    """
    from cmk.dev_deploy import watcher

    hashes = iter(hash_sequence)

    def _scripted_hash(_base: object, _repo_root: object) -> str:
        try:
            return next(hashes)
        except StopIteration:
            raise KeyboardInterrupt from None

    with (
        patch.object(watcher, "_get_content_hash", side_effect=_scripted_hash),
        patch.object(watcher, "_get_state_diff_base", return_value="a" * 40),
        patch("cmk.dev_deploy.watcher.time.sleep"),
    ):
        rc = watcher.watch_loop(MagicMock(), Path("/repo"), deploy_fn)
    assert rc == 0


class TestWatchLoopMidDeployEdits:
    """Files edited while a deploy runs must trigger the next cycle."""

    def test_edit_during_deploy_triggers_second_cycle(self) -> None:
        deploy_fn = MagicMock(return_value=_cycle_result())
        _run_watch_loop(
            [
                "h0",  # initial baseline
                "h1",  # poll: change detected
                "h1",  # debounce re-hash
                # deploy 1 runs; the file is edited meanwhile:
                "h2",  # post-deploy snapshot != pre-deploy -> force next cycle
                "h2",  # poll: differs from forced "" baseline -> cycle 2
                "h2",  # debounce re-hash
                "h2",  # post-deploy snapshot == pre-deploy -> settle
                "h2",  # baseline against updated diff base
                # poll: sequence exhausted -> Ctrl-C
            ],
            deploy_fn,
        )
        assert deploy_fn.call_count == 2

    def test_unchanged_tree_deploys_once(self) -> None:
        deploy_fn = MagicMock(return_value=_cycle_result())
        _run_watch_loop(
            [
                "h0",  # initial baseline
                "h1",  # poll: change detected
                "h1",  # debounce re-hash
                "h1",  # post-deploy snapshot == pre-deploy
                "h9",  # baseline against updated diff base (absorbed)
                "h9",  # poll: no change
                # poll: sequence exhausted -> Ctrl-C
            ],
            deploy_fn,
        )
        assert deploy_fn.call_count == 1

    def test_change_reverted_within_debounce_skips_deploy(self) -> None:
        deploy_fn = MagicMock(return_value=_cycle_result())
        _run_watch_loop(
            [
                "h0",  # initial baseline
                "h1",  # poll: change detected
                "h0",  # debounce re-hash: back to baseline -> no deploy
                "h0",  # poll: no change
                # poll: sequence exhausted -> Ctrl-C
            ],
            deploy_fn,
        )
        deploy_fn.assert_not_called()


# ---------------------------------------------------------------------------
# TestGetStateDiffBase
# ---------------------------------------------------------------------------


class TestGetStateDiffBase:
    """The watcher must poll against the same diff base the cycle maintains."""

    def test_prefers_global_diff_base(self) -> None:
        from cmk.dev_deploy.state.deploy_state import DeployerState, DeployState
        from cmk.dev_deploy.watcher import _get_state_diff_base

        state = DeployState(
            diff_base_commit="d" * 40,
            deployers={
                "config_spec": DeployerState(
                    deployer="config_spec",
                    git_commit="0" * 40,  # stale per-deployer commit
                    dirty_file_hashes={},
                    deployed_at=0.0,
                )
            },
        )
        with patch("cmk.dev_deploy.watcher.load_state", return_value=state):
            assert _get_state_diff_base(MagicMock()) == "d" * 40

    def test_falls_back_to_deployer_commit(self) -> None:
        from cmk.dev_deploy.state.deploy_state import DeployerState, DeployState
        from cmk.dev_deploy.watcher import _get_state_diff_base

        state = DeployState(
            deployers={
                "config_spec": DeployerState(
                    deployer="config_spec",
                    git_commit="0" * 40,
                    dirty_file_hashes={},
                    deployed_at=0.0,
                )
            },
        )
        with patch("cmk.dev_deploy.watcher.load_state", return_value=state):
            assert _get_state_diff_base(MagicMock()) == "0" * 40

    def test_falls_back_to_site_build_commit(self) -> None:
        from cmk.dev_deploy.watcher import _get_state_diff_base

        site = MagicMock()
        site.build_commit = "b" * 40
        with patch("cmk.dev_deploy.watcher.load_state", return_value=None):
            assert _get_state_diff_base(site) == "b" * 40
