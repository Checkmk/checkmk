# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Unit tests for cmk.dev_deploy.path_skip (path-aware skip decisions)."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from cmk.dev_deploy.state.deploy_state import (
    DeployerState,
    DeployState,
    STATE_SCHEMA_VERSION,
)
from cmk.dev_deploy.state.path_skip import _format_short_paths, check_skip
from cmk.dev_deploy.types import SkipResult

# ---------------------------------------------------------------------------
# Module-level mock target constants
# ---------------------------------------------------------------------------

_RESOLVE = "cmk.dev_deploy.execution.source_paths.resolve_source_paths"
_DIRTY = "cmk.dev_deploy.state.path_skip.compute_dirty_hashes"
_SUBPROCESS = "cmk.dev_deploy.state.path_skip.run_checked"
_BUILD_COMMIT = "cmk.dev_deploy.state.path_skip.read_build_commit"
_VALIDATE_COMMIT = "cmk.dev_deploy.state.path_skip._validate_commit_exists"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

REPO = Path("/fake/repo")
SITE = Path("/omd/sites/test")
HEAD = "a" * 40
OLD_COMMIT = "b" * 40
BUILD_COMMIT = "c" * 40


def _make_deployer_state(
    deployer: str = "config_spec",
    git_commit: str = OLD_COMMIT,
    dirty: dict[str, str] | None = None,
    deployed_at: float = 1000.0,
) -> DeployerState:
    """Create a DeployerState with sensible defaults for testing."""
    return DeployerState(
        deployer=deployer,
        git_commit=git_commit,
        dirty_file_hashes=dirty if dirty is not None else {},
        deployed_at=deployed_at,
    )


def _make_state(
    deployers: dict[str, DeployerState] | None = None,
    branch: str = "main",
) -> DeployState:
    """Create a DeployState with sensible defaults."""
    if deployers is None:
        deployers = {
            "config_spec": _make_deployer_state(deployer="config_spec"),
        }
    return DeployState(
        schema_version=STATE_SCHEMA_VERSION,
        branch=branch,
        deployers=deployers,
        created_at=1000.0,
    )


def _completed_process(
    stdout: str = "",
    stderr: str = "",
    returncode: int = 0,
) -> subprocess.CompletedProcess[str]:
    """Create a subprocess.CompletedProcess for mocking."""
    return subprocess.CompletedProcess(
        args=["git"], stdout=stdout, stderr=stderr, returncode=returncode
    )


# ---------------------------------------------------------------------------
# TestPathFilteredSkip — Core path-aware scenarios
# ---------------------------------------------------------------------------


