# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Unit tests for partial dirty-file revert detection."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from cmk.dev_deploy.state.deploy_state import (
    DeployerState,
    DeployState,
    STATE_SCHEMA_VERSION,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_state(
    deployers: dict[str, DeployerState] | None = None,
) -> DeployState:
    return DeployState(
        schema_version=STATE_SCHEMA_VERSION,
        branch="master",
        deployers=deployers or {},
        created_at=0.0,
        diff_base_commit="a" * 40,
    )


def _make_deployer(
    name: str = "install_spec",
    dirty: dict[str, str] | None = None,
) -> DeployerState:
    return DeployerState(
        deployer=name,
        git_commit="a" * 40,
        dirty_file_hashes=dirty or {},
        deployed_at=0.0,
    )


# ---------------------------------------------------------------------------
# Tests for has_reverted_dirty_files
# ---------------------------------------------------------------------------


class TestHasRevertedDirtyFiles:
    """Tests for has_reverted_dirty_files helper."""

    def test_some_reverted(self) -> None:
        """Returns True when a previously-dirty file is now clean."""
        state = _make_state(
            deployers={
                "install_spec": _make_deployer(
                    dirty={"a.cc": "hash1", "b.cc": "hash2"}
                ),
            }
        )
        with patch(
            "cmk.dev_deploy.state.deploy_state.get_dirty_files",
            return_value=["b.cc"],  # a.cc was reverted
        ):
            from cmk.dev_deploy.state.change_detector import has_reverted_dirty_files

            assert has_reverted_dirty_files(state, Path("/repo")) is True

    def test_all_still_dirty(self) -> None:
        """Returns False when all state-recorded dirty files are still dirty."""
        state = _make_state(
            deployers={
                "install_spec": _make_deployer(
                    dirty={"a.cc": "hash1", "b.cc": "hash2"}
                ),
            }
        )
        with patch(
            "cmk.dev_deploy.state.deploy_state.get_dirty_files",
            return_value=["a.cc", "b.cc", "c.cc"],
        ):
            from cmk.dev_deploy.state.change_detector import has_reverted_dirty_files

            assert has_reverted_dirty_files(state, Path("/repo")) is False

    def test_no_dirty_in_state(self) -> None:
        """Returns False when state has no dirty file hashes."""
        state = _make_state(
            deployers={
                "install_spec": _make_deployer(dirty={}),
            }
        )
        from cmk.dev_deploy.state.change_detector import has_reverted_dirty_files

        assert has_reverted_dirty_files(state, Path("/repo")) is False

    def test_all_reverted(self) -> None:
        """Returns True when all previously-dirty files are reverted."""
        state = _make_state(
            deployers={
                "install_spec": _make_deployer(dirty={"a.cc": "hash1"}),
            }
        )
        with patch(
            "cmk.dev_deploy.state.deploy_state.get_dirty_files",
            return_value=[],
        ):
            from cmk.dev_deploy.state.change_detector import has_reverted_dirty_files

            assert has_reverted_dirty_files(state, Path("/repo")) is True

    def test_multiple_deployers(self) -> None:
        """Checks dirty files across all deployers."""
        state = _make_state(
            deployers={
                "install_spec": _make_deployer(
                    name="install_spec", dirty={"a.cc": "hash1"}
                ),
                "config_spec": _make_deployer(
                    name="config_spec", dirty={"b.cfg": "hash2"}
                ),
            }
        )
        # a.cc still dirty, b.cfg reverted
        with patch(
            "cmk.dev_deploy.state.deploy_state.get_dirty_files",
            return_value=["a.cc"],
        ):
            from cmk.dev_deploy.state.change_detector import has_reverted_dirty_files

            assert has_reverted_dirty_files(state, Path("/repo")) is True
