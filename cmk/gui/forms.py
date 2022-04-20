#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import base64
from typing import Callable, Optional, Tuple, Union

import cmk.gui.utils.escaping as escaping
from cmk.gui.globals import html, theme
from cmk.gui.htmllib.foldable_container import (
    foldable_container_id,
    foldable_container_img_id,
    foldable_container_onclick,
)
from cmk.gui.logged_in import user
from cmk.gui.utils.html import HTML

g_header_open = False
g_section_open = False


# New functions for painting forms


def header(
    title: str,
    isopen: bool = True,
    table_id: str = "",
    narrow: bool = False,
    css: Optional[str] = None,
    show_table_head: bool = True,
    show_more_toggle: bool = False,
    show_more_mode: bool = False,
    help_text: Union[str, HTML, None] = None,
) -> None:
    global g_header_open, g_section_open
    if g_header_open:
        end()

    id_ = base64.b64encode(title.encode()).decode()
    treename = html.form_name or "nform"
    isopen = user.get_tree_state(treename, id_, isopen)
    container_id = foldable_container_id(treename, id_)

    html.open_table(
        id_=table_id if table_id else None,
        class_=[
            "nform",
            "narrow" if narrow else None,
            css if css else None,
            "open" if isopen else "closed",
            "more" if user.get_show_more_setting("foldable_%s" % id_) or show_more_mode else None,
        ],
    )

    if show_table_head:
        _table_head(
            treename=treename,
            id_=id_,
            isopen=isopen,
            title=title,
            show_more_toggle=show_more_toggle,
            help_text=help_text,
        )

    html.open_tbody(id_=container_id, class_=["open" if isopen else "closed"])
    html.tr(html.render_td("", colspan=2))
    g_header_open = True
    g_section_open = False


def _table_head(
    treename: str,
    id_: str,
    isopen: bool,
    title: str,
    show_more_toggle: bool,
    help_text: Union[str, HTML, None] = None,
) -> None:
    onclick = foldable_container_onclick(treename, id_, fetch_url=None)
    img_id = foldable_container_img_id(treename, id_)

    html.open_thead()
    html.open_tr(class_="heading")
    html.open_td(id_="nform.%s.%s" % (treename, id_), onclick=onclick, colspan=2)
    html.img(
        id_=img_id,
        class_=["treeangle", "nform", "open" if isopen else "closed"],
        src=theme.url("images/tree_closed.svg"),
        align="absbottom",
    )
    html.write_text(title)
    html.help(help_text)
    if show_more_toggle:
        html.more_button("foldable_" + id_, dom_levels_up=4, with_text=True)
    html.close_td()
    html.close_tr()
    html.close_thead()


# container without legend and content
def container() -> None:
    global g_section_open
    section_close()
    html.open_tr()
    html.open_td(colspan=2)
    g_section_open = True


def space() -> None:
    html.tr(html.render_td("", colspan=2, style="height:15px;"))


def section(
    title: Union[None, HTML, str] = None,
    checkbox: Union[None, HTML, str, Tuple[str, bool, str]] = None,
    section_id: Optional[str] = None,
    simple: bool = False,
    hide: bool = False,
    legend: bool = True,
    css: Optional[str] = None,
    is_show_more: bool = False,
    is_changed: bool = False,
    is_required: bool = False,
) -> None:
    global g_section_open
    section_close()
    html.open_tr(
        id_=section_id,
        class_=[css, "show_more_mode" if is_show_more and not is_changed else "basic"],
        style="display:none;" if hide else None,
    )

    if legend:
        html.open_td(class_=["legend", "simple" if simple else None])
        if title:
            html.open_div(
                class_=["title", "withcheckbox" if checkbox else None],
                title=escaping.strip_tags(title),
            )
            html.write_text(title)
            html.span("." * 200, class_=["dots", "required" if is_required else None])
            html.close_div()
        if checkbox:
            html.open_div(class_="checkbox")
            if isinstance(checkbox, (str, HTML)):
                html.write_text(checkbox)
            else:
                name, active, attrname = checkbox
                html.checkbox(
                    name, active, onclick="cmk.wato.toggle_attribute(this, '%s')" % attrname
                )
            html.close_div()
        html.close_td()
    html.open_td(class_=["content", "simple" if simple else None])
    g_section_open = True


def section_close() -> None:
    if g_section_open:
        html.close_td()
        html.close_tr()


def end() -> None:
    global g_header_open
    g_header_open = False
    section_close()
    html.tr(html.render_td("", colspan=2), class_=["bottom"])
    html.close_tbody()
    html.close_table()


def remove_unused_vars(
    form_prefix: str,
    is_var_to_delete: Callable[[str, str, str], bool] = lambda prefix, varname, value: True,
) -> None:
    """Delete all variables for a form with prefix "form_prefix" that are not
    activated by a "varname_USE" entry.

    * simple example:

      'search_p_fulltext_USE':'on'
      'search_p_fulltext':'my search text'

    * is_var_to_delete: determines variables to keep
    """
    checkboxes, variables = set(), {}
    for varname, value in html.request.itervars(form_prefix):
        if varname.endswith("_USE"):
            checkboxes.add(varname)
            continue
        variables[varname] = value

    active_prefixes = {
        active_checkbox.rsplit("_USE")[0]
        for active_checkbox in checkboxes
        if html.get_checkbox(active_checkbox)
    }

    for varname, value in variables.items():
        if not any(varname.startswith(p) for p in active_prefixes) or is_var_to_delete(
            form_prefix, varname, value
        ):
            html.request.del_var(varname)