class TestPathFilteredSkip:
    """Core path-aware skip decision scenarios."""

    def test_skip_when_no_files_changed_in_paths(self) -> None:
        """Deployer has paths, state has old commit, git diff returns empty -> skip."""
        state = _make_state(deployers={"config_spec": _make_deployer_state(deployer="config_spec")})

        with (
            patch(_RESOLVE, return_value=("cmk/gui/",)),
            patch(_DIRTY, return_value={}),
            patch(_VALIDATE_COMMIT, return_value=None),
            patch(_SUBPROCESS, return_value=_completed_process(stdout="")),
        ):
            result = check_skip("config_spec", REPO, SITE, state, HEAD)

        assert isinstance(result, SkipResult)
        assert result.should_skip is True
        assert result.changed_files == ()

    def test_deploy_when_files_changed_in_paths(self) -> None:
        """git diff returns changed files -> deploy."""
        state = _make_state(deployers={"config_spec": _make_deployer_state(deployer="config_spec")})

        with (
            patch(_RESOLVE, return_value=("cmk/gui/",)),
            patch(_DIRTY, return_value={}),
            patch(_VALIDATE_COMMIT, return_value=None),
            patch(
                _SUBPROCESS,
                return_value=_completed_process(stdout="cmk/gui/views.py\ncmk/gui/models.py\n"),
            ),
        ):
            result = check_skip("config_spec", REPO, SITE, state, HEAD)

        assert result.should_skip is False
        assert "cmk/gui/views.py" in result.changed_files
        assert "cmk/gui/models.py" in result.changed_files

    def test_skip_unrelated_commit(self) -> None:
        """HEAD moved forward, but git diff filtered to deployer's paths returns empty -> skip.

        This is the KEY v1.3 scenario: unrelated commit moves HEAD but deployer paths unchanged.
        """
        new_head = "f" * 40  # HEAD moved forward from OLD_COMMIT
        state = _make_state(deployers={"config_spec": _make_deployer_state(deployer="config_spec")})

        with (
            patch(_RESOLVE, return_value=("cmk/gui/",)),
            patch(_DIRTY, return_value={}),
            patch(_VALIDATE_COMMIT, return_value=None),
            patch(_SUBPROCESS, return_value=_completed_process(stdout="")),
        ):
            result = check_skip("config_spec", REPO, SITE, state, new_head)

        assert result.should_skip is True
        assert result.changed_files == ()

    def test_deploy_related_commit(self) -> None:
        """HEAD moved forward, git diff filtered to deployer's paths returns files -> deploy."""
        new_head = "f" * 40
        state = _make_state(deployers={"config_spec": _make_deployer_state(deployer="config_spec")})

        with (
            patch(_RESOLVE, return_value=("cmk/gui/",)),
            patch(_DIRTY, return_value={}),
            patch(_VALIDATE_COMMIT, return_value=None),
            patch(
                _SUBPROCESS,
                return_value=_completed_process(stdout="cmk/gui/views.py\n"),
            ),
        ):
            result = check_skip("config_spec", REPO, SITE, state, new_head)

        assert result.should_skip is False
        assert "cmk/gui/views.py" in result.changed_files

    def test_result_contains_paths_checked(self) -> None:
        """Verify paths_checked field in SkipResult matches the source paths used."""
        state = _make_state(deployers={"config_spec": _make_deployer_state(deployer="config_spec")})

        with (
            patch(_RESOLVE, return_value=("cmk/gui/", "cmk/base/")),
            patch(_DIRTY, return_value={}),
            patch(_VALIDATE_COMMIT, return_value=None),
            patch(_SUBPROCESS, return_value=_completed_process(stdout="")),
        ):
            result = check_skip("config_spec", REPO, SITE, state, HEAD)

        assert result.paths_checked == ("cmk/gui/", "cmk/base/")

    def test_result_contains_deployer_name(self) -> None:
        """Verify deployer field in SkipResult matches the deployer name."""
        state = _make_state(deployers={"config_spec": _make_deployer_state(deployer="config_spec")})

        with (
            patch(_RESOLVE, return_value=("agents/",)),
            patch(_DIRTY, return_value={}),
            patch(_VALIDATE_COMMIT, return_value=None),
            patch(_SUBPROCESS, return_value=_completed_process(stdout="")),
        ):
            result = check_skip("config_spec", REPO, SITE, state, HEAD)

        assert result.deployer == "config_spec"


# ---------------------------------------------------------------------------
# TestDirtyHashScoping — Per-deployer dirty file filtering
# ---------------------------------------------------------------------------


