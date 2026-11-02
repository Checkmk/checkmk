#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.views.builtin_views import builtin_views
from cmk.gui.wato._snapins import SidebarSnapinWATOFoldertree


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
