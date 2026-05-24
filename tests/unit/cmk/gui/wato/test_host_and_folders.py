#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import shutil
from collections.abc import Generator

import pytest

from livestatus import SiteConfigurations

from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.gui.watolib.hosts_and_folders import Folder, folder_tree, FolderSiteStats
from cmk.gui.watolib.pending_changes import NoopPendingChangesStore, PendingChanges


def _noop_pending_changes() -> PendingChanges:
    return PendingChanges(
        activation_sites=SiteConfigurations({}),
        local_site=SiteId("NO_SITE"),
        acting_user=None,
        store=NoopPendingChangesStore(),
        hooks=(),
    )


@pytest.mark.usefixtures("request_context", "with_admin_login")
class TestFolderSiteStats:
    @pytest.fixture
    def folder_site_stats(self) -> Generator[FolderSiteStats]:
        root_folder = folder_tree().root_folder()
        self._setup_fs(root_folder)
        yield FolderSiteStats.build(root_folder)
        self._cleanup_fs(root_folder)

    def test_host_stats(self, folder_site_stats: FolderSiteStats) -> None:
        values = {host.name() for host in folder_site_stats.hosts[SiteId("NO_SITE")]}
        expected = {"main_host", "sub_host", "nested_host"}
        assert values == expected

    def test_folder_stats(self, folder_site_stats: FolderSiteStats) -> None:
        values = {folder.name() for folder in folder_site_stats.folders[SiteId("NO_SITE")]}
        expected = {"", "sub", "sub/nested"}
        assert values == expected

    def _setup_fs(self, folder: Folder) -> None:
        folder.create_hosts(
            [(HostName("main_host"), {}, None)],
            pprint_value=False,
            pending_changes=_noop_pending_changes(),
        )
        sub = folder.create_subfolder(
            name="sub",
            title="",
            attributes={},
            pprint_value=False,
            pending_changes=_noop_pending_changes(),
        )
        sub.create_hosts(
            [(HostName("sub_host"), {}, None)],
            pprint_value=False,
            pending_changes=_noop_pending_changes(),
        )
        nest = sub.create_subfolder(
            name="sub/nested",
            title="",
            attributes={},
            pprint_value=False,
            pending_changes=_noop_pending_changes(),
        )
        nest.create_hosts(
            [(HostName("nested_host"), {}, None)],
            pprint_value=False,
            pending_changes=_noop_pending_changes(),
        )

    def _cleanup_fs(self, root_folder: Folder) -> None:
        shutil.rmtree(root_folder.filesystem_path(), ignore_errors=True)
        os.makedirs(root_folder.filesystem_path())