class TestDirtyHashScoping:
    """Per-deployer dirty file filtering scenarios."""

    def test_skip_when_dirty_file_outside_paths(self) -> None:
        """Dirty file in cmk/ec/ but deployer watches cmk/gui/ -> skip.

        The dirty hash scoping ensures files outside the deployer's paths
        do not trigger a redeploy.
        """
        state = _make_state(deployers={"config_spec": _make_deployer_state(deployer="config_spec")})

        with (
            patch(_RESOLVE, return_value=("cmk/gui/",)),
            # compute_dirty_hashes with path_prefixes=("cmk/gui/",) returns empty
            # because dirty file cmk/ec/main.py is outside cmk/gui/
            patch(_DIRTY, return_value={}),
            patch(_VALIDATE_COMMIT, return_value=None),
            patch(_SUBPROCESS, return_value=_completed_process(stdout="")),
        ):
            result = check_skip("config_spec", REPO, SITE, state, HEAD)

        assert result.should_skip is True

    def test_deploy_when_dirty_file_inside_paths(self) -> None:
        """Dirty file in cmk/gui/foo.py AND deployer watches cmk/gui/ -> deploy."""
        state = _make_state(deployers={"config_spec": _make_deployer_state(deployer="config_spec")})

        with (
            patch(_RESOLVE, return_value=("cmk/gui/",)),
            # compute_dirty_hashes returns a file inside the watched path
            patch(_DIRTY, return_value={"cmk/gui/foo.py": "abc123"}),
            patch(_VALIDATE_COMMIT, return_value=None),
            # No committed changes
            patch(_SUBPROCESS, return_value=_completed_process(stdout="")),
        ):
            result = check_skip("config_spec", REPO, SITE, state, HEAD)

        assert result.should_skip is False
        assert "cmk/gui/foo.py" in result.changed_files

    def test_deploy_when_dirty_hashes_changed_since_last_deploy(self) -> None:
        """Same commit, but dirty hashes differ from state -> deploy."""
        # State recorded dirty hashes from last deploy
        state = _make_state(
            deployers={
                "config_spec": _make_deployer_state(
                    deployer="config_spec",
                    git_commit=HEAD,  # Same commit as HEAD
                    dirty={"cmk/gui/old.py": "old_hash"},
                )
            }
        )

        with (
            patch(_RESOLVE, return_value=("cmk/gui/",)),
            # Current dirty hashes differ from state
            patch(_DIRTY, return_value={"cmk/gui/new.py": "new_hash"}),
            patch(_VALIDATE_COMMIT, return_value=None),
            # No committed changes (same commit)
            patch(_SUBPROCESS, return_value=_completed_process(stdout="")),
        ):
            result = check_skip("config_spec", REPO, SITE, state, HEAD)

        assert result.should_skip is False

    def test_skip_when_dirty_hashes_match(self) -> None:
        """Same commit, dirty hashes match state -> skip."""
        dirty = {"cmk/gui/foo.py": "abc123"}
        state = _make_state(
            deployers={
                "config_spec": _make_deployer_state(
                    deployer="config_spec",
                    git_commit=HEAD,  # Same commit as HEAD
                    dirty=dirty,
                )
            }
        )

        with (
            patch(_RESOLVE, return_value=("cmk/gui/",)),
            # Current dirty hashes match state
            patch(_DIRTY, return_value=dict(dirty)),
            patch(_VALIDATE_COMMIT, return_value=None),
            # No committed changes (same commit)
            patch(_SUBPROCESS, return_value=_completed_process(stdout="")),
        ):
            result = check_skip("config_spec", REPO, SITE, state, HEAD)

        assert result.should_skip is True


# ---------------------------------------------------------------------------
# TestHeadFallback — Deployers without source paths
# ---------------------------------------------------------------------------


