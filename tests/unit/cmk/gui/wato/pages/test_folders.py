#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator, Mapping
from http import HTTPStatus

import pytest

from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.ccc.version import Edition
from cmk.gui.config import Config
from cmk.gui.exceptions import HTTPRedirect
from cmk.gui.http import Request, request
from cmk.gui.logged_in import LoggedInSuperUser, user
from cmk.gui.page_menu import PageMenuEntry
from cmk.gui.pages import PageContext
from cmk.gui.permissions import all_permissions
from cmk.gui.utils.output_funnel import output_funnel
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.utils.selection_id import SelectionId
from cmk.gui.utils.session import session
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.wato.pages.folders import (
    FolderBulkAction,
    FolderBulkActionRegistry,
    FolderMenuEntry,
    FolderMenuEntryRegistry,
    FolderMenuLocation,
    ModeFolder,
    PageAjaxPopupMoveToFolder,
)
from cmk.gui.watolib import hosts_and_folders
from cmk.gui.watolib.host_attributes import HostAttributes
from cmk.gui.watolib.hosts_and_folders import Folder, FolderTree, make_folder_tree, SearchFolder
from cmk.gui.watolib.pending_changes import NoopPendingChangesStore, PendingChanges
from cmk.livestatus_client import SiteConfigurations
from cmk.livestatus_client.testing import MockLiveStatusConnection
from tests.testlib.unit.gui.web_test_app import WebTestAppForCMK
from tests.unit.cmk.gui.compare_html import inline_event_handlers, ts_function_call
from tests.unit.cmk.gui.helpers.setup_mode_test_helper import (
    end_request,
    page_context,
    render_page,
    submit,
)


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
        f"{ajax_page}?ident=test2&what=folder&_ajaxid=1611222306&back_url=wato.py",
        status=HTTPStatus.BAD_REQUEST,
    )
    assert "Move this folder to" in resp.text, resp.text
    assert "No Setup folder test2." in resp.text, resp.text

    resp = app.get(
        f"{ajax_page}?ident=test2&what=folder&back_url=wato.py", status=HTTPStatus.BAD_REQUEST
    )
    assert "Move this folder to" in resp.text, resp.text
    assert "No Setup folder test2." in resp.text, resp.text

    app.get(
        f"{ajax_page}/{ajax_page}?ident=test2&what=folder&back_url=wato.py",
        status=HTTPStatus.NOT_FOUND,
    )


@pytest.mark.usefixtures("patch_theme", "mock_livestatus")
@pytest.mark.usefixtures("suppress_license_expiry_header")
@pytest.mark.usefixtures("suppress_license_banner")
def test_ajax_call_2(wsgi_app: WebTestAppForCMK, auth_request: Request) -> None:
    ajax_page = "/NO_SITE/check_mk/ajax_popup_move_to_folder.py"
    wsgi_app.get(auth_request)  # to get the cookie

    resp = wsgi_app.get(f"{ajax_page}/{ajax_page}?ident=test2&what=folder&back_url=wato.py")
    assert resp.status_code == HTTPStatus.NOT_FOUND, resp.location


_SELECTION = SelectionId("selection")


def _create_hosts(tree: FolderTree, hosts: Mapping[str, HostAttributes]) -> None:
    tree.root_folder().create_hosts(
        [(HostName(name), attributes, None) for name, attributes in hosts.items()],
        pprint_value=False,
        pending_changes=PendingChanges(
            activation_sites=SiteConfigurations({}),
            local_site=SiteId("NO_SITE"),
            acting_user=None,
            store=NoopPendingChangesStore(),
            hooks=(),
        ),
        acting_user=LoggedInSuperUser(),
    )


def _submit_for_selected_hosts(*host_names: str, **variables: str) -> None:
    user.set_rowselection(_SELECTION, "wato-folder-/", [f"_c_{name}" for name in host_names], "set")
    submit(mode="folder", folder="", selection=_SELECTION, **variables)


def _hosts_in_setup(config: Config) -> set[str]:
    end_request()
    return set(make_folder_tree(config).root_folder().hosts())


@pytest.mark.usefixtures("request_context", "with_admin_login")
def test_bulk_delete_deletes_nothing_before_it_is_confirmed(
    tree: FolderTree, config: Config, test_edition: Edition
) -> None:
    _create_hosts(tree, {"h1": HostAttributes(), "h2": HostAttributes()})
    _submit_for_selected_hosts("h1", _bulk_delete="SET")

    result = ModeFolder(test_edition, page_context(config)).action(config)

    assert result is None
    assert _hosts_in_setup(config) == {"h1", "h2"}


@pytest.mark.usefixtures("request_context", "with_admin_login", "patch_theme")
def test_bulk_delete_confirmation_names_the_relations_the_selection_loses(
    tree: FolderTree,
    config: Config,
    test_edition: Edition,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    _create_hosts(tree, {"os1": HostAttributes()})
    _create_hosts(
        tree,
        {
            "board": HostAttributes(
                {
                    "relations": [
                        {"kind": "management", "direction": "parent", "host": HostName("os1")}
                    ]
                }
            )
        },
    )
    _submit_for_selected_hosts("board", _bulk_delete="SET")
    mode = ModeFolder(test_edition, page_context(config))
    mode.action(config)
    mock_livestatus.expect_query("GET hosts\nColumns: name")

    with mock_livestatus:
        page = render_page(mode, config)

    assert "Delete 1 selected host?" in page
    assert "The following selected host has relations to hosts that are not deleted:" in page


@pytest.mark.usefixtures("request_context", "with_admin_login")
def test_bulk_delete_deletes_the_selected_hosts_once_confirmed(
    tree: FolderTree,
    config: Config,
    test_edition: Edition,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Deleting the host's files needs a site connection, which this test has nothing to say about.
    monkeypatch.setattr(hosts_and_folders.Folder, "_delete_host_files", lambda *_a, **_kw: None)
    _create_hosts(tree, {"h1": HostAttributes(), "h2": HostAttributes()})
    _submit_for_selected_hosts("h1", _bulk_delete="SET", _bulk_delete_confirmed="1")

    result = ModeFolder(test_edition, page_context(config)).action(config)

    assert isinstance(result, HTTPRedirect)
    assert _hosts_in_setup(config) == {"h2"}


@pytest.mark.usefixtures("request_context")
def test_move_to_folder_popup_moves_on_change_without_inline_handler() -> None:
    request.set_var("what", "host")
    request.set_var("ident", "my-host")
    request.set_var("back_url", "wato.py?folder=sub")

    with output_funnel.plugged():
        PageAjaxPopupMoveToFolder().handle_page(
            PageContext(
                config=Config(),
                request=request,
                transactions=transactions,
                session=session,
                user_permissions=UserPermissions.from_config(Config(), all_permissions()),
            )
        )
        code = output_funnel.drain()

    assert inline_event_handlers(code) == []
    assert ts_function_call(code, "select") == (
        "wato_move_to_folder_on_change",
        {"url_prefix": "wato.py?folder=sub&_ident=my-host&_move_host_to="},
    )
