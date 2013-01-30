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

def render_python_raw(data, view, group_painters, painters, num_columns, show_checkboxes):
    html.write(repr(data))

multisite_layouts["python-raw"] = {
    "title"  : _("Python raw data output"),
    "render" : render_python_raw,
    "group"  : False,
    "hide"   : True,
}

def render_python(rows, view, group_painters, painters, num_columns, show_checkboxes):
    html.write("[\n")
    html.write(repr([p[0]["name"] for p in painters]))
    html.write(",\n")
    for row in rows:
        html.write("[")
        for p in painters:
            tdclass, content = p[0]["paint"](row)
            html.write(repr(htmllib.strip_tags(content)))
            html.write(",")
        html.write("],")
    html.write("\n]\n")

multisite_layouts["python"] = {
    "title"  : _("Python data output"),
    "render" : render_python,
    "group"  : False,
    "hide"   : True,
}


json_escape = re.compile(r'[\\"\r\n\t\b\f\x00-\x1f]')
json_encoding_table = dict([(chr(i), '\\u%04x' % i) for i in range(32)])
json_encoding_table.update({'\b': '\\b', '\f': '\\f', '\n': '\\n', '\r': '\\r', '\t': '\\t', '\\': '\\\\', '"': '\\"' })

def encode_string_json(s):
    return '"' + json_escape.sub(lambda m: json_encoding_table[m.group(0)], s) + '"'


def render_json(rows, view, group_painters, painters, num_columns, show_checkboxes):
    html.write("[\n")

    first = True
    html.write("[")
    for p in painters:
        if first:
            first = False
        else:
            html.write(",")
        content = p[0]["name"]
        stripped = htmllib.strip_tags(content)
        utf8 = stripped.encode("utf-8")
        html.write(encode_string_json(utf8))
    html.write("]")

    for row in rows:
        html.write(",\n[")
        first = True
        for p in painters:
            if first:
                first = False
            else:
                html.write(",")
            tdclass, content = p[0]["paint"](row)
            content = content.replace("<br>","\n")
            stripped = htmllib.strip_tags(content)
            utf8 = stripped.encode("utf-8")
            html.write(encode_string_json(utf8))
        html.write("]")

    html.write("\n]\n")


multisite_layouts["json"] = {
    "title"  : _("JSON data output"),
    "render" : render_json,
    "group"  : False,
    "hide"   : True,
}
