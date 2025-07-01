#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import shutil
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any, NewType

import cmk.ccc.version as cmk_version
from cmk.ccc.site import SiteId

from cmk.utils import paths

import cmk.gui.watolib.changes as _changes
from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.config import active_config
from cmk.gui.customer import customer_api, SCOPE_GLOBAL
from cmk.gui.exceptions import MKUserError
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.page_menu import (
    make_simple_link,
    PageMenu,
    PageMenuDropdown,
    PageMenuEntry,
    PageMenuSearch,
    PageMenuTopic,
)
from cmk.gui.site_config import get_login_sites
from cmk.gui.table import table_element
from cmk.gui.type_defs import ActionResult
from cmk.gui.userdb import (
    ConfigurableUserConnectionSpec,
    load_connection_config,
    save_connection_config,
    UserConnectionConfigFile,
)
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.utils.urls import DocReference, make_confirm_delete_link, makeuri_contextless
from cmk.gui.watolib.audit_log import LogMessage
from cmk.gui.watolib.config_domains import ConfigDomainGUI
from cmk.gui.watolib.hosts_and_folders import folder_preserving_link, make_action_link
from cmk.gui.watolib.mode import redirect

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
    customer = customer_api()
    with table_element() as table:
        for display_index, (real_index, connection) in _connections_by_gui_index(
            connection_type, load_connection_config(lock=False)
        ).items():
            table.row()

            table.cell("#", css=["narrow nowrap"])
            html.write_text_permissive(display_index)

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

            if cmk_version.edition(paths.omd_root) is cmk_version.Edition.CME:
                table.cell(_("Customer"), customer.get_customer_name(connection))

            table.cell(_("Description"))
            url = connection.get("docu_url")
            if url:
                html.icon_button(
                    url, _("Context information about this connection"), "url", target="_blank"
                )
                html.write_text_permissive("&nbsp;")
            html.write_text_permissive(connection["description"])


def add_change(*, action_name: str, text: LogMessage, sites: list[SiteId]) -> None:
    _changes.add_change(
        action_name=action_name,
        text=text,
        user_id=user.id,
        domains=[ConfigDomainGUI()],
        sites=sites,
        use_git=active_config.wato_use_git,
    )


def get_affected_sites(connection: ConfigurableUserConnectionSpec) -> list[SiteId]:
    if cmk_version.edition(paths.omd_root) is cmk_version.Edition.CME:
        # TODO CMK-14203
        _customer_api = customer_api()
        customer: str | None = connection.get("customer", SCOPE_GLOBAL)
        if _customer_api.is_global(customer):
            return list(active_config.sites.keys())
        assert customer is not None
        return list(_customer_api.get_sites_of_customer(customer).keys())
    return get_login_sites()


def _delete_connection(
    index: int, connection_type: str, *, custom_config_dirs: Iterable[Path]
) -> None:
    connections = UserConnectionConfigFile().load_for_modification()
    connection = connections[index]
    connection_id = connection["id"]
    add_change(
        action_name=f"delete-{connection_type}-connection",
        text=_("Deleted connection %s") % (connection_id),
        sites=get_affected_sites(connection),
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
    connections = UserConnectionConfigFile().load_for_modification()
    connection = connections[from_index]
    add_change(
        action_name=f"move-{connection_type}-connection",
        text=_("Changed position of connection %s to %d") % (connection["id"], to_index),
        sites=get_affected_sites(connection),
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
