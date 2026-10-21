#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

import pytest
from bs4 import BeautifulSoup

from cmk.gui.utils.output_funnel import output_funnel
from cmk.gui.views.builtin_views import builtin_views
from cmk.gui.wato._snapins import FolderEntry, render_tree_folder, SidebarSnapinWATOFoldertree


def test_folder_tree_offers_hidden_default_target_view() -> None:
    target_views = dict(
        SidebarSnapinWATOFoldertree.target_views(
            {"allhosts": builtin_views["allhosts"]}, "allhosts"
        )
    )

    assert target_views["allhosts"]["hidden"] is False


def test_folder_tree_keeps_other_hidden_views_hidden() -> None:
    target_views = dict(
        SidebarSnapinWATOFoldertree.target_views(
            {"allhosts": builtin_views["allhosts"]}, "searchhost"
        )
    )

    assert target_views["allhosts"]["hidden"] is True


def _folder(path: str, title: str, subfolders: list[FolderEntry] | None = None) -> FolderEntry:
    return FolderEntry(
        {
            ".folders": {f[".path"]: f for f in subfolders or []},
            ".num_hosts": 1,
            ".path": path,
            "title": title,
        }
    )


@pytest.mark.usefixtures("request_context", "patch_theme")
def test_tree_folder_links_open_the_folder_by_click_action() -> None:
    with output_funnel.plugged():
        render_tree_folder("wato-hosts", _folder("", "Main", [_folder("linux", "Linux")]))
        rendered = output_funnel.drain()

    links = BeautifulSoup(rendered, "lxml").select("a.link")
    assert [
        (
            link.get("onclick"),
            link.get("data-cmk_on_click"),
            json.loads(str(link["data-cmk_on_click_arguments"])),
        )
        for link in links
    ] == [
        (None, "wato_tree_click", {"folder_path": ""}),
        (None, "wato_tree_click", {"folder_path": "linux"}),
    ]
