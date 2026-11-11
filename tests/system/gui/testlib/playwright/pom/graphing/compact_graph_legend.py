#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""The compact legend a graph figure draws below its graph.

One item per series - metric, threshold line or shaded region - each a visibility toggle, a
color swatch and the series name, all laid out in a single row.
"""

import re
from typing import NamedTuple

from playwright.sync_api import Locator


class ItemBox(NamedTuple):
    top: float
    height: float


class CompactGraphLegend:
    """The compact legend of one graph figure.

    Args:
        root: the legend's element, `.graphing-graph-legend-compact`.
    """

    def __init__(self, root: Locator) -> None:
        self.root = root

    @property
    def items(self) -> Locator:
        return self.root.locator(".graphing-graph-legend-compact__item")

    @property
    def _names(self) -> Locator:
        return self.items.locator(".graphing-graph-legend-compact__name")

    def names(self) -> list[str]:
        """The series names, in the order the legend shows them.

        Read from the text, not the rendered width: a long name is truncated in the middle by
        CSS only.
        """
        return [name.strip() for name in self._names.all_text_contents()]

    def item(self, name: str) -> Locator:
        name_element = self.root.page.locator(
            ".graphing-graph-legend-compact__name",
            has_text=re.compile(rf"^\s*{re.escape(name)}\s*$"),
        )
        return self.items.filter(has=name_element)

    def swatch(self, name: str) -> Locator:
        return self.item(name).locator(".graphing-graph-legend-compact__swatch")

    def visibility_toggle(self, name: str) -> Locator:
        """The button showing or hiding the series, named after it and pressed while shown."""
        return self.item(name).get_by_role("button", name=name, exact=True)

    def item_boxes(self) -> list[ItemBox]:
        """Where each item is drawn, vertically, in the order the legend shows them."""
        boxes = self.items.evaluate_all(
            "items => items.map(item => {"
            " const box = item.getBoundingClientRect();"
            " return [box.top, box.height];"
            "})"
        )
        return [ItemBox(top, height) for top, height in boxes]
