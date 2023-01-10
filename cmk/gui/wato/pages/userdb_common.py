#!/usr/bin/env python3
# Copyright (C) 2023 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable

from livestatus import SiteId

import cmk.utils.version as cmk_version

import cmk.gui.watolib.changes as _changes
from cmk.gui.breadcrumb import Breadcrumb
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
from cmk.gui.plugins.userdb.utils import connections_by_type, UserConnectionSpec
from cmk.gui.plugins.wato.utils import make_confirm_link
from cmk.gui.site_config import get_login_sites
from cmk.gui.table import table_element
from cmk.gui.utils.urls import DocReference, makeuri_contextless
from cmk.gui.watolib.audit_log import LogMessage
from cmk.gui.watolib.config_domains import ConfigDomainGUI
from cmk.gui.watolib.hosts_and_folders import folder_preserving_link, make_action_link

if cmk_version.is_managed_edition():
    import cmk.gui.cme.helpers as managed_helpers  # pylint: disable=no-name-in-module
    import cmk.gui.cme.managed as managed  # pylint: disable=no-name-in-module


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
    documentation_reference: DocReference,
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
                                    folder_preserving_link([("mode", edit_mode_path)])
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
    page_menu.add_doc_reference(title=title, doc_ref=documentation_reference)
    return page_menu


def render_connections_page(
    connection_type: str, edit_mode_path: str, config_mode_path: str
) -> None:
    with table_element() as table:
        for index, connection in enumerate(connections_by_type(connection_type)):
            table.row()

            table.cell(_("Actions"), css=["buttons"])
            edit_url = folder_preserving_link([("mode", edit_mode_path), ("id", connection["id"])])
            delete_url = make_confirm_link(
                url=make_action_link([("mode", config_mode_path), ("_delete", index)]),
                message=_("Do you really want to delete the connection <b>%s</b>?")
                % connection["id"],
            )
            drag_url = make_action_link([("mode", config_mode_path), ("_move", index)])
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

            table.cell(_("ID"), connection["id"])

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
