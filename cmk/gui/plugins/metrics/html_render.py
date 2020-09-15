#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import copy
import time
import json
import traceback
from typing import NamedTuple, Optional, Tuple, List, Union

import livestatus

import cmk.utils.render

from cmk.gui import sites, escaping
from cmk.gui.htmllib import HTML
from cmk.gui.globals import html
import cmk.gui.config as config
from cmk.gui.exceptions import MKGeneralException

from cmk.gui.i18n import _

from cmk.gui.log import logger

from cmk.gui.plugins.metrics.utils import render_color_icon

from cmk.gui.plugins.metrics import artwork
from cmk.gui.plugins.metrics.identification import graph_identification_types

from cmk.gui.utils.popups import MethodAjax

RenderOutput = Union[HTML, str]

#   .--HTML-Graphs---------------------------------------------------------.
#   |                      _   _ _____ __  __ _                            |
#   |                     | | | |_   _|  \/  | |                           |
#   |                     | |_| | | | | |\/| | |                           |
#   |                     |  _  | | | | |  | | |___                        |
#   |                     |_| |_| |_| |_|  |_|_____|                       |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Code for rendering a graph in HTML.                                 |
#   '----------------------------------------------------------------------'

# Code paths for rendering graphs in HTML:

# View -> Painter
# View -> Icons -> Hover
# Dashboard -> Embedded Graph
# Javascript Interactive Graph
# Graph Collection
# Graph Overview
# Custom graph

# TODO: This is not acurate! Rendering of the graphs is wrong especially when the font size is changed
# this does not lead to correct results. We should find a way to fix this. Otherwise the font size
# chaning of the graph rendering options won't work as expected.
html_size_per_ex = 11.0
min_resize_width = 50
min_resize_height = 6


def host_service_graph_popup_cmk(site, host_name, service_description):
    graph_render_options = {
        "size": (30, 10),
        "font_size": 6.0,  # pt
        "resizable": False,
        "show_controls": False,
        "show_legend": False,
        "interaction": False,
        "show_time_range_previews": False,
    }

    end_time = time.time()
    start_time = end_time - 8 * 3600
    graph_data_range = {
        "time_range": (start_time, end_time),
    }

    graph_identification = ("template", {
        "site": site,
        "host_name": host_name,
        "service_description": service_description,
    })

    html.write(
        render_graphs_from_specification_html(graph_identification,
                                              graph_data_range,
                                              graph_render_options,
                                              render_async=False))


def render_graph_or_error_html(graph_artwork, graph_data_range, graph_render_options):
    try:
        return render_graph_html(graph_artwork, graph_data_range, graph_render_options)
    except Exception as e:
        return render_graph_error_html(e)


def render_graph_error_html(msg_or_exc, title=None):
    if isinstance(msg_or_exc, MKGeneralException) and not config.debug:
        msg = "%s" % msg_or_exc

    elif isinstance(msg_or_exc, Exception):
        if config.debug:
            raise msg_or_exc
        msg = traceback.format_exc()
    else:
        msg = msg_or_exc

    if title is None:
        title = _("Cannot display graph")

    return html.render_div(html.render_div(title, class_="title") + html.render_pre(msg),
                           class_=["graph", "brokengraph"])


# Render the complete HTML code of a graph - including its <div> container.
# Later updates will just replace the content of that container.
def render_graph_html(graph_artwork, graph_data_range, graph_render_options):
    graph_render_options = artwork.add_default_render_options(graph_render_options)

    html_code = render_graph_html_content(graph_artwork, graph_data_range, graph_render_options)

    return html.render_javascript(
        'cmk.graphs.create_graph(%s, %s, %s, %s);' %
        (json.dumps("%s" % html_code), json.dumps(graph_artwork), json.dumps(graph_render_options),
         json.dumps(graph_ajax_context(graph_artwork, graph_data_range, graph_render_options))))


