#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import shutil
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any, NewType

from livestatus import SiteId

import cmk.utils.version as cmk_version

import cmk.gui.watolib.changes as _changes
from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.config import active_config
from cmk.gui.exceptions import MKUserError
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.page_menu import (
    make_simple_link,
    PageMenu,
    PageMenuDropdown,
    PageMenuEntry,
    PageMenuSearch,
    PageMenuTopic,
)
from cmk.gui.plugins.userdb.utils import (
    load_connection_config,
    save_connection_config,
    UserConnectionSpec,
)
from cmk.gui.plugins.wato.utils import make_confirm_delete_link, redirect
from cmk.gui.site_config import get_login_sites
from cmk.gui.table import table_element
from cmk.gui.type_defs import ActionResult
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.utils.urls import DocReference, makeuri_contextless
from cmk.gui.watolib.audit_log import LogMessage
from cmk.gui.watolib.config_domains import ConfigDomainGUI
from cmk.gui.watolib.hosts_and_folders import folder_preserving_link, make_action_link

if cmk_version.is_managed_edition():
    import cmk.gui.cme.helpers as managed_helpers  # pylint: disable=no-name-in-module
    import cmk.gui.cme.managed as managed  # pylint: disable=no-name-in-module


DisplayIndex = NewType("DisplayIndex", int)
RealIndex = NewType("RealIndex", int)


def _related_page_menu_entries() -> Iterable[PageMenuEntry]:
    yield PageMenuEntry(
        title=_("Users"),
        icon_name="users",
        item=make_simple_link(
            makeuri_contextless(
                request,
                [("mode", "users")],
                filename="wato.py",
            )
        ),
    )


def add_connections_page_menu(
    title: str,
    edit_mode_path: str,
    breadcrumb: Breadcrumb,
    *,
    documentation_reference: DocReference | None = None,
) -> PageMenu:
    page_menu: PageMenu = PageMenu(
        dropdowns=[
            PageMenuDropdown(
                name="connections",
                title=_("Connections"),
                topics=[
                    PageMenuTopic(
                        title=_("Add connection"),
                        entries=[
                            PageMenuEntry(
                                title=_("Add connection"),
                                icon_name="new",
                                item=make_simple_link(
                                    folder_preserving_link(
                                        [
                                            ("mode", edit_mode_path),
                                            ("new", request.get_ascii_input("id")),
                                        ]
                                    )
                                ),
                                is_shortcut=True,
                                is_suggested=True,
                            ),
                        ],
                    ),
                ],
            ),
            PageMenuDropdown(
                name="related",
                title=_("Related"),
                topics=[
                    PageMenuTopic(
                        title=_("Setup"),
                        entries=list(_related_page_menu_entries()),
                    ),
                ],
            ),
        ],
        breadcrumb=breadcrumb,
        inpage_search=PageMenuSearch(),
    )
    if documentation_reference:
        page_menu.add_doc_reference(title=title, doc_ref=documentation_reference)
    return page_menu


def _connections(
    connection_type: str, all_connections: Sequence[Mapping[str, Any]]
) -> Iterable[tuple[RealIndex, Mapping[str, Any]]]:
    for real_index, connection in enumerate(all_connections):
        if connection["type"] == connection_type:
            yield RealIndex(real_index), connection


def _connections_by_gui_index(
    connection_type: str, all_connections: Sequence[Mapping[str, Any]]
) -> Mapping[DisplayIndex, tuple[RealIndex, Mapping[str, Any]]]:
    """Enumerated connections of the same type (SAML/LDAP).

    >>> _connections_by_gui_index("saml2", [{"id": "myldap1","type": "ldap"}, {"id": "mysaml1", "type": "saml2"}])
    {0: (1, {'id': 'mysaml1', 'type': 'saml2'})}
    """
    return {
        DisplayIndex(k): v
        for k, v in enumerate(list(_connections(connection_type, all_connections)))
    }


