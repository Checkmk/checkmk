#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Foldable containers for pages"""

import json
from contextlib import contextmanager
from typing import Union, Optional, Iterator

from cmk.gui.globals import html, theme, user
from cmk.gui.utils.html import HTML

from ._tag_rendering import HTMLContent

__all__ = [
    "foldable_container",
    "foldable_container_id",
    "foldable_container_img_id",
    "foldable_container_onclick",
]


@contextmanager
def foldable_container(
    *,
    treename: str,
    id_: str,
    isopen: bool,
    title: HTMLContent,
    indent: Union[str, None, bool] = True,
    first: bool = False,
    icon: Optional[str] = None,
    fetch_url: Optional[str] = None,
    title_url: Optional[str] = None,
    title_target: Optional[str] = None,
    padding: int = 15,
) -> Iterator[bool]:
    isopen = user.get_tree_state(treename, id_, isopen)
    onclick = foldable_container_onclick(treename, id_, fetch_url)
    img_id = foldable_container_img_id(treename, id_)
    container_id = foldable_container_id(treename, id_)

    html.open_div(class_=["foldable", "open" if isopen else "closed"])

    if isinstance(title, HTML):  # custom HTML code
        html.write_text(title)

    else:
        html.open_b(class_=["treeangle", "title"], onclick=None if title_url else onclick)

        if title_url:
            html.a(title, href=title_url, target=title_target)
        else:
            html.write_text(title)
        html.close_b()

    if icon:
        html.img(
            id_=img_id,
            class_=[
                "treeangle",
                "title",
                # Although foldable_sidebar is given via the argument icon it should not be
                # displayed as big as an icon.
                "icon" if icon != "foldable_sidebar" else None,
                "open" if isopen else "closed",
            ],
            src=theme.url(f"images/icon_{icon}.svg"),
            onclick=onclick)
    else:
        html.img(id_=img_id,
                 class_=["treeangle", "open" if isopen else "closed"],
                 src=theme.url("images/tree_closed.svg"),
                 onclick=onclick)

    if indent != "form" or not isinstance(title, HTML):
        html.br()

    indent_style = "padding-left: %dpx; " % (padding if indent else 0)
    if indent == "form":
        html.close_td()
        html.close_tr()
        html.close_table()
        indent_style += "margin: 0; "
    html.open_ul(id_=container_id,
                 class_=["treeangle", "open" if isopen else "closed"],
                 style=indent_style)

    yield isopen

    html.close_ul()
    html.close_div()


def foldable_container_onclick(treename: str, id_: str, fetch_url: Optional[str]) -> str:
    return "cmk.foldable_container.toggle(%s, %s, %s)" % (
        json.dumps(treename), json.dumps(id_), json.dumps(fetch_url if fetch_url else ''))


def foldable_container_img_id(treename: str, id_: str) -> str:
    return "treeimg.%s.%s" % (treename, id_)


def foldable_container_id(treename: str, id_: str) -> str:
    return "tree.%s.%s" % (treename, id_)
