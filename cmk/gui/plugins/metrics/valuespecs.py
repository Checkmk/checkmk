#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import List

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


def transform_graph_render_options_title_format(p) -> List[str]:
    # ->1.5.0i2 pnp_graph reportlet
    if p in ('add_host_name', 'add_host_alias'):
        p = ("add_title_infos", [p])
    #   1.5.0i2->2.0.0i1 title format DropdownChoice to ListChoice
    if p == "plain":
        return ["plain"]
    if isinstance(p, tuple):
        if p[0] == "add_title_infos":
            return ["plain"] + p[1]
        if p[0] == "plain":
            return ["plain"]
    return p


def transform_graph_render_options(value):
    # Graphs in painters and dashlets had the show_service option before 1.5.0i2.
    # This has been consolidated with the option title_format from the reportlet.
    if value.pop("show_service", False):
        value["title_format"] = ["plain", "add_host_name", "add_service_description"]
    #   1.5.0i2->2.0.0i1 title format DropdownChoice to ListChoice
    if isinstance(value.get("title_format"), (str, tuple)):
        value["title_format"] = transform_graph_render_options_title_format(value["title_format"])
    return value


def vs_graph_render_options(default_values=None, exclude=None):
    return Transform(
        Dictionary(
            elements=vs_graph_render_option_elements(default_values, exclude),
            optional_keys=[],
            title=_("Graph rendering options"),
        ),
        forth=transform_graph_render_options,
    )


def vs_title_infos(with_metric: bool = False):
    choices = [
        ("plain", _("Graph title")),
        ("add_host_name", _("Host name")),
        ("add_host_alias", _("Host alias")),
        ("add_service_description", _("Service description")),
    ]
    if with_metric:
        choices.append(("add_metric_name", _("Add metric name")))
    return ListChoice(title=_("Title format"), choices=choices, default_value=["plain"])


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
             vs_title_infos(),
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
