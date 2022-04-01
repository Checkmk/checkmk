#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import base64
from typing import Any, Callable, Dict, List, Optional, Tuple, TYPE_CHECKING, Union

import cmk.gui.utils.escaping as escaping
from cmk.gui.exceptions import MKUserError
from cmk.gui.globals import html, request, theme, transactions, user_errors
from cmk.gui.htmllib.foldable_container import (
    foldable_container_id,
    foldable_container_img_id,
    foldable_container_onclick,
)
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.utils.html import HTML

if TYPE_CHECKING:
    from typing import Sequence

    from cmk.gui.valuespec import Dictionary, Transform, ValueSpec

g_header_open = False
g_section_open = False


def get_input(valuespec: "ValueSpec", varprefix: str) -> Any:
    value = valuespec.from_html_vars(varprefix)
    valuespec.validate_value(value, varprefix)
    return value


# Edit a list of several dictionaries. Those can either be dictionary
# valuespec or just a list of elements. Each entry in dictionaries is
# a pair of key and either a list of elements or a Dictionary.
# TODO: As soon as the reports have been migrated to pagetypes.py
# we can drop edit_dictionaries()? At least the function for editing
# several dictionaries at once.
# TODO: Remove all call sites and clean this up! The mechanic of this
# is very uncommon compared to the other usages of valuespecs.
def edit_dictionaries(
    dictionaries: "Sequence[Tuple[str, Union[Transform, Dictionary]]]",
    value: Dict[str, Any],
    focus: Optional[str] = None,
    hover_help: bool = True,
    validate: Optional[Callable[[Any], None]] = None,
    title: Optional[str] = None,
    method: str = "GET",
    preview: bool = False,
    varprefix: str = "",
    formname: str = "form",
    consume_transid: bool = True,
):

    if request.get_ascii_input("filled_in") == formname and transactions.transaction_valid():
        if not preview and consume_transid:
            transactions.check_transaction()

        messages: List[str] = []
        new_value: Dict[str, Dict[str, Any]] = {}
        for keyname, vs_dict in dictionaries:
            dict_varprefix = varprefix + keyname
            new_value[keyname] = {}
            try:
                edited_value = vs_dict.from_html_vars(dict_varprefix)
                vs_dict.validate_value(edited_value, dict_varprefix)
                new_value[keyname].update(edited_value)
            except MKUserError as e:
                messages.append("%s: %s" % (vs_dict.title() or _("Properties"), e))
                user_errors.add(e)
            except Exception as e:
                messages.append("%s: %s" % (vs_dict.title() or _("Properties"), e))
                user_errors.add(MKUserError(None, str(e)))

            if validate and not user_errors:
                try:
                    validate(new_value[keyname])
                except MKUserError as e:
                    messages.append(str(e))
                    user_errors.add(e)

        if messages:
            messages_joined = "".join(["%s<br>\n" % m for m in messages])
            if not preview:
                html.show_error(messages_joined)
            else:
                raise MKUserError(None, messages_joined)
        else:
            return new_value

    html.begin_form(formname, method=method)
    for keyname, vs_dict in dictionaries:
        dict_varprefix = varprefix + keyname
        subvalue = value.get(keyname, {})
        vs_dict.render_input_as_form(dict_varprefix, subvalue)

    end()
    # Should be ignored be hidden_fields, but I do not dare to change it there
    request.del_var("filled_in")
    html.hidden_fields()
    html.end_form()


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
