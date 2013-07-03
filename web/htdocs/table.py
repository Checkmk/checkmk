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

import htmllib

table = None
mode = None
next_func = None
row_css = None

def begin(title=None, **kwargs):
    global table, mode, next_func

    try:
        import config
        limit = config.table_row_limit
    except:
        pass

    limit = kwargs.get('limit', limit)
    if html.var('limit') == 'none':
        limit = None

    table = {
        "title"         : title,
        "headers"       : [],
        "rows"          : [],
        "limit"         : limit,
        "omit_if_empty" : kwargs.get("omit_if_empty", False),
        "searchable"    : kwargs.get("searchable", True),
    }
    if kwargs.get("empty_text"):
        table["empty_text"] = kwargs["empty_text"]
    else:
        table["empty_text"] = _("No entries.")

    if kwargs.get("help"):
        table["help"] = kwargs["help"]

    if kwargs.get("css"):
        table["css"] = kwargs["css"]

    html.plug()
    mode = 'row'
    next_func = None

def finish_previous():
    global next_func
    if next_func:
        next_func(*next_args[0], **next_args[1])
        next_func = None

def row(*posargs, **kwargs):
    finish_previous()
    global next_func, next_args
    next_func = add_row
    next_args = posargs, kwargs

def add_row(css=None):
    table["rows"].append(([], css))


def cell(*posargs, **kwargs):
    finish_previous()
    global next_func, next_args
    next_func = add_cell
    next_args = posargs, kwargs

def add_cell(title, text="", css=None, help=None):
    if type(text) != unicode:
        text = str(text)
    htmlcode = text + html.drain()
    if len(table["rows"]) == 1: # first row -> pick headers
        table["headers"].append((title, help))
    table["rows"][-1][0].append((htmlcode, css))

def end():
    global table
    finish_previous()
    html.unplug()

    if not table["rows"] and table["omit_if_empty"]:
        table = None
        return

    if table["title"]:
        html.write("<h3>%s</h3>" % table["title"])

    if table.get("help"):
        html.help(table["help"])

    if not table["rows"]:
        html.write("<div class=info>%s</div>" % table["empty_text"])
        table = None
        return

    show_table_actions = table["searchable"]

    if show_table_actions:
        html.begin_form("actions")

        if table["searchable"]:
            html.write("<div class=table_search>")
            html.text_input("_search")
            html.button("_submit", _("Search"))
            html.set_focus("search")
            html.write("</div>\n")

        html.hidden_fields()
        html.end_form()

    rows = table["rows"]

    if html.var('_search'):
        search_term = html.var('_search')
        filtered_rows = []
        for row, css in rows:
            for cell_content, css_classes in row:
                if search_term in cell_content:
                    filtered_rows.append((row, css))
                    break # skip other cells when matched
        rows = filtered_rows

        if not rows:
            html.message(_('Got no row matching your search term. Please try another one.'))
            table = None
            return

    num_rows_unlimited = len(rows)

    # Apply limit after search / sorting etc.
    limit = table['limit']
    if limit is not None:
        rows = rows[:limit]

    html.write('<table class="data')
    if "css" in table:
        html.write(" %s" % table["css"])
    html.write('">\n')

    html.write("  <tr>")
    for header, help in table["headers"]:
        if help:
            header = '<span title="%s">%s</span>' % (htmllib.attrencode(help), header)
        html.write("  <th>%s</th>\n" % header)
    html.write("  </tr>\n")

    odd = "even"
    # TODO: Sorting
    for row, css in rows:
        odd = odd == "odd" and "even" or "odd"
        html.write('  <tr class="data %s0' % odd)
        if css:
            html.write(' %s' % css)
        html.write('">\n')
        for cell_content, css_classes in row:
            html.write("    <td%s>" % (css_classes and (" class='%s'" % css_classes) or ""))
            html.write(cell_content)
            html.write("</td>\n")
        html.write("</tr>\n")
    html.write("</table>\n")

    if limit is not None and num_rows_unlimited > limit:
        html.message(_('This table is limited to show only %d of %d rows. '
                       'Click <a href="%s">here</a> to disable the limitation.') %
                           (limit, num_rows_unlimited, html.makeuri([('limit', 'none')])))

    table = None


