#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from typing import Literal

from cmk.gui.htmllib.html import html
from cmk.gui.watolib.main_menu import MenuItem


class TileMenuRenderer:
    def __init__(
        self,
        items: Sequence[MenuItem] | None = None,
        columns: int = 2,
        tile_size: Literal["large"] | None = None,
    ) -> None:
        self._items = list(items) if items else []
        self._columns = columns
        self._tile_size = tile_size

    def add_item(self, item: MenuItem) -> None:
        self._items.append(item)

    def show(self) -> None:
        html.open_div(class_="mainmenu")
        for item in self._items:
            if not item.may_see():
                continue

            html.open_a(
                href=item.get_url(), onfocus="if (this.blur) this.blur();", class_=self._tile_size
            )
            html.icon(item.icon, item.title)
            html.div(item.title, class_="title")
            html.div(item.description, class_="subtitle")
            html.close_a()

        html.close_div()
