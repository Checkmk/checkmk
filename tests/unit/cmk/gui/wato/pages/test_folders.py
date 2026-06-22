#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Iterator

import pytest

from cmk.gui.http import Request
from cmk.gui.page_menu import PageMenuEntry
from cmk.gui.wato.pages.folders import (
    FolderBulkAction,
    FolderBulkActionRegistry,
    FolderMenuEntry,
    FolderMenuEntryRegistry,
    FolderMenuLocation,
)
from cmk.gui.watolib.hosts_and_folders import Folder, SearchFolder
from cmk.livestatus_client.testing import MockLiveStatusConnection
from tests.testlib.gui.web_test_app import WebTestAppForCMK


def test_folder_menu_entry_registry_filters_by_location() -> None:
    registry = FolderMenuEntryRegistry()

    def _no_entries(_folder: Folder | SearchFolder) -> Iterator[PageMenuEntry]:
        yield from ()

    in_folder = FolderMenuEntry(FolderMenuLocation.IN_FOLDER, "in_folder", _no_entries)
    selected = FolderMenuEntry(FolderMenuLocation.SELECTED_HOSTS, "selected", _no_entries)
    registry.register(in_folder)
    registry.register(selected)

    assert registry["in_folder"] is in_folder
    assert registry.by_location(FolderMenuLocation.IN_FOLDER) == [in_folder]
    assert registry.by_location(FolderMenuLocation.SELECTED_HOSTS) == [selected]


def test_folder_bulk_action_registry_keys_by_request_var() -> None:
    registry = FolderBulkActionRegistry()

    action = FolderBulkAction(request_var="_demo", mode_name="demo")
    registry.register(action)

    assert registry["_demo"] is action
    assert list(registry.values()) == [action]


@pytest.mark.usefixtures("patch_theme")
@pytest.mark.usefixtures("suppress_license_expiry_header")
@pytest.mark.usefixtures("suppress_license_banner")
def test_ajax_call(logged_in_wsgi_app: WebTestAppForCMK) -> None:
    ajax_page = "/NO_SITE/check_mk/ajax_popup_move_to_folder.py"
    app = logged_in_wsgi_app
    resp = app.get(
        f"{ajax_page}?ident=test2&what=folder&_ajaxid=1611222306&back_url=wato.py", status=400
    )
    assert "Move this folder to" in resp.text, resp.text
    assert "No Setup folder test2." in resp.text, resp.text

    resp = app.get(f"{ajax_page}?ident=test2&what=folder&back_url=wato.py", status=400)
    assert "Move this folder to" in resp.text, resp.text
    assert "No Setup folder test2." in resp.text, resp.text

    app.get(f"{ajax_page}/{ajax_page}?ident=test2&what=folder&back_url=wato.py", status=404)


@pytest.mark.usefixtures("patch_theme")
@pytest.mark.usefixtures("suppress_license_expiry_header")
@pytest.mark.usefixtures("suppress_license_banner")
def test_ajax_call_2(
    wsgi_app: WebTestAppForCMK,
    mock_livestatus: MockLiveStatusConnection,
    auth_request: Request,
) -> None:
    ajax_page = "/NO_SITE/check_mk/ajax_popup_move_to_folder.py"
    wsgi_app.get(auth_request)  # to get the cookie

    resp = wsgi_app.get(f"{ajax_page}/{ajax_page}?ident=test2&what=folder&back_url=wato.py")
    assert resp.status_code == 404, resp.location
