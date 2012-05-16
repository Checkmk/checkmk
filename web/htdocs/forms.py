#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2012             mk@mathias-kettner.de |
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
# ails.  You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

from lib import *
import htmllib

# A input function with the same call syntax as htmllib.textinput()
def input(valuespec, varprefix, defvalue):
    if html.form_filled_in():
        value = valuespec.from_html_vars(varprefix)
    else:
        value = defvalue
    valuespec.render_input(varprefix, value)

def get_input(valuespec, varprefix):
    value = valuespec.from_html_vars(varprefix)
    valuespec.validate_value(value, varprefix)
    return value


def edit_dictionary(entries, value, focus=None, hover_help=True, validate=None, buttontext = None):
    new_value = value.copy()
    if html.var("filled_in") == "form" and html.check_transaction():
        messages = []
        for name, vs in entries: 
            try:
                v = vs.from_html_vars(name)
                vs.validate_value(v, name)
                new_value[name] = v
            except MKUserError, e:
                messages.append(u"%s: %s" % (vs.title(), e.message))
                html.add_user_error(e.varname, e.message)

        if validate:
            try:
                validate(new_value)
            except MKUserError, e:
                messages.append(e.message)
                html.add_user_error(e.varname, e.message)

        if messages:
            html.show_error("".join(["%s<br>\n" % m for m in messages]))
        else:
            return new_value

    html.begin_form("form")
    html.write("<table class=form>\n")
    first = True
    for name, vs in entries:

        html.write("<tr><td ")
        if vs.help() and hover_help:
            html.write('title="%s" ' % vs.help().replace('"', "&quot;"))
        html.write("class=legend>%s" % (vs.title() or "")) 
        if vs.help() and not hover_help:
            html.write("<br><i>%s</i>" % vs.help())
        html.write("</td><td class=content>")
        if name in value:
            v = value[name]
        else:
            v = vs.default_value()
        vs.render_input(name, v)
        if (not focus and first) or (name == focus):
            vs.set_focus(name)
            first = False 
    html.write("<tr><td class=buttons colspan=2>")
    if buttontext == None:
        buttontext = _("Save")
    html.button("save", buttontext)
    html.write("</td></tr>\n")
    html.write("</table>\n")
    html.hidden_fields()
    html.end_form()

# New functions for painting forms

def strip_bad_chars(x):
    return "".join([c for c in x if c > ' ' and c < 'z' and c not in ["'", '"']])

def header(title, isopen = True, table_id = ""):
    global g_header_open
    global g_section_open
    global g_section_isopen
    try:
        if g_header_open:
            end()
    except:
        pass

    if table_id:
        table_id = ' id="%s"' % table_id
    else:
        table_id = ''
    html.write('<table %s class=nform>' % table_id)
    fold_id = strip_bad_chars(title)
    g_section_isopen = html.begin_foldable_container(html.form_name, fold_id, isopen, title, indent="nform")
    html.write('<tr class=top style="display: %s"><td colspan=2></td></tr>' % (not isopen and "none" or ""))
    g_header_open = True
    g_section_open = False

def section(title = None, checkbox = None, id = ""): 
    global g_section_open
    if g_section_open:
        html.write('</td></tr>')
    if id:
        id = ' id="%s"' % id
    html.write('<tr style="display: %s"%s><td class=legend>' % (not g_section_isopen and "none" or "", id))
    if title:
        html.write('<div class="title%s">%s<span class="dots">%s</span></div>' % 
                  (checkbox and " withcheckbox" or "", title, "."*100))
    if checkbox:
        html.write('<div class=checkbox>')
        if type(checkbox) == str:
            html.write(checkbox)
        else:
            name, inactive, attrname = checkbox
            html.checkbox(name, inactive, onclick = 'wato_toggle_attribute(this, \'%s\')' % attrname)
        html.write('</div>')

    html.write('</td>')
    html.write('<td class=content>')
    g_section_open = True

def end():
    global g_header_open
    g_header_open = False
    if g_section_open:
        html.write('</td></tr>')
    html.end_foldable_container()
    html.write('<tr class=bottom style="display: %s"><td colspan=2></td></tr>' 
            % (not g_section_isopen and "none" or ""))
    html.write('</table>')