class TestHeadFallback:
    """HEAD fallback mode for deployers without source path metadata."""

    def test_head_fallback_skip_when_head_unchanged(self) -> None:
        """resolve_source_paths returns None, same HEAD -> skip."""
        state = _make_state(
            deployers={
                "custom_deployer": _make_deployer_state(
                    deployer="custom_deployer",
                    git_commit=HEAD,
                )
            }
        )

        with (
            patch(_RESOLVE, return_value=None),
            patch(_DIRTY, return_value={}),
        ):
            result = check_skip("custom_deployer", REPO, SITE, state, HEAD)

        assert result.should_skip is True
        assert "HEAD fallback" in result.reason

    def test_head_fallback_deploy_when_head_changed(self) -> None:
        """resolve_source_paths returns None, HEAD differs -> deploy."""
        new_head = "f" * 40
        state = _make_state(
            deployers={
                "custom_deployer": _make_deployer_state(
                    deployer="custom_deployer",
                    git_commit=OLD_COMMIT,  # different from new_head
                )
            }
        )

        with (
            patch(_RESOLVE, return_value=None),
            patch(_DIRTY, return_value={}),
        ):
            result = check_skip("custom_deployer", REPO, SITE, state, new_head)

        assert result.should_skip is False
        assert "HEAD" in result.reason

    def test_head_fallback_deploy_when_no_state(self) -> None:
        """resolve_source_paths returns None, state is None -> deploy."""
        with patch(_RESOLVE, return_value=None):
            result = check_skip("custom_deployer", REPO, SITE, None, HEAD)

        assert result.should_skip is False

    def test_head_fallback_paths_checked_empty(self) -> None:
        """Verify paths_checked is empty tuple for HEAD fallback."""
        state = _make_state(
            deployers={
                "custom_deployer": _make_deployer_state(
                    deployer="custom_deployer",
                    git_commit=HEAD,
                )
            }
        )

        with (
            patch(_RESOLVE, return_value=None),
            patch(_DIRTY, return_value={}),
        ):
            result = check_skip("custom_deployer", REPO, SITE, state, HEAD)

        assert result.paths_checked == ()


# ---------------------------------------------------------------------------
# TestFirstDeploy — First deploy with site build commit baseline
# ---------------------------------------------------------------------------


class TestFirstDeploy:
    """First deploy with site build commit baseline."""

    def test_first_deploy_with_build_commit_and_changes(self) -> None:
        """No deployer state, site has build commit, git diff shows changes -> deploy."""
        # State exists but deployer not in it
        state = _make_state(deployers={})

        with (
            patch(_RESOLVE, return_value=("cmk/gui/",)),
            patch(_BUILD_COMMIT, return_value=BUILD_COMMIT),
            patch(_DIRTY, return_value={}),
            patch(
                _SUBPROCESS,
                return_value=_completed_process(stdout="cmk/gui/views.py\n"),
            ),
        ):
            result = check_skip("config_spec", REPO, SITE, state, HEAD)

        assert result.should_skip is False
        assert "cmk/gui/views.py" in result.changed_files
        assert "first deploy" in result.reason

    def test_first_deploy_with_build_commit_no_changes(self) -> None:
        """No deployer state, site has build commit, git diff shows NO changes -> deploy.

        Note: _check_skip_first_deploy always returns should_skip=False when
        there is a build commit, because it constructs the reason as
        'first deploy from build commit ...' and returns should_skip=False.
        """
        state = _make_state(deployers={})

        with (
            patch(_RESOLVE, return_value=("cmk/gui/",)),
            patch(_BUILD_COMMIT, return_value=BUILD_COMMIT),
            patch(_DIRTY, return_value={}),
            patch(_SUBPROCESS, return_value=_completed_process(stdout="")),
        ):
            result = check_skip("config_spec", REPO, SITE, state, HEAD)

        # First deploy always deploys (even with no diff) — the implementation
        # returns should_skip=False with "first deploy from build commit ..."
        assert result.should_skip is False
        assert "first deploy" in result.reason
        assert result.changed_files == ()

    def test_first_deploy_no_build_commit(self) -> None:
        """No deployer state AND no site build commit -> deploy, reason contains 'no baseline'."""
        state = _make_state(deployers={})

        with (
            patch(_RESOLVE, return_value=("cmk/gui/",)),
            patch(_BUILD_COMMIT, return_value=None),
        ):
            result = check_skip("config_spec", REPO, SITE, state, HEAD)

        assert result.should_skip is False
        assert "no baseline" in result.reason


# ---------------------------------------------------------------------------
# TestFailedStateOverride — Failed/missing state
# ---------------------------------------------------------------------------


