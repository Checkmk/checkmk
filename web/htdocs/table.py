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

table = None
mode = None
next_func = None
row_css = None

def begin(title=None, **kwargs):
    global table, mode, next_func

    if table:
        end()

    table = {
        "title": title,
        "headers" : [],
        "rows" : [],
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

def add_cell(title, text="", css=None):
    if type(text) != unicode:
        text = str(text)
    htmlcode = text + html.drain()
    if len(table["rows"]) == 1: # first row -> pick headers
        table["headers"].append(title)
    table["rows"][-1][0].append((htmlcode, css))

def end():
    global table
    finish_previous()
    html.unplug()
    if table["title"]:
        html.write("<h3>%s</h3>" % table["title"])

    if table.get("help"):
        html.help(table["help"])

    if not table["rows"]:
        html.write("<div class=info>%s</div>" % table["empty_text"])
        table = None
        return

    html.write('<table class="data')
    if "css" in table:
        html.write(" %s" % table["css"])
    html.write('">\n')
    html.write("  <tr>")
    for header in table["headers"]:
        html.write("    <th>%s</th>\n" % header)
    html.write("  </tr>\n")

    odd = "even"
    # TODO: Sorting
    for row, css in table["rows"]:
        # TODO: Filtering
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
    table = None


