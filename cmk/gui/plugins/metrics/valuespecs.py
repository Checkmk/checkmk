#!/usr/bin/env python
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

from __future__ import division, absolute_import, print_function
from typing import Optional  # pylint: disable=unused-import

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    CascadingDropdown,
    Checkbox,
    GraphColor,
    Dictionary,
    DropdownChoice,
    Float,
    Fontsize,
    ListChoice,
    Transform,
)

from cmk.gui.plugins.metrics import artwork


# This was moved from pnp_graph reportlet specific code
def transform_graph_render_options_title_format(p):
    if p == "add_host_name" or p == "add_host_alias":
        p = ("add_title_infos", [p])
    return p


def vs_graph_render_options(default_values=None, exclude=None):
    return Transform(
        Dictionary(
            elements=vs_graph_render_option_elements(default_values, exclude),
            optional_keys=[],
            title=_("Graph rendering options"),
        ),
        forth=_transform_graph_render_options,
    )


def _transform_graph_render_options(value):
    # Graphs in painters and dashlets had the show_service option before 1.5.0i2.
    # This has been consolidated with the option title_format from the reportlet.
    if "show_service" in value:
        show_service = value.pop("show_service")
        if show_service:
            value["title_format"] = ("add_title_infos",
                                     ["add_host_name", "add_service_description"])
        else:
            value["title_format"] = ("plain", [])
    return value


def vs_graph_render_option_elements(default_values=None, exclude=None):
    # Allow custom default values to be specified by the caller. This is, for example,
    # needed by the dashlets which should add the host/service by default.
    if default_values is None:
        default_values = artwork.get_default_graph_render_options()
    else:
        default_values = default_values.copy()
        for k, v in artwork.get_default_graph_render_options().items():
            default_values.setdefault(k, v)

    elements = [
        ("font_size", Fontsize(default_value=default_values["font_size"],)),
        ("show_title",
         DropdownChoice(
             title=_("Title"),
             choices=[
                 (False, _("Don't show graph title")),
                 (True, _("Show graph title")),
                 ("inline", _("Show graph title on graph area")),
             ],
             default_value=default_values["show_title"],
         )),
        ("title_format",
         Transform(
             CascadingDropdown(
                 title=_("Title format"),
                 orientation="vertical",
                 choices=[
                     ("plain", _("Just show graph title")),
                     ("add_title_infos", _("Add additional information"),
                      ListChoice(choices=[
                          ("add_host_name", _("Add host name")),
                          ("add_host_alias", _("Add host alias")),
                          ("add_service_description", _("Add service description")),
                      ])),
                 ],
             ),
             forth=transform_graph_render_options_title_format,
         )),
        ("show_graph_time",
         Checkbox(
             title=_("Show graph time range"),
             label=_("Show the graph time range on top of the graph"),
             default_value=default_values["show_graph_time"],
         )),
        ("show_margin",
         Checkbox(
             title=_("Show margin round the graph"),
             label=_("Show a margin round the graph"),
             default_value=default_values["show_margin"],
         )),
        ("show_legend",
         Checkbox(
             title=_("Show legend"),
             label=_("Show the graph legend"),
             default_value=default_values["show_legend"],
         )),
        ("show_vertical_axis",
         Checkbox(
             title=_("Show vertical axis"),
             label=_("Show the graph vertical axis"),
             default_value=default_values["show_vertical_axis"],
         )),
        ("vertical_axis_width",
         CascadingDropdown(
             title=_("Vertical axis width"),
             orientation="horizontal",
             choices=[
                 ("fixed", _("Use fixed width (relative to font size)")),
                 ("explicit", _("Use absolute width:"),
                  Float(title="", default_value=40.0, unit=_("pt"))),
             ],
         )),
        ("show_time_axis",
         Checkbox(
             title=_("Show time axis"),
             label=_("Show the graph time axis"),
             default_value=default_values["show_time_axis"],
         )),
        ("show_controls",
         Checkbox(
             title=_("Show controls"),
             label=_("Show the graph controls"),
             default_value=default_values["show_controls"],
         )),
        ("show_pin",
         Checkbox(
             title=_("Show pin"),
             label=_("Show the pin"),
             default_value=default_values["show_pin"],
         )),
        ("show_time_range_previews",
         Checkbox(
             title=_("Show time range previews"),
             label="Show previews",
             default_value=default_values["show_time_range_previews"],
         )),
        ("foreground_color",
         GraphColor(
             title=_("Foreground color"),
             default_value=default_values["foreground_color"],
         )),
        ("background_color",
         GraphColor(
             title=_("Background color"),
             default_value=default_values["background_color"],
         )),
        ("canvas_color",
         GraphColor(
             title=_("Canvas color"),
             default_value=default_values["canvas_color"],
         )),
    ]

    if exclude:
        elements = [x for x in elements if x[0] not in exclude]

    return elements