# The ajax context will be passed back to us to the page handler ajax_graph() whenever
# an update of the graph should be done. It must contain everything that we need to
# create the HTML code of the graph. The entry "graph_id" will be set by the javascript
# code since it is not known to us.
def graph_ajax_context(graph_artwork, graph_data_range, graph_render_options):
    return {
        "definition": graph_artwork["definition"],
        "data_range": graph_data_range,
        "render_options": graph_render_options,
    }


def render_plain_graph_title(graph_artwork, graph_render_options):
    return " / ".join(
        txt for txt, _url in _render_graph_title_elements(graph_artwork, graph_render_options))


def _render_graph_title_elements(graph_artwork, graph_render_options):
    if not graph_render_options["show_title"]:
        return []

    # Hard override of the graph title. This is e.g. needed for the graph previews
    if "title" in graph_render_options:
        return [(graph_render_options["title"], None)]

    title_elements: List[Tuple[str, Optional[str]]] = [(graph_artwork["title"], None)]

    if isinstance(graph_render_options["title_format"], (tuple, list)):
        title_format, title_format_params = graph_render_options["title_format"]
    else:
        title_format, title_format_params = graph_render_options["title_format"], []

    if title_format == "plain":
        return title_elements

    # Only add host/service information for template based graphs
    ident_type, spec_info = graph_artwork["definition"]["specification"]
    if ident_type != "template":
        return title_elements

    if title_format != "add_title_infos":
        raise NotImplementedError()

    if "add_host_name" in title_format_params:
        host_name = spec_info["host_name"]
        host_url = html.makeuri_contextless([("view_name", "hoststatus"),
                                             ("host", spec_info["host_name"])],
                                            filename="view.py")
        title_elements.append((host_name, host_url))

    if "add_host_alias" in title_format_params:
        host_alias = _get_alias_of_host(spec_info["site"], spec_info["host_name"])
        host_url = html.makeuri_contextless([("view_name", "hoststatus"),
                                             ("host", spec_info["host_name"])],
                                            filename="view.py")
        title_elements.append((host_alias, host_url))

    if "add_service_description" in title_format_params:
        service_description = spec_info["service_description"]
        if service_description != "_HOST_":
            service_url = html.makeuri_contextless([("view_name", "service"),
                                                    ("host", spec_info["host_name"]),
                                                    ("service", service_description)],
                                                   filename="view.py")
            title_elements.append((service_description, service_url))

    return title_elements


def _get_alias_of_host(site, host_name):
    query = ("GET hosts\n"
             "Cache: reload\n"
             "Columns: alias\n"
             "Filter: name = %s" % livestatus.lqencode(host_name))

    with sites.only_sites(site):
        try:
            return sites.live().query_value(query)
        except Exception as e:
            logger.warning("Could not determine alias of host %s on site %s: %s", host_name, site,
                           e)
            if config.debug:
                raise
            return host_name


def render_html_graph_title(graph_artwork, graph_render_options):
    title = HTML(" / ").join([
        (html.render_a(txt, href=url) if url else txt)
        for txt, url in _render_graph_title_elements(graph_artwork, graph_render_options)
    ])
    if title:
        return html.render_div(
            title,
            class_=["title", "inline" if graph_render_options["show_title"] == "inline" else None])
    return ""


def show_graph_legend(graph_render_options, graph_artwork):
    return graph_render_options["show_legend"] and graph_artwork["curves"]


