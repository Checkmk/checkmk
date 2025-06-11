#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-override, no-untyped-def"

"""Breadcrumb processing

Cares about rendering the breadcrumb which is shown at the top of all pages
"""

from __future__ import annotations

from collections.abc import Iterable, MutableSequence
from typing import NamedTuple

import cmk.gui.htmllib.html
from cmk.gui.type_defs import MainMenu
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

    def __getitem__(self, index):
        return self._items[index]

    def __setitem__(self, index, value):
        self._items[index] = value

    def __delitem__(self, index):
        self._items.pop(index)

    def insert(self, index, value):
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
