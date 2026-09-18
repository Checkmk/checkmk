#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Final

from cmk.gui.pagetypes import PagetypeTopics
from cmk.update_config.plugins.lib.pagetypes import UpdatePagetypes
from cmk.update_config.registry import update_action_registry


class PagetypeTopicsUpdater:
    def __init__(self) -> None:
        self.target_type: Final = PagetypeTopics

    def update_raw_page_dict(self, page_dict: dict[str, object]) -> dict[str, object]:
        return page_dict | {
            "icon_name": (
                page_dict["icon_name"]
                # transparent icon
                or "trans"
            )
        }


update_action_registry.register(
    UpdatePagetypes(
        name="pagetype_topics",
        title="Topics",
        sort_index=120,  # can run whenever
        updater=PagetypeTopicsUpdater(),
    )
)