# Render the HTML code of a graph without its container. That is a canvas object
# for drawing the actual graph and also legend, buttons, resize handle, etc.
def render_graph_html_content(graph_artwork, graph_data_range, graph_render_options):
    graph_render_options = artwork.add_default_render_options(graph_render_options)

    css = " preview" if graph_render_options["preview"] else ""
    output: RenderOutput = '<div class="graph%s" style="font-size: %.1fpt;%s">' % (
        css, graph_render_options["font_size"], _graph_padding_styles(graph_render_options))

    if graph_render_options["show_controls"]:
        output += render_graph_add_to_icon_for_popup(graph_artwork, graph_data_range,
                                                     graph_render_options)

    v_axis_label = graph_artwork["vertical_axis"]["axis_label"]
    if v_axis_label:
        output += '<div class=v_axis_label>%s</div>' % v_axis_label

    # Add the floating elements
    if graph_render_options["show_graph_time"] and not graph_render_options["preview"]:
        output += html.render_div(
            graph_artwork["time_axis"]["title"] or "",
            css=["time", "inline" if graph_render_options["show_title"] == "inline" else None])

    if graph_render_options["show_controls"] and graph_render_options["resizable"]:
        output += '<img class=resize src="%s">' % html.theme_url("images/resize_graph.png")

    output += render_html_graph_title(graph_artwork, graph_render_options)
    output += render_graph_canvas(graph_render_options)

    # Note: due to "omit_zero_metrics" the graph might not have any curves
    if show_graph_legend(graph_render_options, graph_artwork):
        output += render_graph_legend(graph_artwork, graph_render_options)

    model_params_repr = graph_artwork["definition"].get("model_params_repr")
    model_params_display = graph_artwork["definition"].get('model_params',
                                                           {}).get("display_model_parametrization")
    if model_params_repr and model_params_display:
        output += "<div align='center'><h2>Forecast Parametrization</h2>%s</div>" % model_params_repr

    output += '</div>'
    return output


def render_graph_add_to_icon_for_popup(graph_artwork, graph_data_range, graph_render_options):
    icon_html = html.render_icon('menu', _('Add this graph to...'))
    element_type_name = "pnpgraph"

    # Data will be transferred via URL and Javascript magic eventually
    # to our function popup_add_element (htdocs/reporting.py)
    # argument report_name --> provided by popup system
    # further arguments:
    return html.render_popup_trigger(
        content=icon_html,
        ident='add_visual',
        method=MethodAjax(endpoint='add_visual', url_vars=[("add_type", "pnpgraph")]),
        data=[
            element_type_name, None,
            graph_ajax_context(graph_artwork, graph_data_range, graph_render_options)
        ],
        style="z-index:2")  # Ensures that graph canvas does not cover it


def render_graph_canvas(graph_render_options):
    # Create canvas where actual graph will be rendered
    size = graph_render_options["size"]
    graph_width = size[0] * html_size_per_ex
    graph_height = size[1] * html_size_per_ex
    return '<canvas style="position: relative; width: %dpx; height: %dpx;"' \
           ' width=%d height=%d></canvas>' % (graph_width, graph_height, graph_width*2, graph_height*2)


def show_pin_time(graph_artwork, graph_render_options):
    if not graph_render_options["show_pin"]:
        return False

    timestamp = graph_artwork["pin_time"]
    return timestamp is not None and graph_artwork["start_time"] <= timestamp <= graph_artwork[
        "end_time"]


def render_pin_time_label(graph_artwork):
    timestamp = graph_artwork["pin_time"]
    return cmk.utils.render.date_and_time(timestamp)[:-3]


def get_scalars(graph_artwork, graph_render_options):
    scalars = []
    for scalar, title in [
        ("min", _("Minimum")),
        ("max", _("Maximum")),
        ("average", _("Average")),
    ]:

        consolidation_function = graph_artwork["definition"]["consolidation_function"]
        inactive = consolidation_function is not None and consolidation_function != scalar

        scalars.append((scalar, title, inactive))

    scalars.append(("last", _("Last"), False))

    if show_pin_time(graph_artwork, graph_render_options):
        scalars.append(("pin", render_pin_time_label(graph_artwork), False))

    return scalars


def graph_curves(graph_artwork):
    curves = []
    for curve in graph_artwork["curves"][::-1]:
        if not curve.get("dont_paint"):
            curves.append(curve)
    return curves


