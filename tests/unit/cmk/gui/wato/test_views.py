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
from cmk.gui.config import Config, RequestCacheConfig
from cmk.gui.http import Request
from cmk.gui.logged_in import LoggedInSuperUser
from cmk.gui.type_defs import Row
from cmk.gui.wato.views import get_wato_folder
from cmk.gui.watolib.hosts_and_folders import make_folder_tree
from cmk.gui.watolib.pending_changes import NoopPendingChangesStore, PendingChanges
from cmk.web.utils.html import HTML
from cmk.web.utils.request_cache import RequestCache

_REQUEST = Request(create_environ())


def _noop_pending_changes() -> PendingChanges:
    return PendingChanges(
        activation_sites=SiteConfigurations({}),
        local_site=SiteId("NO_SITE"),
        acting_user=None,
        store=NoopPendingChangesStore(),
        hooks=(),
    )


@pytest.fixture(name="folder_sub")
def fixture_folder_sub() -> Iterator[None]:
    """The folder "sub" titled "Sub" below the main folder"""
    root_folder = make_folder_tree(Config()).root_folder()
    root_folder.create_subfolder(
        name="sub",
        title="Sub",
        attributes={},
        pprint_value=False,
        pending_changes=_noop_pending_changes(),
        acting_user=LoggedInSuperUser(),
    )
    try:
        yield
    finally:
        shutil.rmtree(root_folder.filesystem_path(), ignore_errors=True)
        os.makedirs(root_folder.filesystem_path())


def _host_row_in(wato_path: str) -> Row:
    return {"site": "NO_SITE", "host_name": "host", "host_filename": f"/wato/{wato_path}/hosts.mk"}


def _folder_of(
    row: Row,
    how: str,
    request_cache: RequestCache[RequestCacheConfig] | None = None,
    with_links: bool = False,
) -> str | HTML:
    return get_wato_folder(
        row,
        how,
        with_links,
        request=_REQUEST,
        request_cache=request_cache or RequestCache(Config()),
    )


def _rename_folder_sub() -> None:
    make_folder_tree(Config()).folder("sub").edit(
        "Renamed",
        {},
        pprint_value=False,
        pending_changes=_noop_pending_changes(),
        acting_user=LoggedInSuperUser(),
    )


@pytest.mark.usefixtures("folder_sub")
def test_the_complete_path_shows_the_titles_of_the_folders() -> None:
    assert _folder_of(_host_row_in("sub"), "abs") == "Main / Sub"


@pytest.mark.usefixtures("folder_sub")
def test_the_folder_name_shows_the_title_of_the_folder() -> None:
    assert _folder_of(_host_row_in("sub"), "plain") == "Sub"


def test_a_folder_unknown_to_the_setup_shows_its_path() -> None:
    """The folder of a host of a remote site with a folder hierarchy of its own"""
    assert _folder_of(_host_row_in("remote/only"), "abs") == "remote / only"


def test_a_host_not_managed_by_the_setup_shows_no_folder() -> None:
    row = {"site": "NO_SITE", "host_name": "host", "host_filename": "/etc/hosts.mk"}

    assert _folder_of(row, "abs") == ""


@pytest.mark.usefixtures("request_context", "folder_sub")
def test_the_linked_path_links_each_folder_to_the_setup() -> None:
    linked = str(_folder_of(_host_row_in("sub"), "abs", with_links=True))

    assert "folder=sub" in linked and ">Sub</a>" in linked


@pytest.mark.usefixtures("folder_sub")
def test_a_request_keeps_showing_the_titles_it_resolved_first() -> None:
    request_cache = RequestCache(Config())
    _folder_of(_host_row_in("sub"), "plain", request_cache)

    _rename_folder_sub()

    assert _folder_of(_host_row_in("sub"), "plain", request_cache) == "Sub"


@pytest.mark.usefixtures("folder_sub")
def test_a_new_request_shows_the_renamed_folder() -> None:
    _folder_of(_host_row_in("sub"), "plain", RequestCache(Config()))

    _rename_folder_sub()

    assert _folder_of(_host_row_in("sub"), "plain") == "Renamed"
