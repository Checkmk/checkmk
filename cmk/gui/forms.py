#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import base64
from collections.abc import Callable
from typing import NamedTuple

from cmk.gui.htmllib.foldable_container import (
    foldable_container_id,
    foldable_container_img_id,
    foldable_container_onclick,
)
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.logged_in import user
from cmk.gui.theme.current_theme import theme
from cmk.gui.utils import escaping
from cmk.gui.utils.html import HTML

g_header_open = False
g_section_open = False


# New functions for painting forms


class FoldableAttrs(NamedTuple):
    container_id: str
    class_: list[str]


def header(
    title: str,
    # TODO Cleanup dependencies on call sites: foldable & isopen
    foldable: bool = True,
    isopen: bool = True,
    table_id: str = "",
    narrow: bool = False,
    css: str | None = None,
    show_table_head: bool = True,
    show_more_toggle: bool = False,
    show_more_mode: bool = False,
    help_text: str | HTML | None = None,
) -> None:
    global g_header_open, g_section_open
    if g_header_open:
        end()

    id_ = base64.b64encode(title.encode()).decode()
    treename = html.form_name or "nform"
    if foldable:
        foldable_attrs = FoldableAttrs(
            container_id=foldable_container_id(treename, id_),
            class_=["open" if user.get_tree_state(treename, id_, isopen) else "closed"],
        )
    else:
        foldable_attrs = FoldableAttrs(container_id=id_, class_=[])

    class_ = ["nform"]
    if narrow:
        class_.append("narrow")
    if css:
        class_.append(css)
    class_.extend(foldable_attrs.class_)
    if user.get_show_more_setting("foldable_%s" % id_) or show_more_mode:
        class_.append("more")

    html.open_table(
        id_=table_id if table_id else None,
        class_=class_,
    )

    if show_table_head:
        _table_head(
            id_=id_,
            treename=treename,
            foldable_attrs=foldable_attrs,
            title=title,
            show_more_toggle=show_more_toggle,
            help_text=help_text,
        )

    html.open_tbody(id_=foldable_attrs.container_id, class_=foldable_attrs.class_)
    html.tr(HTMLWriter.render_td("", colspan=2))
    g_header_open = True
    g_section_open = False


def _table_head(
    id_: str,
    treename: str,
    foldable_attrs: FoldableAttrs,
    title: str,
    show_more_toggle: bool,
    help_text: str | HTML | None = None,
) -> None:
    html.open_thead()
    html.open_tr(class_="heading")
    if foldable_attrs.class_:
        html.open_td(
            id_=f"nform.{treename}.{id_}",
            onclick=foldable_container_onclick(treename, id_, fetch_url=None),
            colspan=2,
        )
        html.img(
            id_=foldable_container_img_id(treename, id_),
            class_=["treeangle", "nform"] + foldable_attrs.class_,
            src=theme.url("images/tree_closed.svg"),
            align="absbottom",
        )
    else:
        html.open_td(id_=f"nform.{treename}.{id_}", colspan=2)

    html.write_text_permissive(title)
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
    html.tr(HTMLWriter.render_td("", colspan=2, style="height:15px;"))


def warning_message(message: str) -> None:
    html.tr(
        HTMLWriter.render_td(
            html.render_div(html.render_div(message, class_="content"), class_="warning_container"),
            colspan=2,
        )
    )


def section(
    title: None | HTML | str = None,
    checkbox: None | HTML | str | tuple[str, bool, str] = None,
    section_id: str | None = None,
    simple: bool = False,
    hide: bool = False,
    legend: bool = True,
    css: str | None = None,
    is_show_more: bool = False,
    is_changed: bool = False,
    is_required: bool = False,
) -> None:
    global g_section_open
    section_close()
    html.open_tr(
        id_=section_id,
        class_=([] if css is None else [css])
        + ["show_more_mode" if is_show_more and not is_changed else "basic"],
        style="display:none;" if hide else None,
    )

    if legend:
        html.open_td(class_=["legend"] + (["simple"] if simple else []))
        if title:
            html.open_div(
                class_=["title"] + (["withcheckbox"] if checkbox else []),
                title=escaping.strip_tags(title),
            )
            html.write_text_permissive(title)
            html.span("." * 200, class_=["dots"] + (["required"] if is_required else []))
            html.close_div()
        if checkbox:
            html.open_div(class_="checkbox")
            if isinstance(checkbox, str | HTML):
                html.write_text_permissive(checkbox)
            else:
                name, active, attrname = checkbox
                html.checkbox(
                    name, active, onclick="cmk.wato.toggle_attribute(this, '%s')" % attrname
                )
            html.close_div()
        html.close_td()
    html.open_td(
        class_=["content"] + (["simple"] if simple else []), colspan=2 if not legend else None
    )
    g_section_open = True


def section_close() -> None:
    if g_section_open:
        html.close_td()
        html.close_tr()


def end() -> None:
    global g_header_open
    g_header_open = False
    section_close()
    html.tr(HTMLWriter.render_td("", colspan=2), class_=["bottom"])
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
    for varname, value in request.itervars(form_prefix):
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
            request.del_var(varname)


def open_submit_button_container_div(tooltip: str) -> None:
    html.open_div(
        class_="submit_button_container",
        data_title=tooltip,
        title=tooltip,
    )