# Render legend that describe the metrics
def render_graph_legend(graph_artwork, graph_render_options):
    graph_width = graph_render_options["size"][0] * html_size_per_ex
    font_size_style = "font-size: %dpt;" % graph_render_options["font_size"]

    scalars = get_scalars(graph_artwork, graph_render_options)

    if graph_render_options["show_vertical_axis"] or graph_render_options["show_controls"]:
        legend_margin_left = 49
    else:
        legend_margin_left = 0

    style = []
    legend_width = graph_width - legend_margin_left

    # In case there is no margin show: Add some to the legend since it looks
    # ugly when there is no space between the outer graph border and the legend
    if not graph_render_options["show_margin"]:
        legend_width -= 5 * 2
        style.append("margin: 8px 5px 5px 5px")

    style.append("width:%dpx" % legend_width)

    if legend_margin_left:
        style.append("margin-left:%dpx" % legend_margin_left)

    output: RenderOutput = '<table class=legend style="%s">' % ";".join(style)

    # Render the title row
    output += '<tr><th></th>'
    for scalar, title, inactive in scalars:
        classes = ["scalar", scalar]
        if inactive and graph_artwork["step"] != 60:
            descr = _("This graph is based on data consolidated with the function \"%s\". The "
                      "values in this column are the \"%s\" values of the \"%s\" values "
                      "aggregated in %s steps. Assuming a check interval of 1 minute, the %s "
                      "values here are based on the %s value out of %d raw values.") % (
                          graph_artwork["definition"]["consolidation_function"],
                          scalar,
                          graph_artwork["definition"]["consolidation_function"],
                          artwork.get_step_label(graph_artwork["step"]),
                          scalar,
                          graph_artwork["definition"]["consolidation_function"],
                          (graph_artwork["step"] / 60),
                      )

            descr += "\n\n" + _("Click here to change the graphs "
                                "consolidation function to \"%s\".") % scalar

            classes.append("inactive")
        else:
            descr = ""

        output += '<th class="%s" style="%s" title=\"%s\">%s</th>' % \
                        (" ".join(classes), font_size_style, escaping.escape_attribute(descr), title)
    output += '</tr>'

    # Render the curve related rows
    for curve in graph_curves(graph_artwork):
        output += '<tr>'
        output += '<td style="%s">%s ' % (font_size_style, render_color_icon(curve["color"]))
        output += '%s</td>' % curve["title"]

        for scalar, title, inactive in scalars:
            if scalar == "pin" and not show_pin_time(graph_artwork, graph_render_options):
                continue

            if inactive and graph_artwork["step"] != 60:
                inactive_cls = " inactive"
            else:
                inactive_cls = ""

            output += '<td class="scalar%s" style="%s">%s</td>' % \
                        (inactive_cls, font_size_style, curve["scalars"][scalar][1])

        output += '</tr>'

    # Render scalar values
    if graph_artwork["horizontal_rules"]:
        first = True
        for _value, readable, color, title in graph_artwork["horizontal_rules"]:
            output += '<tr class="scalar%s">' % (first and " first" or "")
            output += '<td style="%s">' % font_size_style
            output += render_color_icon(color)
            output += '%s</td>' % title
            # A colspan of 5 has to be used here, since the pin that is added by a click into
            # the graph introduces a new column.
            output += '<td colspan=5 class=scalar style="%s">%s</td>' % (font_size_style, readable)
            output += '</tr>'
            first = False

    output += '</table>'
    return output


Bounds = NamedTuple("Bounds", [("top", float), ("right", float), ("bottom", float),
                               ("left", float)])


def _graph_padding_styles(graph_render_options):
    return "padding: %0.2fex %0.2fex %0.2fex %0.2fex;" % _graph_margin_ex(graph_render_options)


def _graph_margin_ex(graph_render_options, defaults=(8, 16, 4, 8)):
    """Return 4-Tuple for top, right, bottom, left spacing"""
    if graph_render_options["preview"]:
        return Bounds(0, 0, 0, 0)
    if graph_render_options["show_margin"]:
        return Bounds(*(x / html_size_per_ex for x in defaults))
    return Bounds(0, 0, 0, 0)


