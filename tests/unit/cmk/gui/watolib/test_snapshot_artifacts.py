#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator

import pytest

from cmk.gui.config import Config
from cmk.gui.watolib.activate_changes import ActivateChangesManager
from cmk.gui.watolib.hosts_and_folders import FolderTree, make_folder_tree
from cmk.gui.watolib.snapshot_artifacts import snapshot_artifact_registry, SnapshotArtifact
from cmk.livestatus_client import SiteConfigurations


@pytest.fixture(name="written_from")
def fixture_written_from() -> Iterator[list[FolderTree]]:
    """The trees a snapshot artifact registered for the test was written from"""
    trees: list[FolderTree] = []
    snapshot_artifact_registry.register(SnapshotArtifact(ident="test", write=trees.append))
    try:
        yield trees
    finally:
        snapshot_artifact_registry.unregister("test")


@pytest.mark.usefixtures("with_admin_login", "load_config")
def test_the_activation_writes_the_artifacts_from_its_tree(written_from: list[FolderTree]) -> None:
    tree = make_folder_tree(Config())

    ActivateChangesManager()._pre_activate_changes(  # noqa: SLF001
        tree, SiteConfigurations({}), debug=True
    )

    assert written_from == [tree]


@pytest.mark.usefixtures("with_admin_login", "load_config", "remote_site")
def test_a_remote_site_writes_no_artifacts(written_from: list[FolderTree]) -> None:
    """A remote site gets them from the central site through the config sync."""
    ActivateChangesManager()._pre_activate_changes(  # noqa: SLF001
        make_folder_tree(Config()), SiteConfigurations({}), debug=True
    )

    assert not written_from
