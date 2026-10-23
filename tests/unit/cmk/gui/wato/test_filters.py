#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import shutil
from collections.abc import Iterator

import pytest
from werkzeug.test import create_environ

from livestatus import SiteConfigurations

from cmk.ccc.site import SiteId
from cmk.gui.config import Config
from cmk.gui.http import Request
from cmk.gui.logged_in import LoggedInSuperUser
from cmk.gui.visuals.filter import FilterGroup
from cmk.gui.wato._folder_titles import FolderTitles
from cmk.gui.wato.filters import FilterWatoFolder
from cmk.gui.wato.views import get_wato_folder
from cmk.gui.watolib.hosts_and_folders import Folder, make_folder_tree
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
def fixture_folder_sub() -> Iterator[Folder]:
    """The folder "sub" titled "Sub" below the main folder"""
    root_folder = make_folder_tree(Config()).root_folder()
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


def _folder_filter() -> FilterWatoFolder:
    return FilterWatoFolder(
        ident="wato_folder",
        title="Folder",
        sort_index=10,
        info="host",
        htmlvars=["wato_folder"],
        link_columns=[],
        group=FilterGroup.FOLDER,
    )


def _rename(folder: Folder) -> None:
    folder.edit(
        "Renamed",
        {},
        pprint_value=False,
        pending_changes=_noop_pending_changes(),
        acting_user=LoggedInSuperUser(),
    )


def test_the_heading_shows_the_current_title_of_the_folder(folder_sub: Folder) -> None:
    folder_filter = _folder_filter()
    folder_filter.heading_info({"wato_folder": "sub"}, RequestCache(Config()))

    _rename(folder_sub)

    assert folder_filter.heading_info({"wato_folder": "sub"}, RequestCache(Config())) == "Renamed"


def test_a_request_keeps_showing_the_title_it_resolved_first(folder_sub: Folder) -> None:
    folder_filter = _folder_filter()
    request_cache = RequestCache(Config())
    folder_filter.heading_info({"wato_folder": "sub"}, request_cache)

    _rename(folder_sub)

    assert folder_filter.heading_info({"wato_folder": "sub"}, request_cache) == "Sub"


def test_the_heading_of_a_folder_unknown_to_the_setup_is_empty() -> None:
    assert _folder_filter().heading_info({"wato_folder": "remote"}, RequestCache(Config())) is None


def test_the_filters_of_a_page_show_the_titles_its_painters_resolved(folder_sub: Folder) -> None:
    request_cache = RequestCache(Config())
    host_row = {"site": "NO_SITE", "host_name": "host", "host_filename": "/wato/sub/hosts.mk"}
    get_wato_folder(
        host_row, "plain", False, request=Request(create_environ()), request_cache=request_cache
    )

    _rename(folder_sub)

    assert _folder_filter().heading_info({"wato_folder": "sub"}, request_cache) == "Sub"


@pytest.mark.usefixtures("folder_sub")
def test_the_folder_selection_lists_the_subfolders_indented_below_their_parent() -> None:
    assert list(FolderTitles(Config()).selection()) == [
        ("", "Main"),
        ("sub", "\u00a0" * 6 + "\u2514\u2500 Sub"),
    ]