@cmk.gui.pages.register("ajax_graph")
def ajax_graph():
    html.set_output_format("json")
    try:
        context_var = html.request.get_str_input_mandatory("context")
        context = json.loads(context_var)
        response_data = render_ajax_graph(context)
        html.write(json.dumps(response_data))
    except Exception as e:
        logger.error("Ajax call ajax_graph.py failed: %s\n%s", e, traceback.format_exc())
        if config.debug:
            raise
        html.write("ERROR: %s" % e)


def render_ajax_graph(context):
    graph_data_range = context["data_range"]
    graph_render_options = context["render_options"]
    graph_recipe = context["definition"]

    start_time_var = html.request.var("start_time")
    end_time_var = html.request.var("end_time")
    step_var = html.request.var("step")
    if start_time_var is not None and end_time_var is not None and step_var is not None:
        start_time = float(start_time_var)
        end_time = float(end_time_var)
        step = float(step_var)
    else:
        start_time, end_time = graph_data_range["time_range"]
        step = graph_data_range["step"]

    size = graph_render_options["size"]

    resize_x_var = html.request.var("resize_x")
    resize_y_var = html.request.var("resize_y")

    if resize_x_var is not None and resize_y_var is not None:
        render_opt_x, render_opt_y = context["render_options"]["size"]
        size_x = max(min_resize_width, float(resize_x_var) / html_size_per_ex + render_opt_x)
        size_y = max(min_resize_height, float(resize_y_var) / html_size_per_ex + render_opt_y)
        config.user.save_file("graph_size", (size_x, size_y))
        size = (size_x, size_y)

    range_from_var = html.request.var("range_from")
    range_to_var = html.request.var("range_to")
    if range_from_var is not None and range_to_var is not None:
        vertical_range: Optional[Tuple[float, float]] = (float(range_from_var), float(range_to_var))
    else:
        vertical_range = None

    if html.request.has_var("pin"):
        artwork.save_graph_pin()

    if html.request.has_var("consolidation_function"):
        graph_recipe["consolidation_function"] = html.request.var("consolidation_function")

    graph_render_options["size"] = size
    graph_data_range["time_range"] = (start_time, end_time)
    graph_data_range["vertical_range"] = vertical_range
    graph_data_range["step"] = step

    # Persist the current data range for the graph editor
    if graph_render_options["editing"]:
        save_user_graph_data_range(graph_data_range)

    graph_artwork = artwork.compute_graph_artwork(graph_recipe, graph_data_range,
                                                  graph_render_options)
    html_code = render_graph_html_content(graph_artwork, graph_data_range, graph_render_options)

    return {
        "html": html_code,
        "graph": graph_artwork,
        "context": {
            "graph_id": context["graph_id"],
            "definition": graph_recipe,
            "data_range": graph_data_range,
            "render_options": graph_render_options,
        }
    }


def load_user_graph_data_range():
    return config.user.load_file("graph_range", {
        "time_range": (time.time() - 86400, time.time()),
    })


def save_user_graph_data_range(graph_data_range):
    config.user.save_file("graph_range", graph_data_range)


def forget_manual_vertical_zoom():
    user_range = load_user_graph_data_range()
    if "vertical_range" in user_range:
        del user_range["vertical_range"]
        save_user_graph_data_range(user_range)


def render_graphs_from_specification_html(graph_identification,
                                          graph_data_range,
                                          graph_render_options,
                                          render_async=True):
    try:
        graph_recipes = graph_identification_types.create_graph_recipes(graph_identification)
    except livestatus.MKLivestatusNotFoundError:
        return render_graph_error_html(
            "%s\n\n%s: %r" % (_("Cannot fetch data via Livestatus"),
                              _("The graph specification is"), graph_identification),
            _("Cannot calculate graph recipes"))
    except Exception as e:
        return render_graph_error_html(e, _("Cannot calculate graph recipes"))

    return render_graphs_from_definitions(graph_recipes, graph_data_range, graph_render_options,
                                          render_async)


