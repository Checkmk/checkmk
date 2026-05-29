#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Iterator

from cmk.ccc.hostaddress import HostName
from cmk.gui.htmllib.html import html
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.page_menu import make_form_submit_link, make_simple_link, PageMenuEntry
from cmk.gui.type_defs import IconNames, StaticIcon
from cmk.gui.watolib.hosts_and_folders import Folder, Host, SearchFolder

# URL variable flag passed from the folder view to the host_action_menu ajax endpoint.
HOST_ACTION_MENU_IDENT = "show_parentscan_link"


def folder_page_menu_entries(folder: Folder | SearchFolder) -> Iterator[PageMenuEntry]:
    if (
        not folder.locked_hosts()
        and user.may("wato.parentscan")
        and folder.permissions.may("write")
    ):
        folder_or_subfolder_has_hosts = (
            isinstance(folder, Folder) and folder.num_hosts_recursively() > 0
        )
        yield PageMenuEntry(
            title=_("Detect network parent hosts"),
            icon_name=StaticIcon(IconNames.parentscan),
            item=make_simple_link(folder.url([("mode", "parentscan"), ("all", "1")])),
            disabled_tooltip=_("Add host to use this action"),
            is_enabled=folder_or_subfolder_has_hosts,
        )


def selected_hosts_page_menu_entries(folder: Folder | SearchFolder) -> Iterator[PageMenuEntry]:
    if not folder.locked_hosts() and user.may("wato.parentscan"):
        yield PageMenuEntry(
            title=_("Detect network parent hosts"),
            icon_name=StaticIcon(IconNames.parentscan),
            item=make_form_submit_link(form_name="hosts", button_name="_parentscan"),
            disabled_tooltip=_("Add host/subfolder to use this action"),
            is_enabled=folder.has_hosts(),
        )


def host_action_menu_is_shown(_host: Host, folder: Folder | SearchFolder) -> bool:
    return not folder.locked_hosts() and user.may("wato.parentscan")


def render_host_action_menu_entry(_host_name: HostName, form_name: str) -> None:
    html.open_a(
        href=None,
        onclick="cmk.selection.execute_bulk_action_for_single_host(this, cmk.page_menu.form_submit, %s);"
        % json.dumps([form_name, "_parentscan"]),
    )
    html.static_icon(StaticIcon(IconNames.parentscan))
    html.write_text_permissive(_("Detect network parents"))
    html.close_a()
