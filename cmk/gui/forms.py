#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

import base64
import six

from cmk.gui.htmllib import HTML
from cmk.gui.i18n import _
from cmk.gui.globals import html
from cmk.gui.exceptions import MKUserError

g_header_open = False
g_section_open = False


# A input function with the same call syntax as htmllib.textinput()
def textinput(valuespec, varprefix, defvalue):
    if html.form_submitted(html.form_name):
        value = valuespec.from_html_vars(varprefix)
    else:
        value = defvalue
    valuespec.render_input(varprefix, value)


def get_input(valuespec, varprefix):
    value = valuespec.from_html_vars(varprefix)
    valuespec.validate_value(value, varprefix)
    return value


# TODO: Remove all call sites and clean this up! The mechanic of this
# and the edit_dictionaries() is very uncommon compared to the other
# usages of valuespecs.
def edit_dictionary(entries, value, **args):
    result = edit_dictionaries([("value", entries)], {"value": value}, **args)
    if result:
        return result["value"]
    return result


# Edit a list of several dictionaries. Those can either be dictionary
# valuespec or just a list of elements. Each entry in dictionaries is
# a pair of key and either a list of elements or a Dictionary.
# TODO: As soon as the reports have been migrated to pagetypes.py
# we can drop edit_dictionaries()? At least the function for editing
# several dictionaries at once.
# TODO: Remove all call sites and clean this up! The mechanic of this
# and the edit_dictionary() is very uncommon compared to the other
# usages of valuespecs.
def edit_dictionaries(dictionaries,
                      value,
                      focus=None,
                      hover_help=True,
                      validate=None,
                      buttontext=None,
                      title=None,
                      buttons=None,
                      method="GET",
                      preview=False,
                      varprefix="",
                      formname="form",
                      consume_transid=True):

    # Convert list of entries/dictionaries
    sections = []
    for keyname, d in dictionaries:
        if isinstance(d, list):
            sections.append((keyname, title or _("Properties"), d))
        else:
            sections.append((keyname, None, d))  # valuespec Dictionary, title used from dict

    if html.request.var("filled_in") == formname and html.transaction_valid():
        if not preview and consume_transid:
            html.check_transaction()

        messages = []
        new_value = {}
        for keyname, _section_title, entries in sections:
            if isinstance(entries, list):
                new_value[keyname] = value.get(keyname, {}).copy()
                for name, vs in entries:
                    if len(sections) == 1:
                        vp = varprefix
                    else:
                        vp = keyname + "_" + varprefix
                    try:
                        v = vs.from_html_vars(vp + name)
                        vs.validate_value(v, vp + name)
                        new_value[keyname][name] = v
                    except MKUserError as e:
                        messages.append("%s: %s" % (vs.title(), e))
                        html.add_user_error(e.varname, e)

            else:
                new_value[keyname] = {}
                try:
                    edited_value = entries.from_html_vars(keyname)
                    entries.validate_value(edited_value, keyname)
                    new_value[keyname].update(edited_value)
                except MKUserError as e:
                    messages.append("%s: %s" % (entries.title() or _("Properties"), e))
                    html.add_user_error(e.varname, e)
                except Exception as e:
                    messages.append("%s: %s" % (entries.title() or _("Properties"), e))
                    html.add_user_error(None, e)

            if validate and not html.has_user_errors():
                try:
                    validate(new_value[keyname])
                except MKUserError as e:
                    messages.append(e)
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
    for keyname, title1, entries in sections:
        subvalue = value.get(keyname, {})
        if isinstance(entries, list):
            header(title1)
            first = True
            for name, vs in entries:
                section(vs.title())
                html.help(vs.help())
                if name in subvalue:
                    v = subvalue[name]
                else:
                    v = vs.default_value()
                if len(sections) == 1:
                    vp = varprefix
                else:
                    vp = keyname + "_" + varprefix
                vs.render_input(vp + name, v)
                if (not focus and first) or (name == focus):
                    vs.set_focus(vp + name)
                    first = False
        else:
            entries.render_input_as_form(keyname, subvalue)

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
def edit_valuespec(vs,
                   value,
                   buttontext=None,
                   method="GET",
                   varprefix="",
                   validate=None,
                   formname="form",
                   consume_transid=True,
                   focus=None):

    if html.request.var("filled_in") == formname and html.transaction_valid():
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


# New functions for painting forms


def header(title, isopen=True, table_id="", narrow=False, css=None):
    global g_header_open, g_section_open
    if g_header_open:
        end()

    html.open_table(id_=table_id if table_id else None,
                    class_=["nform", "narrow" if narrow else None, css if css else None])

    html.begin_foldable_container(
        treename=html.form_name if html.form_name else "nform",
        id_=base64.b64encode(title.encode("utf-8") if isinstance(title, unicode) else title),
        isopen=isopen,
        title=title,
        indent="nform")
    html.tr(html.render_td('', colspan=2))
    g_header_open = True
    g_section_open = False


# container without legend and content
def container():
    global g_section_open
    if g_section_open:
        html.close_td()
        html.close_tr()
    html.open_tr()
    html.open_td(colspan=2, class_=container)
    g_section_open = True


def space():
    html.tr(html.render_td('', colspan=2, style="height:15px;"))


def section(title=None,
            checkbox=None,
            section_id=None,
            simple=False,
            hide=False,
            legend=True,
            css=None):
    global g_section_open
    if g_section_open:
        html.close_td()
        html.close_tr()
    html.open_tr(id_=section_id, class_=[css], style="display:none;" if hide else None)

    if legend:
        html.open_td(class_=["legend", "simple" if simple else None])
        if title:
            html.open_div(class_=["title", "withcheckbox" if checkbox else None],
                          title=html.strip_tags(title))
            html.write(html.permissive_attrencode(title))
            html.span('.' * 100, class_="dots")
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
    global g_header_open
    g_header_open = False
    if g_section_open:
        html.close_td()
        html.close_tr()
    html.end_foldable_container()
    html.tr(html.render_td('', colspan=2), class_=["bottom"])
    html.close_tbody()
    html.close_table()
