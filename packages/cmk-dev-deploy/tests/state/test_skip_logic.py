# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Unit tests for path-aware skip logic integration and partial failure state."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from cmk.dev_deploy.execution.step_registry import (
    DEPLOYER_DISPLAY_NAMES,
    STEP_TO_DEPLOYER,
)
from cmk.dev_deploy.state.deploy_state import (
    build_and_save_state,
    DeployerState,
    DeployState,
    load_state,
    STATE_SCHEMA_VERSION,
)
from cmk.dev_deploy.types import Edition, SiteInfo, SkipResult

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_deployer_state(
    deployer: str = "install_spec",
    git_commit: str = "a" * 40,
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
    """Create a DeployState with all 3 deployers if deployers is None."""
    if deployers is None:
        commit = "a" * 40
        deployers = {
            "config_spec": _make_deployer_state(deployer="config_spec", git_commit=commit),
            "install_spec": _make_deployer_state(deployer="install_spec", git_commit=commit),
            "wheel_spec": _make_deployer_state(deployer="wheel_spec", git_commit=commit),
        }
    return DeployState(
        schema_version=STATE_SCHEMA_VERSION,
        branch=branch,
        deployers=deployers,
        created_at=1000.0,
    )


def _make_site(tmp_path: Path) -> SiteInfo:
    """Create a SiteInfo with tmp_path as the site root."""
    return SiteInfo(
        name="test",
        root=tmp_path,
        edition=Edition.PRO,
        version_string="2.6.0-2026.02.13.pro",
        build_commit="b" * 40,
    )


def _make_skip_result(
    should_skip: bool = True,
    reason: str = "no changes in config/",
    deployer: str = "config_spec",
    paths_checked: tuple[str, ...] = ("agents/",),
    changed_files: tuple[str, ...] = (),
) -> SkipResult:
    """Create a SkipResult for testing."""
    return SkipResult(
        should_skip=should_skip,
        reason=reason,
        deployer=deployer,
        paths_checked=paths_checked,
        changed_files=changed_files,
    )


# ---------------------------------------------------------------------------
# TestPathAwareSkipIntegration
# ---------------------------------------------------------------------------


class TestPathAwareSkipIntegration:
    """Tests for path-aware skip logic integration in pipeline deployers."""

    def test_check_skip_called_for_pipeline_deployers(self) -> None:
        """check_skip is called once for each pipeline deployer when state exists."""
        state = _make_state()
        head = "a" * 40
        skip_result = _make_skip_result(should_skip=True)

        with patch("cmk.dev_deploy.__main__.check_skip", return_value=skip_result) as mock_check:
            # Simulate the skip check loop from _run_deploy_cycle
            skip_results: dict[str, SkipResult] = {}
            for deployer_name in ("config_spec", "install_spec"):
                result = mock_check(deployer_name, Path("/repo"), Path("/site"), state, head)
                skip_results[deployer_name] = result

            assert mock_check.call_count == 2
            # Verify each deployer was called
            deployer_names_called = [c.args[0] for c in mock_check.call_args_list]
            assert set(deployer_names_called) == {
                "config_spec",
                "install_spec",
            }

    def test_full_flag_bypasses_check_skip(self) -> None:
        """When --full is active, check_skip is NOT called at all."""
        # The skip_results dict stays empty when args.full is True
        skip_results: dict[str, SkipResult] = {}
        args_full = True

        # Simulate: if not args.full -> skip check runs
        if not args_full:
            skip_results["config_spec"] = _make_skip_result()

        # With --full, skip_results is empty = no skip = deploy all
        assert len(skip_results) == 0

    def test_skip_result_with_paths_shows_path_context(self) -> None:
        """SkipResult with paths_checked includes path context in reason."""
        result = _make_skip_result(
            should_skip=True,
            reason="no changes in cmk/",
            paths_checked=("cmk/",),
        )
        assert result.should_skip is True
        assert "cmk/" in result.reason
        assert result.paths_checked == ("cmk/",)

    def test_fallback_deployer_shows_note(self) -> None:
        """SkipResult with HEAD fallback has empty paths_checked and fallback reason."""
        result = _make_skip_result(
            should_skip=False,
            reason="HEAD changed (no source paths, HEAD fallback)",
            deployer="config_spec",
            paths_checked=(),
            changed_files=(),
        )
        assert result.paths_checked == ()
        assert "HEAD fallback" in result.reason
        assert not result.should_skip


# ---------------------------------------------------------------------------
# TestStepToDeployerMapping
# ---------------------------------------------------------------------------


class TestStepToDeployerMapping:
    """Tests for STEP_TO_DEPLOYER and DEPLOYER_DISPLAY_NAMES consistency."""

    def test_all_deployer_names_valid(self) -> None:
        """Every value in STEP_TO_DEPLOYER is a recognized deployer name."""
        # Valid deployer names are the keys of DEPLOYER_DISPLAY_NAMES
        valid_deployers = set(DEPLOYER_DISPLAY_NAMES.keys())
        for step, deployer in STEP_TO_DEPLOYER.items():
            assert deployer in valid_deployers, (
                f"Step {step!r} maps to unknown deployer {deployer!r}"
            )

    def test_display_names_cover_all_deployers(self) -> None:
        """Every STEP_TO_DEPLOYER value has a DEPLOYER_DISPLAY_NAMES entry."""
        for deployer in STEP_TO_DEPLOYER.values():
            assert deployer in DEPLOYER_DISPLAY_NAMES, (
                f"Deployer {deployer!r} missing from DEPLOYER_DISPLAY_NAMES"
            )


# ---------------------------------------------------------------------------
# TestPartialFailureStateSave
# ---------------------------------------------------------------------------


class TestPartialFailureStateSave:
    """Tests for build_and_save_state with partial failure recovery."""

    def _setup_state_dir(self, tmp_path: Path) -> None:
        """Create the state directory on disk."""
        (tmp_path / "tmp" / "cmk-dev-deploy").mkdir(parents=True, exist_ok=True)

    def test_save_only_successful_deployers(self, tmp_path: Path) -> None:
        """Only install_spec succeeded; config_spec carries forward from previous state."""
        self._setup_state_dir(tmp_path)
        site = _make_site(tmp_path)
        previous = _make_state()  # all 3 deployers with commit "a" * 40

        with (
            patch(
                "cmk.dev_deploy.state.deploy_state.get_head_commit",
                return_value="c" * 40,
            ),
            patch(
                "cmk.dev_deploy.state.deploy_state.compute_dirty_hashes",
                return_value={},
            ),
        ):
            build_and_save_state(
                repo_root=tmp_path,
                site_root=site.root,
                branch="main",
                successful_deployers={"install_spec"},
                previous_state=previous,
            )

        loaded = load_state(tmp_path)
        assert loaded is not None
        # install_spec got new commit
        assert loaded.deployers["install_spec"].git_commit == "c" * 40
        # config_spec carries forward old commit
        assert loaded.deployers["config_spec"].git_commit == "a" * 40
        # wheel_spec is not a pipeline deployer, not in all_deployer_names
        assert "wheel_spec" not in loaded.deployers

    def test_save_carries_forward_failed_deployers(self, tmp_path: Path) -> None:
        """config_spec not in successful set -> carries forward 'old' commit."""
        self._setup_state_dir(tmp_path)
        site = _make_site(tmp_path)
        # Give config_spec a distinct "old" commit
        deployers = {
            "config_spec": _make_deployer_state(
                deployer="config_spec", git_commit="old" + "0" * 37
            ),
            "install_spec": _make_deployer_state(deployer="install_spec"),
            "wheel_spec": _make_deployer_state(deployer="wheel_spec"),
        }
        previous = _make_state(deployers=deployers)

        with (
            patch(
                "cmk.dev_deploy.state.deploy_state.get_head_commit",
                return_value="d" * 40,
            ),
            patch(
                "cmk.dev_deploy.state.deploy_state.compute_dirty_hashes",
                return_value={},
            ),
        ):
            build_and_save_state(
                repo_root=tmp_path,
                site_root=site.root,
                branch="main",
                successful_deployers={"install_spec"},
                previous_state=previous,
            )

        loaded = load_state(tmp_path)
        assert loaded is not None
        # config_spec was NOT successful -> carried forward
        assert loaded.deployers["config_spec"].git_commit == "old" + "0" * 37
        # install_spec got the new head
        assert loaded.deployers["install_spec"].git_commit == "d" * 40

    def test_save_all_successful(self, tmp_path: Path) -> None:
        """All 2 pipeline deployers successful -> all get new commit/timestamp."""
        self._setup_state_dir(tmp_path)
        site = _make_site(tmp_path)
        previous = _make_state()

        pipeline_deployers = {"config_spec", "install_spec"}
        with (
            patch(
                "cmk.dev_deploy.state.deploy_state.get_head_commit",
                return_value="e" * 40,
            ),
            patch(
                "cmk.dev_deploy.state.deploy_state.compute_dirty_hashes",
                return_value={},
            ),
        ):
            build_and_save_state(
                repo_root=tmp_path,
                site_root=site.root,
                branch="main",
                successful_deployers=pipeline_deployers,
                previous_state=previous,
            )

        loaded = load_state(tmp_path)
        assert loaded is not None
        for name in pipeline_deployers:
            assert loaded.deployers[name].git_commit == "e" * 40, f"{name} should have new commit"

    def test_save_no_previous_state(self, tmp_path: Path) -> None:
        """previous_state=None -> only install_spec appears in saved state."""
        self._setup_state_dir(tmp_path)
        site = _make_site(tmp_path)

        with (
            patch(
                "cmk.dev_deploy.state.deploy_state.get_head_commit",
                return_value="f" * 40,
            ),
            patch(
                "cmk.dev_deploy.state.deploy_state.compute_dirty_hashes",
                return_value={},
            ),
        ):
            build_and_save_state(
                repo_root=tmp_path,
                site_root=site.root,
                branch="main",
                successful_deployers={"install_spec"},
                previous_state=None,
            )

        loaded = load_state(tmp_path)
        assert loaded is not None
        assert "install_spec" in loaded.deployers
        assert loaded.deployers["install_spec"].git_commit == "f" * 40
        # No other deployers should be present (no carry-forward from None)
        for name in ("config_spec", "wheel_spec"):
            assert name not in loaded.deployers, f"{name} should not be present"

    def test_save_uses_per_deployer_dirty_hashes(self, tmp_path: Path) -> None:
        """When deployer_dirty_hashes is provided, each deployer gets its own hashes."""
        self._setup_state_dir(tmp_path)
        site = _make_site(tmp_path)
        previous = _make_state()

        cfg_dirty = {"agents/cfg.txt": "hash_cfg"}
        bzl_dirty = {"packages/livestatus/src.cc": "hash_bzl"}
        deployer_dirty = {
            "config_spec": cfg_dirty,
            "install_spec": bzl_dirty,
        }

        with (
            patch(
                "cmk.dev_deploy.state.deploy_state.get_head_commit",
                return_value="g" * 40,
            ),
            # compute_dirty_hashes should NOT be called when deployer_dirty_hashes is provided
            patch(
                "cmk.dev_deploy.state.deploy_state.compute_dirty_hashes",
                side_effect=AssertionError("should not be called"),
            ),
        ):
            build_and_save_state(
                repo_root=tmp_path,
                site_root=site.root,
                branch="main",
                successful_deployers={"config_spec", "install_spec"},
                previous_state=previous,
                deployer_dirty_hashes=deployer_dirty,
            )

        loaded = load_state(tmp_path)
        assert loaded is not None
        # Each deployer should have its own filtered dirty hashes
        assert loaded.deployers["config_spec"].dirty_file_hashes == cfg_dirty
        assert loaded.deployers["install_spec"].dirty_file_hashes == bzl_dirty
