#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Breadcrumb processing

Cares about rendering the breadcrumb which is shown at the top of all pages
"""

from typing import Iterable, List, MutableSequence, NamedTuple, Optional, TYPE_CHECKING, Union

from cmk.gui.globals import html
from cmk.gui.type_defs import MegaMenu
from cmk.gui.utils.escaping import escape_html
from cmk.gui.utils.speaklater import LazyString

if TYPE_CHECKING:
    from cmk.gui.pagetypes import PagetypeTopics


class BreadcrumbItem(NamedTuple):
    title: Union[str, LazyString]
    url: Optional[str]


class Breadcrumb(MutableSequence[BreadcrumbItem]):  # pylint: disable=too-many-ancestors
    def __init__(self, items: Optional[Iterable[BreadcrumbItem]] = None):
        super().__init__()
        self._items: List[BreadcrumbItem] = list(items) if items else []

    def __len__(self):
        return len(self._items)

    def __getitem__(self, index):
        return self._items[index]

    def __setitem__(self, index, value):
        self._items[index] = value

    def __delitem__(self, index):
        self._items.pop(index)

    def insert(self, index, value):
        self._items.insert(index, value)

    def __add__(self, other):
        return Breadcrumb(list(self) + list(other))


class BreadcrumbRenderer:
    def show(self, breadcrumb: Breadcrumb) -> None:
        html.open_div(class_="breadcrumb")

        for item in breadcrumb:
            if item.url:
                html.a(escape_html(str(item.title)), href=item.url)
            else:
                html.span(escape_html(str(item.title)))

        html.close_div()


def make_simple_page_breadcrumb(menu: MegaMenu, title: str) -> Breadcrumb:
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


def make_topic_breadcrumb(menu: MegaMenu, topic: "PagetypeTopics") -> Breadcrumb:
    """Helper to create a breadcrumb down to topic level"""
    # 1. Main menu level
    breadcrumb = make_main_menu_breadcrumb(menu)

    # 2. Topic level
    breadcrumb.append(
        BreadcrumbItem(
            title=topic.title(),
            url=None,
        )
    )

    return breadcrumb


def make_main_menu_breadcrumb(menu: MegaMenu) -> Breadcrumb:
    """Create a breadcrumb for the main menu level"""
    return Breadcrumb(
        [
            BreadcrumbItem(
                title=menu.title,
                url=None,
            )
        ]
    )
