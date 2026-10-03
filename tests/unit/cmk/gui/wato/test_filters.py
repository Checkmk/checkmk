#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import shutil
from collections.abc import Iterator

import pytest

from livestatus import SiteConfigurations

from cmk.ccc.site import SiteId
from cmk.gui.config import Config
from cmk.gui.logged_in import LoggedInSuperUser
from cmk.gui.visuals.filter import FilterGroup
from cmk.gui.wato.filters import FilterWatoFolder
from cmk.gui.watolib.hosts_and_folders import Folder, folder_tree
from cmk.gui.watolib.pending_changes import NoopPendingChangesStore, PendingChanges
from cmk.web.utils.request_cache import RequestCache


def _noop_pending_changes() -> PendingChanges:
    return PendingChanges(
        activation_sites=SiteConfigurations({}),
        local_site=SiteId("NO_SITE"),
        acting_user=None,
        store=NoopPendingChangesStore(),
        hooks=(),
    )


@pytest.fixture(name="folder_sub")
def fixture_folder_sub(request_context: None) -> Iterator[Folder]:  # noqa: ARG001  # Unused fixtures are needed for setup side effects
    """The folder "sub" titled "Sub" below the main folder of the request"""
    root_folder = folder_tree().root_folder()
    try:
        yield root_folder.create_subfolder(
            name="sub",
            title="Sub",
            attributes={},
            pprint_value=False,
            pending_changes=_noop_pending_changes(),
            acting_user=LoggedInSuperUser(),
        )
    finally:
        shutil.rmtree(root_folder.filesystem_path(), ignore_errors=True)
        os.makedirs(root_folder.filesystem_path())


def test_the_heading_shows_the_current_title_of_the_folder(folder_sub: Folder) -> None:
    folder_filter = FilterWatoFolder(
        ident="wato_folder",
        title="Folder",
        sort_index=10,
        info="host",
        htmlvars=["wato_folder"],
        link_columns=[],
        group=FilterGroup.FOLDER,
    )
    folder_filter.heading_info({"wato_folder": "sub"}, RequestCache(Config()))

    folder_sub.edit(
        "Renamed",
        {},
        pprint_value=False,
        pending_changes=_noop_pending_changes(),
        acting_user=LoggedInSuperUser(),
    )

    assert folder_filter.heading_info({"wato_folder": "sub"}, RequestCache(Config())) == "Renamed"
