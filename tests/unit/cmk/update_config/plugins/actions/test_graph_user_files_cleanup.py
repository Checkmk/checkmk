#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from pathlib import Path

import pytest

from cmk.update_config.plugins.actions.graph_user_files_cleanup import (
    RemoveOrphanedGraphUserFiles,
)

LOGGER = logging.getLogger()

# The former renderer wrote these through save_user_file(), i.e. repr() of the value.
GRAPH_SIZE = "(84, 20)\n"
GRAPH_RANGES = (
    "{'time_range': (1755000000, 1755003600), 'step': 60, 'vertical_range': (0.0, 42.5)}\n"
)
GRAPH_PIN = "1755001800\n"


def test_remove_orphaned_files(tmp_path: Path) -> None:
    orphaned = {
        tmp_path / "cmkadmin" / "graph_size.mk": GRAPH_SIZE,
        tmp_path / "cmkadmin" / "graph_range_my_graph.mk": GRAPH_RANGES,
        tmp_path / "cmkadmin" / "graph_range_other_graph.mk": GRAPH_RANGES,
        tmp_path / "harry" / "graph_size.mk": GRAPH_SIZE,
    }
    kept = {
        tmp_path / "cmkadmin" / "graph_pin.mk": GRAPH_PIN,
        tmp_path / "cmkadmin" / "favorites.mk": "[]\n",
        # Not inside a user directory, so out of reach.
        tmp_path / "ldap_default_sync_time.mk": "1755000000.0\n",
        tmp_path / ".tmp_restore" / "graph_size.mk": GRAPH_SIZE,
    }
    for path, content in (orphaned | kept).items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

    RemoveOrphanedGraphUserFiles.remove_orphaned_files(tmp_path, LOGGER)

    assert [path for path in orphaned if path.exists()] == []
    surviving = {path: path.read_text() for path in kept if path.exists()}
    assert surviving == kept


def test_remove_orphaned_files_without_orphans(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Nobody ever resized a graph: nothing is removed, and nothing is reported."""
    untouched = {
        tmp_path / "cmkadmin" / "graph_pin.mk": GRAPH_PIN,
        tmp_path / "harry" / "favorites.mk": "[]\n",
    }
    for path, content in untouched.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

    with caplog.at_level(logging.INFO):
        RemoveOrphanedGraphUserFiles.remove_orphaned_files(tmp_path, LOGGER)

    surviving = {path: path.read_text() for path in untouched if path.exists()}
    assert surviving == untouched
    assert caplog.messages == []


def test_remove_orphaned_files_skips_symlinked_profiles(tmp_path: Path) -> None:
    """A symlink must not lead the sweep out of the profile directory."""
    profile_dir = tmp_path / "web"
    profile_dir.mkdir()
    # A sibling of the profile directory, so it is not swept as a profile of its own.
    outside = tmp_path / "elsewhere"
    outside.mkdir()
    (outside / "graph_size.mk").write_text(GRAPH_SIZE)
    (profile_dir / "cmkadmin").symlink_to(outside)

    RemoveOrphanedGraphUserFiles.remove_orphaned_files(profile_dir, LOGGER)

    assert (outside / "graph_size.mk").exists(), (
        "the sweep followed the symlink out of the profile directory"
    )


def test_remove_orphaned_files_without_profile_dir(tmp_path: Path) -> None:
    RemoveOrphanedGraphUserFiles.remove_orphaned_files(tmp_path / "web", LOGGER)
