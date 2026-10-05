#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""The "Relation detection" page: what the hosts say about each other, and what to keep.

A thin shell around the Vue app. The page asks only which relation to look for, where, and
in which folder or site - then it shows what it found in the hosts and lets the user confirm
it - so all the shell hands over is how the relations are worded, what can be looked in, and
the app talks to the internal API.
"""

from collections.abc import Collection, Iterator, Sequence
from dataclasses import asdict
from typing import override

from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.config import Config
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.page_menu import make_simple_link, PageMenu, PageMenuEntry
from cmk.gui.user_sites import get_configured_site_choices
from cmk.gui.wato.pages.folders import (
    FolderMenuEntry,
    FolderMenuEntryRegistry,
    FolderMenuLocation,
    ModeFolder,
)
from cmk.gui.watolib.host_relation_detection import (
    detectable_kind_words,
    detectable_kinds,
    relation_end_nouns,
    relation_row_titles,
)
from cmk.gui.watolib.hosts_and_folders import (
    Folder,
    folder_preserving_link,
    folder_tree,
    SearchFolder,
)
from cmk.gui.watolib.mode import ModeRegistry, WatoMode
from cmk.shared_typing.mode_host_relation_detection import HostRelationDetection, ScopeChoice
from cmk.web.utils.icons import IconNames, StaticIcon
from cmk.web.utils.permission_verification import PermissionName
from cmk.web.utils.urls import makeuri_contextless


class ModeHostRelationDetection(WatoMode[None]):
    @classmethod
    @override
    def name(cls) -> str:
        return "host_relation_detection"

    @staticmethod
    @override
    def static_permissions() -> Collection[PermissionName]:
        return ["edit", "hosts", "edit_hosts"]

    @classmethod
    @override
    def parent_mode(cls) -> type[WatoMode[None]] | None:
        return ModeFolder

    @override
    def title(self) -> str:
        return _("Relation detection")

    @override
    def page_menu(self, config: Config, breadcrumb: Breadcrumb) -> PageMenu:
        return PageMenu(dropdowns=[], breadcrumb=breadcrumb)

    @override
    def page(self, config: Config) -> None:
        folders = [
            ScopeChoice(name=f"/{path}", title=title)
            for path, title in folder_tree().folder_choices_fulltitle(user)
        ]
        sites = get_configured_site_choices()
        html.vue_component(
            "cmk-mode-host-relation-detection",
            data=asdict(
                HostRelationDetection(
                    kinds=dict(detectable_kinds()),
                    kind_words=dict(detectable_kind_words()),
                    relation_titles=dict(relation_row_titles()),
                    relation_nouns=dict(relation_end_nouns()),
                    activate_changes_url=makeuri_contextless(
                        request, [("mode", "changelog")], filename="wato.py"
                    ),
                    folders=folders,
                    folder=_opened_from(folders),
                    sites=(
                        [ScopeChoice(name=site_id, title=title) for site_id, title in sites]
                        if len(sites) > 1
                        else []
                    ),
                )
            ),
        )


def _opened_from(folders: Sequence[ScopeChoice]) -> str:
    """The folder the page was opened from, as the API names it, if the user may see it; else
    the main folder."""
    wanted = "/" + request.get_str_input_mandatory("folder", "")
    return wanted if any(folder.name == wanted for folder in folders) else "/"


def _folder_page_menu_entries(_folder: Folder | SearchFolder) -> Iterator[PageMenuEntry]:
    # Next to the other tools that work on all of Setup rather than on the folder at hand: the
    # page reads every host, and only starts out looking for relations in this folder.
    if user.may("wato.edit") and user.may("wato.hosts") and user.may("wato.edit_hosts"):
        yield PageMenuEntry(
            title=_("Relation detection"),
            icon_name=StaticIcon(IconNames.link),
            item=make_simple_link(
                folder_preserving_link(request, [("mode", ModeHostRelationDetection.name())])
            ),
        )


def register(
    mode_registry: ModeRegistry,
    folder_menu_entry_registry: FolderMenuEntryRegistry,
) -> None:
    mode_registry.register(ModeHostRelationDetection)
    folder_menu_entry_registry.register(
        FolderMenuEntry(
            location=FolderMenuLocation.RELATED,
            ident="host_relation_detection",
            func=_folder_page_menu_entries,
        )
    )
