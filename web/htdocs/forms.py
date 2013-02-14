#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2013             mk@mathias-kettner.de |
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


def edit_dictionary(entries, value, focus=None, hover_help=True, validate=None, buttontext = None, title = None):
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
    header(title and title or _("Properties"))
    first = True
    for name, vs in entries:
        section(vs.title())
        html.help(vs.help())
        if name in value:
            v = value[name]
        else:
            v = vs.default_value()
        vs.render_input(name, v)
        if (not focus and first) or (name == focus):
            vs.set_focus(name)
            first = False

    end()
    if buttontext == None:
        buttontext = _("Save")
    html.button("save", buttontext)
    html.hidden_fields()
    html.end_form()

# New functions for painting forms

twofivesix = "".join(map(chr, range(0,256)))
def strip_bad_chars(x):
    s = "".join([c for c in x if c > ' ' and c < 'z'])

    if type(x) == unicode:
        return s.translate({
            ord(u"'"): None,
            ord(u"&"): None,
            ord(u";"): None,
            ord(u"<"): None,
            ord(u">"): None,
            ord(u"\""): None,
        })
    else:
        return s.translate(twofivesix, "'&;<>\"")

def header(title, isopen = True, table_id = "", narrow = False):
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
    html.write('<table %s class="nform%s">' % (table_id, narrow and " narrow" or ""))
    fold_id = strip_bad_chars(title)
    g_section_isopen = html.begin_foldable_container(
            html.form_name and html.form_name or "nform", fold_id, isopen, title, indent="nform")
    html.write('<tr class="top %s"><td colspan=2></td></tr>' % (g_section_isopen and "open" or "closed"))
    g_header_open = True
    g_section_open = False

# container without legend and content
def container():
    global g_section_open
    if g_section_open:
        html.write('</td></tr>')
    html.write('<tr class="%s"><td colspan=2 class=container>' %
         (g_section_isopen and "open" or "closed"))
    g_section_open = True

def section(title = None, checkbox = None, id = "", simple=False, hide = False):
    global g_section_open
    if g_section_open:
        html.write('</td></tr>')
    if id:
        id = ' id="%s"' % id
    html.write('<tr class="%s"%s%s><td class="legend%s">' %
            (g_section_isopen and "open" or "closed", id,
             hide and ' style="display:none;"' or '',
             simple and " simple" or ""))
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
    html.write('<td class="content%s">' % (simple and " simple" or ""))
    g_section_open = True

def end():
    global g_header_open
    g_header_open = False
    if g_section_open:
        html.write('</td></tr>')
    html.end_foldable_container()
    html.write('<tr class="bottom %s"><td colspan=2></td></tr>'
            % (g_section_isopen and "open" or "closed"))
    html.write('</table>')