def render_connections_page(
    connection_type: str, edit_mode_path: str, config_mode_path: str
) -> None:
    with table_element() as table:
        for display_index, (real_index, connection) in _connections_by_gui_index(
            connection_type, load_connection_config(lock=False)
        ).items():
            table.row()

            table.cell("#", css=["narrow nowrap"])
            html.write_text(display_index)

            table.cell(_("Actions"), css=["buttons"])
            connection_id = connection["id"]
            edit_url = folder_preserving_link(
                [("mode", edit_mode_path), ("id", connection_id), ("edit", connection_id)]
            )
            delete_url = make_confirm_delete_link(
                url=make_action_link([("mode", config_mode_path), ("_delete", real_index)]),
                title=_("Delete connection #%d") % display_index,
                suffix=connection.get("name", connection["id"]),
                message=_("ID: %s") % connection["id"],
            )
            drag_url = make_action_link(
                [
                    ("mode", config_mode_path),
                    ("_move", real_index),
                    ("_connection_type", connection["type"]),
                ]
            )
            clone_url = folder_preserving_link(
                [("mode", edit_mode_path), ("clone", connection["id"])]
            )

            html.icon_button(edit_url, _("Edit this connection"), "edit")
            html.icon_button(clone_url, _("Create a copy of this connection"), "clone")
            html.element_dragger_url("tr", base_url=drag_url)
            html.icon_button(delete_url, _("Delete this connection"), "delete")

            table.cell("", css=["narrow"])
            if connection.get("disabled"):
                html.icon(
                    "disabled",
                    _("This connection is currently not being used for synchronization."),
                )
            else:
                html.empty_icon_button()

            connection_id = connection["id"]
            table.cell(_("ID"), connection_id)
            table.cell(_("Name"), connection.get("name", connection_id))

            if cmk_version.is_managed_edition():
                table.cell(_("Customer"), managed.get_customer_name(connection))

            table.cell(_("Description"))
            url = connection.get("docu_url")
            if url:
                html.icon_button(
                    url, _("Context information about this connection"), "url", target="_blank"
                )
                html.write_text("&nbsp;")
            html.write_text(connection["description"])


def add_change(action_name: str, text: LogMessage, sites: list[SiteId]) -> None:
    _changes.add_change(action_name, text, domains=[ConfigDomainGUI], sites=sites)


def get_affected_sites(connection: UserConnectionSpec) -> list[SiteId]:
    if cmk_version.is_managed_edition():
        return list(managed_helpers.get_sites_of_customer(connection["customer"]).keys())
    return get_login_sites()


def _delete_connection(
    index: int, connection_type: str, *, custom_config_dirs: Iterable[Path]
) -> None:
    connections = load_connection_config(lock=True)
    connection = connections[index]
    connection_id = connection["id"]
    add_change(
        f"delete-{connection_type}-connection",
        _("Deleted connection %s") % (connection_id),
        get_affected_sites(connection),
    )

    for dir_ in custom_config_dirs:
        # Any custom config files the user may have uploaded, such as custom certificates
        _remove_custom_files(dir_)

    del connections[index]
    save_connection_config(connections)


def _remove_custom_files(cert_dir: Path) -> None:
    if not cert_dir.exists():
        return
    shutil.rmtree(cert_dir)


def _move_connection(from_index: int, to_index: int, connection_type: str) -> None:
    connections = load_connection_config(lock=True)
    connection = connections[from_index]
    add_change(
        f"move-{connection_type}-connection",
        _("Changed position of connection %s to %d") % (connection["id"], to_index),
        get_affected_sites(connection),
    )
    del connections[from_index]  # make to_pos now match!
    connections[to_index:to_index] = [connection]
    save_connection_config(connections)


def _gui_index_to_real_index(
    connection_type: str, gui_index: DisplayIndex, all_connections: Sequence[Mapping[str, Any]]
) -> RealIndex:
    """Map the index that's shown in the GUI and available as '_index' HTTP parameter in case of a
    move connection action to its actual index in the user_connections.mk file.

    >>> all_connections = [{"id": "myldap1","type": "ldap"}, {"id": "mysaml1", "type": "saml2"}]
    >>> _gui_index_to_real_index("saml2", DisplayIndex(0), all_connections)
    1
    """
    return _connections_by_gui_index(connection_type, all_connections)[gui_index][0]


def connection_actions(
    config_mode_url: str, connection_type: str, custom_config_dirs: Iterable[Path]
) -> ActionResult:
    if not transactions.check_transaction():
        return redirect(config_mode_url)

    if request.has_var("_delete"):
        _delete_connection(
            index=request.get_integer_input_mandatory("_delete"),
            connection_type=connection_type,
            custom_config_dirs=custom_config_dirs,
        )

    elif request.has_var("_move"):
        _move_connection(
            from_index=request.get_integer_input_mandatory("_move"),
            to_index=_gui_index_to_real_index(
                request.get_ascii_input_mandatory("_connection_type"),
                DisplayIndex(request.get_integer_input_mandatory("_index")),
                load_connection_config(lock=False),
            ),
            connection_type=connection_type,
        )

    return redirect(config_mode_url)


def validate_connection_id(value: str, varprefix: str) -> None:
    if value in [c["id"] for c in active_config.user_connections] or value == "htpasswd":
        raise MKUserError(
            varprefix,
            _("This ID already exists."),
        )
