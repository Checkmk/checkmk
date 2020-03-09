#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import base64
from typing import Union, Callable, Text, Dict, Optional, Tuple, List, Any, TYPE_CHECKING  # pylint: disable=unused-import
import six

import cmk.gui.escaping as escaping
from cmk.gui.htmllib import HTML
from cmk.gui.i18n import _
from cmk.gui.globals import html
from cmk.gui.exceptions import MKUserError

if TYPE_CHECKING:
    from cmk.gui.valuespec import Dictionary, ValueSpec, Transform  # pylint: disable=unused-import

g_header_open = False
g_section_open = False


def get_input(valuespec, varprefix):
    # type: (ValueSpec, str) -> Any
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
    dictionaries,  # type: List[Tuple[str, Union[Transform, Dictionary]]]
    value,  # type: Dict[str, Any]
    focus=None,  # type: Optional[str]
    hover_help=True,  # type: bool
    validate=None,  # type: Optional[Callable[[Any], None]]
    buttontext=None,  # type: Optional[Text]
    title=None,  # type: Optional[Text]
    buttons=None,  # type: List[Tuple[str, Text, str]]
    method="GET",  # type: str
    preview=False,  # type: bool
    varprefix="",  # type: str
    formname="form",  # type: str
    consume_transid=True  # type: bool
):

    if html.request.get_ascii_input("filled_in") == formname and html.transaction_valid():
        if not preview and consume_transid:
            html.check_transaction()

        messages = []  # type: List[Text]
        new_value = {}  # type: Dict[str, Dict[str, Any]]
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
    if buttons:
        for name, button_title, _icon in buttons:
            html.button(name, button_title)
    else:
        if buttontext is None:
            buttontext = _("Save")
        html.button("save", buttontext)
    # Should be ignored be hidden_fields, but I do not dare to change it there
    html.request.del_var("filled_in")
    html.hidden_fields()
    html.end_form()


# Similar but for editing an arbitrary valuespec
def edit_valuespec(
    vs,  # type: Dictionary
    value,  # type: Dict[str, Any]
    buttontext=None,  # type: Optional[Text]
    method="GET",  # type: str
    varprefix="",  # type: str
    validate=None,  # type: Optional[Callable[[Dict[str, Any]], None]]
    formname="form",  # type: str
    consume_transid=True,  # type: bool
    focus=None  # type: Optional[str]
):
    # type: (...) -> Optional[Dict[str, Any]]

    if html.request.get_ascii_input("filled_in") == formname and html.transaction_valid():
        if consume_transid:
            html.check_transaction()

        messages = []
        try:
            new_value = vs.from_html_vars(varprefix)
            vs.validate_value(new_value, varprefix)

        except MKUserError as e:
            messages.append("%s: %s" % (vs.title(), e.message))
            html.add_user_error(e.varname, e.message)

        if validate and not html.has_user_errors():
            try:
                validate(new_value)
            except MKUserError as e:
                messages.append(e.message)
                html.add_user_error(e.varname, e.message)

        if messages:
            html.show_error("".join(["%s<br>\n" % m for m in messages]))
        else:
            return new_value

    html.begin_form(formname, method=method)
    html.help(vs.help())
    vs.render_input(varprefix, value)
    if buttontext is None:
        buttontext = _("Save")
    html.button("save", buttontext)
    # Should be ignored be hidden_fields, but I do not dare to change it there
    html.request.del_var("filled_in")
    html.hidden_fields()
    if focus:
        html.set_focus(focus)
    else:
        vs.set_focus(varprefix)
    html.end_form()
    return None


# New functions for painting forms


def header(title, isopen=True, table_id="", narrow=False, css=None):
    # type: (Text, bool, str, bool, Optional[str]) -> None
    global g_header_open, g_section_open
    if g_header_open:
        end()

    html.open_table(id_=table_id if table_id else None,
                    class_=["nform", "narrow" if narrow else None, css if css else None])

    html.begin_foldable_container(treename=html.form_name if html.form_name else "nform",
                                  id_=six.ensure_str(base64.b64encode(six.ensure_binary(title))),
                                  isopen=isopen,
                                  title=title,
                                  indent="nform")
    html.tr(html.render_td('', colspan=2))
    g_header_open = True
    g_section_open = False


# container without legend and content
def container():
    # type: () -> None
    global g_section_open
    if g_section_open:
        html.close_td()
        html.close_tr()
    html.open_tr()
    html.open_td(colspan=2)
    g_section_open = True


def space():
    # type: () -> None
    html.tr(html.render_td('', colspan=2, style="height:15px;"))


def section(title=None,
            checkbox=None,
            section_id=None,
            simple=False,
            hide=False,
            legend=True,
            css=None):
    # type: (Optional[Text], Optional[Union[Text, str, HTML]], Optional[str], bool, bool, bool, Optional[str]) -> None
    global g_section_open
    if g_section_open:
        html.close_td()
        html.close_tr()
    html.open_tr(id_=section_id, class_=[css], style="display:none;" if hide else None)

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
            if isinstance(checkbox, six.string_types + (HTML,)):
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


def end():
    # type: () -> None
    global g_header_open
    g_header_open = False
    if g_section_open:
        html.close_td()
        html.close_tr()
    html.end_foldable_container()
    html.tr(html.render_td('', colspan=2), class_=["bottom"])
    html.close_tbody()
    html.close_table()
