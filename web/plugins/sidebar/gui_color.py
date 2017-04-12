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

gui_colors = {
    1 : ( 73, 138, 166), 
    2 : ( 73, 166, 157), 
    3 : ( 84, 166,  73), 
    4 : (166, 166,  73), 
    5 : (166, 115,  73), 
    6 : (209,  92,  92),
    7 : (201,  96, 219),
    8 : (140, 142, 207),
    9 : (160, 160, 160), 
}


def render_gui_color():
    html.open_div(class_="gui_color")
    for name, rgb_int in gui_colors.items():
        html.div("",
            class_  = "pick_gui_color",
            style   = "background-color: rgb(%d,%d,%d);" % rgb_int,
            onclick = "set_gui_color(%d,%d,%d);" % rgb_int,
        )
    html.close_div()


def ajax_set_gui_color():
    html.log(html.all_vars())
    r = int(html.var("r"))
    g = int(html.var("g"))
    b = int(html.var("b"))
    config.user.save_file("gui_color", (r, g, b))


sidebar_snapins["gui_color"] = {
    "title" : _("GUI Color"),
    "description" : _("Choose your favourite color of the user interface"),
    "render" : render_gui_color,
    "allowed" : [ "admin", "user", ],
    "styles" : """

div.gui_color {
    text-align: center;
    width: 100%;
}

div.pick_gui_color {
    width: 18.2px;
    height: 18.5px;
    float: none;
    display: inline-block;
    margin-right: 5px;
    border: 1px solid black;
    box-shadow: 0.5px 0.5px 1px rgba(0, 0, 0, 0.5);
}

div.pick_gui_color:hover {
    transform: scale(1.1);
    cursor: pointer;
    box-shadow: 1.5px 1.5px 3px rgba(0, 0, 0, 0.5);
}
"""
}