def render_graphs_from_definitions(graph_recipes,
                                   graph_data_range,
                                   graph_render_options,
                                   render_async=True):
    # Estimate step. Step is the number of seconds each fetched data point represents.
    # It does not make sense to fetch the data in *much* greater precision than our
    # display has. A *bit* more precision is useful for better optical zoom.
    graph_data_range.setdefault(
        "step", estimate_graph_step_for_html(graph_data_range["time_range"], graph_render_options))

    output: RenderOutput = ""
    for graph_recipe in graph_recipes:
        if render_async:
            output += render_graph_container_html(graph_recipe, graph_data_range,
                                                  graph_render_options)
        else:
            output += render_graph_content_html(graph_recipe, graph_data_range,
                                                graph_render_options)
    return output


# cmk.graphs.load_graph_content will call ajax_render_graph_content() via JSON to finally load the graph
def render_graph_container_html(graph_recipe, graph_data_range, graph_render_options):
    graph_render_options = artwork.add_default_render_options(graph_render_options)

    # Estimate size of graph. This will not be the exact size of the graph, because
    # this does calculate the size of the canvas area and does not take e.g. the legend
    # into account. We would need the graph_artwork to calculate that, but this is something
    # we don't have in this early stage.
    size = graph_render_options["size"]
    graph_width = size[0] * html_size_per_ex
    graph_height = size[1] * html_size_per_ex

    content = html.render_div("", class_="title") \
            + html.render_div("",
                class_="content",
                style="width:%dpx;height:%dpx" % (graph_width, graph_height))

    output = html.render_div(html.render_div(content, class_=["graph", "loading_graph"]),
                             class_="graph_load_container") \

    output += html.render_javascript("cmk.graphs.load_graph_content(%s, %s, %s)" % (
        json.dumps(graph_recipe),
        json.dumps(graph_data_range),
        json.dumps(graph_render_options),
    ))

    if "cmk.graphs.register_delayed_graph_listener" not in html.final_javascript_code:
        html.final_javascript("cmk.graphs.register_delayed_graph_listener()")

    return output


# Called from javascript code via JSON to initially render a graph
@cmk.gui.pages.register("ajax_render_graph_content")
def ajax_render_graph_content():
    html.set_output_format("json")
    try:
        request = html.get_request()
        response = {
            "result_code": 0,
            "result": render_graph_content_html(request["graph_recipe"],
                                                request["graph_data_range"],
                                                request["graph_render_options"]),
        }
    except Exception:
        logger.exception("could not render graph")
        response = {
            "result_code": 1,
            "result": _("Unhandled exception: %s") % traceback.format_exc(),
        }

    html.write(json.dumps(response))


def render_graph_content_html(graph_recipe, graph_data_range, graph_render_options):
    output = ""
    try:
        graph_artwork = artwork.compute_graph_artwork(graph_recipe, graph_data_range,
                                                      graph_render_options)
        main_graph_html = render_graph_or_error_html(graph_artwork, graph_data_range,
                                                     graph_render_options)

        previews = graph_render_options["show_time_range_previews"]
        if graph_recipe['specification'][0] == 'forecast':
            previews = False

        if previews:
            output += "<div class=\"graph_with_timeranges\">"
            output += main_graph_html
            output += render_time_range_selection(graph_recipe, graph_render_options)
            output += "</div>"
        else:
            output += main_graph_html

    except livestatus.MKLivestatusNotFoundError:
        output += render_graph_error_html(_("Cannot fetch data via Livestatus"),
                                          _("Cannot create graph"))

    except Exception as e:
        output += render_graph_error_html(e, _("Cannot create graph"))
    return output