class TestFailedStateOverride:
    """Failed/missing state always triggers deployment."""

    def test_deploy_when_state_is_none(self) -> None:
        """state=None -> deploy (always deploy on first run)."""
        with (
            patch(_RESOLVE, return_value=("cmk/gui/",)),
            patch(_BUILD_COMMIT, return_value=None),
        ):
            result = check_skip("config_spec", REPO, SITE, None, HEAD)

        assert result.should_skip is False

    def test_deploy_when_deployer_not_in_state(self) -> None:
        """state exists but deployer_name not in deployers dict -> deploy."""
        state = _make_state(deployers={})  # No deployers

        with (
            patch(_RESOLVE, return_value=("cmk/gui/",)),
            patch(_BUILD_COMMIT, return_value=None),
        ):
            result = check_skip("config_spec", REPO, SITE, state, HEAD)

        assert result.should_skip is False


# ---------------------------------------------------------------------------
# TestEmptySourcePaths — Empty paths edge case
# ---------------------------------------------------------------------------


class TestEmptySourcePaths:
    """Empty source paths always skip (no source files = nothing to deploy)."""

    def test_skip_when_source_paths_empty_tuple(self) -> None:
        """resolve_source_paths returns () (empty tuple, not None) -> skip."""
        with patch(_RESOLVE, return_value=()):
            result = check_skip("config_spec", REPO, SITE, None, HEAD)

        assert result.should_skip is True
        assert "no source files" in result.reason


# ---------------------------------------------------------------------------
# TestGitFailures — Error handling
# ---------------------------------------------------------------------------


class TestGitFailures:
    """Git failure error handling."""

    def test_git_diff_failure_raises_error(self) -> None:
        """run_checked raises RuntimeError on non-zero git diff exit."""
        state = _make_state(deployers={"config_spec": _make_deployer_state(deployer="config_spec")})

        with (
            patch(_RESOLVE, return_value=("cmk/gui/",)),
            patch(_VALIDATE_COMMIT, return_value=None),
            patch(
                _SUBPROCESS,
                side_effect=RuntimeError("git diff failed (exit 128): fatal: bad object"),
            ),
            pytest.raises(RuntimeError, match="git diff failed"),
        ):
            check_skip("config_spec", REPO, SITE, state, HEAD)

    def test_missing_old_commit_raises_error(self) -> None:
        """git cat-file -e for old commit fails -> RuntimeError raised."""
        state = _make_state(deployers={"config_spec": _make_deployer_state(deployer="config_spec")})

        with (
            patch(_RESOLVE, return_value=("cmk/gui/",)),
            patch(
                _VALIDATE_COMMIT,
                side_effect=RuntimeError(f"Commit {OLD_COMMIT[:12]} no longer exists in repo"),
            ),
            pytest.raises(RuntimeError, match="no longer exists"),
        ):
            check_skip("config_spec", REPO, SITE, state, HEAD)


# ---------------------------------------------------------------------------
# TestFormatShortPaths — _format_short_paths helper
# ---------------------------------------------------------------------------


class TestFormatShortPaths:
    """Tests for _format_short_paths() compact display formatting."""

    def test_single_path(self) -> None:
        assert _format_short_paths(("alpha",)) == "alpha"

    def test_two_paths(self) -> None:
        assert _format_short_paths(("alpha", "beta")) == "alpha, beta"

    def test_three_paths(self) -> None:
        assert _format_short_paths(("a", "b", "c")) == "a, b, c"

    def test_four_paths_truncated(self) -> None:
        assert _format_short_paths(("a", "b", "c", "d")) == "a, b, c (+1 more)"

    def test_six_paths_truncated(self) -> None:
        result = _format_short_paths(("a", "b", "c", "d", "e", "f"))
        assert result == "a, b, c (+3 more)"

    def test_trailing_slashes_stripped(self) -> None:
        assert _format_short_paths(("cmk/gui/",)) == "cmk/gui"

    def test_trailing_slashes_stripped_multiple(self) -> None:
        result = _format_short_paths(("cmk/gui/", "cmk/base/"))
        assert result == "cmk/gui, cmk/base"

    def test_trailing_slashes_with_truncation(self) -> None:
        result = _format_short_paths(("a/", "b/", "c/", "d/"))
        assert result == "a, b, c (+1 more)"
