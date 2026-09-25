#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""The "Relation discovery" page: what the hosts say about each other, and what to keep.

A thin shell around the Vue app. The page asks only which relation to look for and where -
then it shows what it found in the hosts and lets the user confirm it - so all the shell hands
over is how the relations are worded, and the app talks to the internal API.
"""

from collections.abc import Collection, Iterator
from dataclasses import asdict
from typing import override

from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.config import Config
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.page_menu import make_simple_link, PageMenu, PageMenuEntry
from cmk.gui.wato.pages.folders import (
    FolderMenuEntry,
    FolderMenuEntryRegistry,
    FolderMenuLocation,
    ModeFolder,
)
from cmk.gui.watolib.host_relation_discovery import (
    discoverable_kind_words,
    discoverable_kinds,
    relation_end_nouns,
    relation_row_titles,
)
from cmk.gui.watolib.hosts_and_folders import Folder, SearchFolder
from cmk.gui.watolib.mode import ModeRegistry, WatoMode
from cmk.shared_typing.mode_host_relation_discovery import HostRelationDiscovery
from cmk.web.utils.icons import IconNames, StaticIcon
from cmk.web.utils.permission_verification import PermissionName
from cmk.web.utils.urls import makeuri_contextless

_TITLE = _("Relation discovery")


class ModeHostRelationDiscovery(WatoMode[None]):
    @classmethod
    @override
    def name(cls) -> str:
        return "host_relation_discovery"

    @staticmethod
    @override
    def static_permissions() -> Collection[PermissionName]:
        return ["hosts", "edit_hosts"]

    @classmethod
    @override
    def parent_mode(cls) -> type[WatoMode[None]] | None:
        return ModeFolder

    @override
    def title(self) -> str:
        return _TITLE

    @override
    def page_menu(self, config: Config, breadcrumb: Breadcrumb) -> PageMenu:
        return PageMenu(dropdowns=[], breadcrumb=breadcrumb)

    @override
    def page(self, config: Config) -> None:
        html.vue_component(
            "cmk-mode-host-relation-discovery",
            data=asdict(
                HostRelationDiscovery(
                    kinds=dict(discoverable_kinds()),
                    kind_words=dict(discoverable_kind_words()),
                    relation_titles=dict(relation_row_titles()),
                    relation_nouns=dict(relation_end_nouns()),
                    activate_changes_url=makeuri_contextless(
                        request, [("mode", "changelog")], filename="wato.py"
                    ),
                )
            ),
        )


def _folder_page_menu_entries(_folder: Folder | SearchFolder) -> Iterator[PageMenuEntry]:
    # Next to the other tools that work on all of Setup rather than on the folder at hand:
    # the page reads every host, wherever it is opened from.
    if user.may("wato.hosts") and user.may("wato.edit_hosts"):
        # A verb in the menu and a noun on the page, like "Detect network parent hosts".
        yield PageMenuEntry(
            title=_("Detect related hosts"),
            icon_name=StaticIcon(IconNames.link),
            item=make_simple_link(
                makeuri_contextless(
                    request, [("mode", ModeHostRelationDiscovery.name())], filename="wato.py"
                )
            ),
        )


def register(
    mode_registry: ModeRegistry,
    folder_menu_entry_registry: FolderMenuEntryRegistry,
) -> None:
    mode_registry.register(ModeHostRelationDiscovery)
    folder_menu_entry_registry.register(
        FolderMenuEntry(
            location=FolderMenuLocation.RELATED,
            ident="host_relation_discovery",
            func=_folder_page_menu_entries,
        )
    )