def render_time_range_selection(graph_recipe, graph_render_options):
    now = int(time.time())
    output: RenderOutput = "<table class=timeranges>"
    graph_render_options = copy.deepcopy(graph_render_options)
    for timerange_attrs in config.graph_timeranges:
        duration = timerange_attrs["duration"]
        assert isinstance(duration, int)
        graph_render_options.update({
            "size": (20, 4),
            "font_size": 6.0,  # pt
            "onclick": "cmk.graphs.change_graph_timerange(graph, %d)" % duration,
            "fixed_timerange": True,  # Do not follow timerange changes of other graphs
            "title": timerange_attrs["title"],
            "show_legend": False,
            "show_controls": False,
            "preview": True,
            "resizable": False,
            "interaction": False,
        })

        timerange = now - duration, now
        graph_data_range = {
            "time_range": timerange,
            "step": 2 * estimate_graph_step_for_html(timerange, graph_render_options),
        }

        output += "<td title=\"%s\">\n" % (_("Change graph timerange to: %s") %
                                           timerange_attrs["title"])
        graph_artwork = artwork.compute_graph_artwork(graph_recipe, graph_data_range,
                                                      graph_render_options)
        output += render_graph_html(graph_artwork, graph_data_range, graph_render_options)
        output += "\n</td>"
        output += "</tr><tr>"
    output += "</table>"
    return output


def estimate_graph_step_for_html(time_range, graph_render_options):
    graph_render_options = artwork.add_default_render_options(graph_render_options)
    width_in_ex = graph_render_options["size"][1]
    steps_per_ex = html_size_per_ex * 4
    number_of_steps = width_in_ex * steps_per_ex
    return int((time_range[1] - time_range[0]) / number_of_steps)


#.
#   .--Graph hover---------------------------------------------------------.
#   |        ____                 _       _                                |
#   |       / ___|_ __ __ _ _ __ | |__   | |__   _____   _____ _ __        |
#   |      | |  _| '__/ _` | '_ \| '_ \  | '_ \ / _ \ \ / / _ \ '__|       |
#   |      | |_| | | | (_| | |_) | | | | | | | | (_) \ V /  __/ |          |
#   |       \____|_|  \__,_| .__/|_| |_| |_| |_|\___/ \_/ \___|_|          |
#   |                      |_|                                             |
#   +----------------------------------------------------------------------+
#   | Processing of the graph hover which shows the current values at the  |
#   | position of the mouse                                                |
#   '----------------------------------------------------------------------'


@cmk.gui.pages.register("ajax_graph_hover")
def ajax_graph_hover():
    html.set_output_format("json")
    try:
        context_var = html.request.get_str_input_mandatory("context")
        context = json.loads(context_var)
        hover_time = html.request.get_integer_input_mandatory("hover_time")
        response_data = render_ajax_graph_hover(context, hover_time)
        html.write(json.dumps(response_data))
    except Exception as e:
        logger.error("Ajax call ajax_graph_hover.py failed: %s\n%s", e, traceback.format_exc())
        if config.debug:
            raise
        html.write("ERROR: %s" % e)


def render_ajax_graph_hover(context, hover_time):
    graph_data_range = context["data_range"]
    graph_recipe = context["definition"]

    curves = artwork.compute_graph_artwork_curves(graph_recipe, graph_data_range)

    curve_values = artwork._compute_curve_values_at_timestamp(graph_recipe, curves, hover_time)

    return {
        "rendered_hover_time": cmk.utils.render.date_and_time(hover_time),
        "curve_values": curve_values,
    }


# Estimates the height of the graph legend in pixels
# TODO: This is not acurate! Especially when the font size is changed this does not lead to correct
# results. But this is a more generic problem of the html_size_per_ex which is hard coded instead
# of relying on the font as it should.
def graph_legend_height_ex(graph_render_options, graph_artwork):
    if not show_graph_legend(graph_render_options, graph_artwork):
        return 0.0
    # Add header line + spacing: '3.0'
    return 3.0 + (len(graph_curves(graph_artwork)) + len(graph_artwork["horizontal_rules"])) * 1.3


