#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import base64
from typing import Union, Callable, Dict, Optional, Tuple, List, Any, TYPE_CHECKING
from six import ensure_binary, ensure_str

import cmk.gui.escaping as escaping
from cmk.gui.htmllib import HTML
from cmk.gui.i18n import _
from cmk.gui.globals import html
from cmk.gui.exceptions import MKUserError

if TYPE_CHECKING:
    from typing import Sequence
    from cmk.gui.valuespec import Dictionary, ValueSpec, Transform

g_header_open = False
g_section_open = False


def get_input(valuespec: 'ValueSpec', varprefix: str) -> Any:
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
def edit_dictionaries(dictionaries: 'Sequence[Tuple[str, Union[Transform, Dictionary]]]',
                      value: Dict[str, Any],
                      focus: Optional[str] = None,
                      hover_help: bool = True,
                      validate: Optional[Callable[[Any], None]] = None,
                      title: Optional[str] = None,
                      method: str = "GET",
                      preview: bool = False,
                      varprefix: str = "",
                      formname: str = "form",
                      consume_transid: bool = True):

    if html.request.get_ascii_input("filled_in") == formname and html.transaction_valid():
        if not preview and consume_transid:
            html.check_transaction()

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
                html.add_user_error(e.varname, e)
            except Exception as e:
                messages.append("%s: %s" % (vs_dict.title() or _("Properties"), e))
                html.add_user_error(None, e)

            if validate and not html.has_user_errors():
                try:
                    validate(new_value[keyname])
                except MKUserError as e:
                    messages.append("%s" % e)
                    html.add_user_error(e.varname, e)

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
    html.request.del_var("filled_in")
    html.hidden_fields()
    html.end_form()


# New functions for painting forms


def header(title: str,
           isopen: bool = True,
           table_id: str = "",
           narrow: bool = False,
           css: Optional[str] = None,
           show_advanced_toggle: bool = False) -> None:
    global g_header_open, g_section_open
    if g_header_open:
        end()

    html.open_table(id_=table_id if table_id else None,
                    class_=[
                        "nform",
                        "narrow" if narrow else None,
                        css if css else None,
                        "open" if isopen else "closed",
                    ])

    _begin_foldable_nform_container(
        treename=html.form_name if html.form_name else "nform",
        id_=ensure_str(base64.b64encode(ensure_binary(title))),
        isopen=isopen,
        title=title,
        show_advanced_toggle=show_advanced_toggle,
    )
    html.tr(html.render_td('', colspan=2))
    g_header_open = True
    g_section_open = False


def _begin_foldable_nform_container(
    treename: str,
    id_: str,
    isopen: bool,
    title: str,
    show_advanced_toggle: bool,
) -> bool:
    isopen = html.foldable_container_is_open(treename, id_, isopen)
    onclick = html.foldable_container_onclick(treename, id_, fetch_url=None)
    img_id = html.foldable_container_img_id(treename, id_)
    container_id = html.foldable_container_id(treename, id_)

    html.open_thead()
    html.open_tr(class_="heading")
    html.open_td(id_="nform.%s.%s" % (treename, id_), onclick=onclick, colspan=2)
    html.img(id_=img_id,
             class_=["treeangle", "nform", "open" if isopen else "closed"],
             src="themes/%s/images/tree_closed.png" % (html.get_theme()),
             align="absbottom")
    html.write_text(title)
    if show_advanced_toggle:
        html.more_button("foldable_" + id_, dom_levels_up=4)
    html.close_td()
    html.close_tr()
    html.close_thead()
    html.open_tbody(id_=container_id, class_=["open" if isopen else "closed"])

    return isopen


# container without legend and content
def container() -> None:
    global g_section_open
    section_close()
    html.open_tr()
    html.open_td(colspan=2)
    g_section_open = True


def space() -> None:
    html.tr(html.render_td('', colspan=2, style="height:15px;"))


def section(title: Union[None, HTML, str] = None,
            checkbox: Union[None, HTML, str, Tuple[str, bool, str]] = None,
            section_id: Optional[str] = None,
            simple: bool = False,
            hide: bool = False,
            legend: bool = True,
            css: Optional[str] = None,
            is_advanced: bool = False) -> None:
    global g_section_open
    section_close()
    html.open_tr(
        id_=section_id,
        class_=[css, "advanced" if is_advanced else "basic"],
        style="display:none;" if hide else None,
    )

    if legend:
        html.open_td(class_=["legend", "simple" if simple else None])
        if title:
            html.open_div(class_=["title", "withcheckbox" if checkbox else None],
                          title=escaping.strip_tags(title))
            html.write(escaping.escape_text(title))
            html.span('.' * 200, class_="dots")
            html.close_div()
        if checkbox:
            html.open_div(class_="checkbox")
            if isinstance(checkbox, (str, HTML)):
                html.write(checkbox)
            else:
                name, active, attrname = checkbox
                html.checkbox(name,
                              active,
                              onclick='cmk.wato.toggle_attribute(this, \'%s\')' % attrname)
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
    html.tr(html.render_td('', colspan=2), class_=["bottom"])
    html.close_tbody()
    html.close_table()
