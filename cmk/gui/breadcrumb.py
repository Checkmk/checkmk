#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Breadcrumb processing

Cares about rendering the breadcrumb which is shown at the top of all pages
"""

from __future__ import annotations

from collections.abc import Iterable, MutableSequence
from typing import NamedTuple, overload

import cmk.gui.htmllib.html
from cmk.gui.main_menu_types import MainMenu
from cmk.gui.utils.html import HTML
from cmk.gui.utils.speaklater import LazyString


class BreadcrumbItem(NamedTuple):
    title: str | LazyString
    url: str | None


class Breadcrumb(MutableSequence[BreadcrumbItem]):
    def __init__(self, items: Iterable[BreadcrumbItem] | None = None) -> None:
        super().__init__()
        self._items: list[BreadcrumbItem] = list(items) if items else []

    def __len__(self) -> int:
        return len(self._items)

    @overload
    def __getitem__(self, index: int) -> BreadcrumbItem: ...

    @overload
    def __getitem__(self, index: slice[int, int, int]) -> MutableSequence[BreadcrumbItem]: ...

    def __getitem__(self, index: int | slice) -> BreadcrumbItem | MutableSequence[BreadcrumbItem]:
        return self._items[index]

    @overload
    def __setitem__(self, index: int, value: BreadcrumbItem) -> None: ...

    @overload
    def __setitem__(self, index: slice[int, int, int], value: Iterable[BreadcrumbItem]) -> None: ...

    def __setitem__(
        self, index: int | slice, value: BreadcrumbItem | Iterable[BreadcrumbItem]
    ) -> None:
        self._items[index] = value  # type: ignore[index,assignment]

    @overload
    def __delitem__(self, index: int) -> None: ...

    @overload
    def __delitem__(self, index: slice[int, int, int]) -> None: ...

    def __delitem__(self, index: int | slice) -> None:
        if isinstance(index, int):
            self._items.pop(index)
        else:
            del self._items[index]

    def insert(self, index: int, value: BreadcrumbItem) -> None:
        self._items.insert(index, value)

    def __add__(self, other: Breadcrumb) -> Breadcrumb:
        return Breadcrumb(list(self) + list(other))


class BreadcrumbRenderer:
    def show(self, breadcrumb: Breadcrumb) -> None:
        cmk.gui.htmllib.html.html.open_div(class_="breadcrumb")

        for item in breadcrumb:
            if item.url:
                cmk.gui.htmllib.html.html.a(HTML.with_escaping(str(item.title)), href=item.url)
            else:
                cmk.gui.htmllib.html.html.span(HTML.with_escaping(str(item.title)))

        cmk.gui.htmllib.html.html.close_div()


def make_simple_page_breadcrumb(menu: MainMenu, title: str) -> Breadcrumb:
    """Helper to create breadcrumbs for simple pages

    This can be used to create breadcrumbs for pages that are on the level
    right below the main menu
    """
    breadcrumb = make_main_menu_breadcrumb(menu)
    breadcrumb.append(make_current_page_breadcrumb_item(title))

    return breadcrumb


def make_current_page_breadcrumb_item(title: str) -> BreadcrumbItem:
    """Helper to create a breadcrumb link to the current page"""
    return BreadcrumbItem(
        title=title,
        url="javascript:document.location.reload(false)",
    )


def make_topic_breadcrumb(
    menu: MainMenu,
    topic_title: str | LazyString,
) -> Breadcrumb:
    """Helper to create a breadcrumb down to topic level"""
    # 1. Main menu level
    breadcrumb = make_main_menu_breadcrumb(menu)

    # 2. Topic level
    breadcrumb.append(
        BreadcrumbItem(
            title=topic_title,
            url=None,
        )
    )

    return breadcrumb


def make_main_menu_breadcrumb(menu: MainMenu) -> Breadcrumb:
    """Create a breadcrumb for the main menu level"""
    return Breadcrumb(
        [
            BreadcrumbItem(
                title=menu.title,
                url=None,
            )
        ]
    )