#.
#   .--Graph Dashlet-------------------------------------------------------.
#   |    ____                 _       ____            _     _      _       |
#   |   / ___|_ __ __ _ _ __ | |__   |  _ \  __ _ ___| |__ | | ___| |_     |
#   |  | |  _| '__/ _` | '_ \| '_ \  | | | |/ _` / __| '_ \| |/ _ \ __|    |
#   |  | |_| | | | (_| | |_) | | | | | |_| | (_| \__ \ | | | |  __/ |_     |
#   |   \____|_|  \__,_| .__/|_| |_| |____/ \__,_|___/_| |_|_|\___|\__|    |
#   |                  |_|                                                 |
#   +----------------------------------------------------------------------+
#   |  This page handler is called by graphs embedded in a dashboard.      |
#   '----------------------------------------------------------------------'


class GraphDestinations:
    dashlet = "dashlet"
    view = "view"
    report = "report"
    notification = "notification"

    @classmethod
    def choices(cls):
        return [
            (GraphDestinations.dashlet, _("Dashlet")),
            (GraphDestinations.view, _("View")),
            (GraphDestinations.report, _("Report")),
            (GraphDestinations.notification, _("Notification")),
        ]


def _graph_title_height_ex(graph_render_options):
    if graph_render_options["show_title"] in [False, "inline"]:
        return 0
    return 1  # ex


default_dashlet_graph_render_options = {
    "font_size": 8,
    "show_legend": False,
    "title_format": ("add_title_infos", ["add_host_name", "add_service_description"]),
    "show_controls": False,
    "resizable": False,
    "show_time_range_previews": False,
}


def host_service_graph_dashlet_cmk(graph_identification, custom_graph_render_options):
    graph_render_options = default_dashlet_graph_render_options.copy()
    graph_render_options = artwork.add_default_render_options(graph_render_options)
    graph_render_options.update(custom_graph_render_options)

    width_var = html.request.get_float_input_mandatory("width", 0.0)
    width = int((width_var / html_size_per_ex))

    height_var = html.request.get_float_input_mandatory("height", 0.0)
    height = int((height_var / html_size_per_ex))

    bounds = _graph_margin_ex(graph_render_options)
    height -= _graph_title_height_ex(graph_render_options)
    height -= bounds.top + bounds.bottom
    width -= bounds.left + bounds.right

    graph_render_options["size"] = (width, height)

    # The timerange is specified in PNP like manner.
    range_secs = {
        "0": 4 * 3600,
        "1": 25 * 3600,
        "2": 7 * 86400,
        "3": 31 * 86400,
        "4": 366 * 86400,
    }

    secs_var = html.request.var("timerange")
    if secs_var not in range_secs:
        secs = 4 * 3600
    else:
        secs = range_secs[secs_var]
    end_time = time.time()
    start_time = end_time - secs
    graph_data_range = {
        "time_range": (start_time, end_time),
    }

    graph_data_range["step"] = estimate_graph_step_for_html(graph_data_range["time_range"],
                                                            graph_render_options)

    try:
        graph_recipes = graph_identification_types.create_graph_recipes(
            graph_identification, destination=GraphDestinations.dashlet)
        if graph_recipes:
            graph_recipe = graph_recipes[0]
        else:
            raise MKGeneralException(_("Failed to calculate a graph recipe."))
    except livestatus.MKLivestatusNotFoundError:
        html.div(_("Cannot render graphs: cannot fetch data via Livestatus"), class_="error")
        return

    # When the legend is enabled, we need to reduce the height by the height of the legend to
    # make the graph fit into the dashlet area.
    if graph_render_options["show_legend"]:
        # TODO FIXME: This graph artwork is calulated twice. Once here and once in render_graphs_from_specification_html()
        graph_artwork = artwork.compute_graph_artwork(graph_recipe, graph_data_range,
                                                      graph_render_options)
        if graph_artwork["curves"]:
            legend_width, legend_height = graph_legend_height_ex(graph_render_options,
                                                                 graph_artwork)
            graph_render_options["size"] = (width - legend_width, height - legend_height)

    html_code = render_graphs_from_definitions([graph_recipe],
                                               graph_data_range,
                                               graph_render_options,
                                               render_async=False)
    html.write(html_code)
