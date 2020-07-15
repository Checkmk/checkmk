#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Breadcrumb processing

Cares about rendering the breadcrumb which is shown at the top of all pages
"""

from typing import NamedTuple, MutableSequence, List, Iterable, Optional

from cmk.gui.globals import html

BreadcrumbItem = NamedTuple("BreadcrumbItem", [
    ("title", str),
    ("url", Optional[str]),
])


class Breadcrumb(MutableSequence[BreadcrumbItem]):
    def __init__(self, items: Iterable[BreadcrumbItem] = None):
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
                html.a(item.title, href=item.url)
            else:
                html.span(item.title)

        html.close_div()
