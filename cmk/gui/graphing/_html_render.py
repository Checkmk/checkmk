#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import copy
import json
import time
import traceback
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from livestatus import MKLivestatusNotFoundError, SiteId

import cmk.utils.render
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.hostaddress import HostName
from cmk.utils.paths import profile_dir
from cmk.utils.servicename import ServiceName

from cmk.gui.config import active_config
from cmk.gui.exceptions import MKMissingDataError
from cmk.gui.graphing._graph_templates import TemplateGraphSpecification
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.htmllib.html import html
from cmk.gui.http import request, response
from cmk.gui.i18n import _, _u
from cmk.gui.log import logger
from cmk.gui.logged_in import LoggedInUser, user
from cmk.gui.pages import AjaxPage, PageResult
from cmk.gui.sites import get_alias_of_host
from cmk.gui.type_defs import SizePT
from cmk.gui.utils.html import HTML
from cmk.gui.utils.output_funnel import output_funnel
from cmk.gui.utils.popups import MethodAjax
from cmk.gui.utils.rendering import text_with_links_to_user_translated_html
from cmk.gui.utils.theme import theme
from cmk.gui.utils.urls import makeuri_contextless
from cmk.gui.valuespec import Timerange, TimerangeValue

from ._artwork import (
    compute_curve_values_at_timestamp,
    compute_graph_artwork,
    compute_graph_artwork_curves,
    get_step_label,
    GraphArtwork,
    order_graph_curves_for_legend_and_mouse_hover,
    save_graph_pin,
)
from ._color import render_color_icon
from ._graph_render_config import GraphRenderConfig, GraphRenderConfigBase, GraphTitleFormat
from ._graph_specification import GraphDataRange, GraphRecipe, GraphSpecification
from ._utils import SizeEx

RenderOutput = HTML | str

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


def host_service_graph_popup_cmk(
    site: SiteId | None,
    host_name: HostName,
    service_description: ServiceName,
) -> None:
    graph_render_config = GraphRenderConfig.from_user_context_and_options(
        user,
        theme.get(),
        size=(30, 10),
        font_size=SizePT(6.0),
        resizable=False,
        show_controls=False,
        show_legend=False,
        interaction=False,
        show_time_range_previews=False,
    )

    graph_data_range = make_graph_data_range(
        ((end_time := int(time.time())) - 8 * 3600, end_time),
        graph_render_config.size[1],
    )

    html.write_html(
        render_graphs_from_specification_html(
            TemplateGraphSpecification(
                site=site,
                host_name=host_name,
                service_description=service_description,
            ),
            graph_data_range,
            graph_render_config,
            render_async=False,
        )
    )


def _render_graph_or_error_html(
    graph_artwork: GraphArtwork,
    graph_data_range: GraphDataRange,
    graph_render_config: GraphRenderConfig,
) -> HTML:
    try:
        return _render_graph_html(graph_artwork, graph_data_range, graph_render_config)
    except Exception as e:
        return render_graph_error_html(e)


def render_graph_error_html(msg_or_exc: Exception | str, title: str | None = None) -> HTML:
    if isinstance(msg_or_exc, MKGeneralException) and not active_config.debug:
        msg = "%s" % msg_or_exc

    elif isinstance(msg_or_exc, Exception):
        if active_config.debug:
            raise msg_or_exc
        msg = traceback.format_exc()
    else:
        msg = msg_or_exc

    if title is None:
        title = _("Cannot display graph")

    return HTMLWriter.render_div(
        HTMLWriter.render_div(title, class_="title") + HTMLWriter.render_pre(msg),
        class_=["graph", "brokengraph"],
    )


# Render the complete HTML code of a graph - including its <div> container.
# Later updates will just replace the content of that container.
def _render_graph_html(
    graph_artwork: GraphArtwork,
    graph_data_range: GraphDataRange,
    graph_render_config: GraphRenderConfig,
) -> HTML:
    with output_funnel.plugged():
        _show_graph_html_content(graph_artwork, graph_data_range, graph_render_config)
        html_code = HTML(output_funnel.drain())

    return HTMLWriter.render_javascript(
        "cmk.graphs.create_graph(%s, %s, %s, %s);"
        % (
            json.dumps(html_code),
            json.dumps(graph_artwork.model_dump()),
            json.dumps(graph_render_config.model_dump()),
            json.dumps(_graph_ajax_context(graph_artwork, graph_data_range, graph_render_config)),
        )
    )


# The ajax context will be passed back to us to the page handler ajax_graph() whenever
# an update of the graph should be done. It must contain everything that we need to
# create the HTML code of the graph. The entry "graph_id" will be set by the javascript
# code since it is not known to us.
def _graph_ajax_context(
    graph_artwork: GraphArtwork,
    graph_data_range: GraphDataRange,
    graph_render_config: GraphRenderConfig,
) -> dict[str, Any]:
    return {
        "definition": graph_artwork.definition.model_dump(),
        "data_range": graph_data_range.model_dump(),
        "render_config": graph_render_config.model_dump(),
        "display_id": graph_artwork.display_id,
    }


def _render_title_elements_plain(elements: Iterable[str]) -> str:
    return " / ".join(_u(txt) for txt in elements if txt)


def render_plain_graph_title(
    graph_artwork: GraphArtwork,
    graph_render_config: GraphRenderConfigBase,
) -> str:
    return _render_title_elements_plain(
        element[0] for element in _render_graph_title_elements(graph_artwork, graph_render_config)
    )


def _render_graph_title_elements(
    graph_artwork: GraphArtwork,
    graph_render_config: GraphRenderConfigBase,
    explicit_title: str | None = None,
) -> list[tuple[str, str | None]]:
    if not graph_render_config.show_title:
        return []

    # Hard override of the graph title. This is e.g. needed for the graph previews
    if explicit_title is not None:
        return [(explicit_title, None)]

    title_elements: list[tuple[str, str | None]] = []

    if graph_render_config.title_format.plain and graph_artwork.title:
        title_elements.append((graph_artwork.title, None))

    # Only add host/service information for template based graphs
    specification = graph_artwork.definition.specification
    if not isinstance(specification, TemplateGraphSpecification):
        return title_elements

    title_elements.extend(_title_info_elements(specification, graph_render_config.title_format))

    return title_elements


def _title_info_elements(
    spec_info: TemplateGraphSpecification, title_format: GraphTitleFormat
) -> Iterable[tuple[str, str]]:
    if title_format.add_host_name:
        host_url = makeuri_contextless(
            request,
            [("view_name", "hoststatus"), ("host", spec_info.host_name)],
            filename="view.py",
        )
        yield spec_info.host_name, host_url

    if title_format.add_host_alias:
        host_alias = get_alias_of_host(spec_info.site, spec_info.host_name)
        host_url = makeuri_contextless(
            request,
            [("view_name", "hoststatus"), ("host", spec_info.host_name)],
            filename="view.py",
        )
        yield host_alias, host_url

    if title_format.add_service_description:
        service_description = spec_info.service_description
        if service_description != "_HOST_":
            service_url = makeuri_contextless(
                request,
                [
                    ("view_name", "service"),
                    ("host", spec_info.host_name),
                    ("service", service_description),
                ],
                filename="view.py",
            )
            yield service_description, service_url


def _show_html_graph_title(
    graph_artwork: GraphArtwork, graph_render_config: GraphRenderConfig
) -> None:
    title = text_with_links_to_user_translated_html(
        _render_graph_title_elements(
            graph_artwork,
            graph_render_config,
            explicit_title=graph_render_config.explicit_title,
        ),
        separator=" / ",
    )
    if not title:
        return

    html.div(
        title,
        class_=["title"] + (["inline"] if graph_render_config.show_title == "inline" else []),
    )


def _graph_legend_enabled(
    graph_render_config: GraphRenderConfig, graph_artwork: GraphArtwork
) -> bool:
    return bool(graph_render_config.show_legend and graph_artwork.curves)


def _show_graph_html_content(
    graph_artwork: GraphArtwork,
    graph_data_range: GraphDataRange,
    graph_render_config: GraphRenderConfig,
) -> None:
    """Render the HTML code of a graph without its container

    That is a canvas object for drawing the actual graph and also legend, buttons, resize handle,
    etc.
    """
    html.open_div(
        class_=["graph"] + (["preview"] if graph_render_config.preview else []),
        style=(
            f"font-size: {graph_render_config.font_size:.1f}pt;"
            f"{_graph_padding_styles(graph_render_config.show_margin)}"
        ),
    )

    if graph_render_config.show_controls:
        _show_graph_add_to_icon_for_popup(graph_artwork, graph_data_range, graph_render_config)

    v_axis_label = graph_artwork.vertical_axis["axis_label"]
    if v_axis_label:
        html.div(v_axis_label, class_="v_axis_label")

    # Add the floating elements
    if graph_render_config.show_graph_time and not graph_render_config.preview:
        html.div(
            graph_artwork.time_axis["title"] or "",
            css=["time"] + (["inline"] if graph_render_config.show_title == "inline" else []),
        )

    if graph_render_config.show_controls and graph_render_config.resizable:
        html.img(src=theme.url("images/resize_graph.png"), class_="resize")

    _show_html_graph_title(graph_artwork, graph_render_config)
    _show_graph_canvas(graph_render_config.size)

    # Note: due to "omit_zero_metrics" the graph might not have any curves
    if _graph_legend_enabled(graph_render_config, graph_artwork):
        _show_graph_legend(graph_artwork, graph_render_config)

    if additional_html := graph_artwork.definition.additional_html:
        html.open_div(align="center")
        html.h2(additional_html.title)
        html.write_html(HTML(additional_html.html))
        html.close_div()

    html.close_div()


def _show_graph_add_to_icon_for_popup(
    graph_artwork: GraphArtwork,
    graph_data_range: GraphDataRange,
    graph_render_config: GraphRenderConfig,
) -> None:
    icon_html = html.render_icon("menu", _("Add to ..."))
    element_type_name = "pnpgraph"

    # Data will be transferred via URL and Javascript magic eventually
    # to our function popup_add_element (htdocs/reporting.py)
    # argument report_name --> provided by popup system
    # further arguments:
    html.popup_trigger(
        content=icon_html,
        ident="add_visual",
        method=MethodAjax(endpoint="add_visual", url_vars=[("add_type", "pnpgraph")]),
        data=[
            element_type_name,
            None,
            _graph_ajax_context(graph_artwork, graph_data_range, graph_render_config),
        ],
        style="z-index:2",
    )  # Ensures that graph canvas does not cover it


def _show_graph_canvas(size: tuple[int, int]) -> None:
    """Create canvas where actual graph will be rendered"""
    graph_width: float = size[0] * html_size_per_ex
    graph_height: float = size[1] * html_size_per_ex
    html.canvas(
        "",
        style="position: relative; width: %dpx; height: %dpx;" % (graph_width, graph_height),
        width=str(graph_width * 2),
        height=str(graph_height * 2),
    )


def _show_pin_time(graph_artwork: GraphArtwork, config: GraphRenderConfig) -> bool:
    if not config.show_pin:
        return False

    timestamp = graph_artwork.pin_time
    return timestamp is not None and graph_artwork.start_time <= timestamp <= graph_artwork.end_time


def _render_pin_time_label(graph_artwork: GraphArtwork) -> str:
    timestamp = graph_artwork.pin_time
    return cmk.utils.render.date_and_time(timestamp)[:-3]


def _get_scalars(
    graph_artwork: GraphArtwork, graph_render_config: GraphRenderConfig
) -> list[tuple[str, str, bool]]:
    scalars = []
    for scalar, title in [
        ("min", _("Minimum")),
        ("max", _("Maximum")),
        ("average", _("Average")),
    ]:
        consolidation_function = graph_artwork.definition.consolidation_function
        inactive = consolidation_function is not None and consolidation_function != scalar

        scalars.append((scalar, title, inactive))

    scalars.append(("last", _("Last"), False))

    if _show_pin_time(graph_artwork, graph_render_config):
        scalars.append(("pin", _render_pin_time_label(graph_artwork), False))

    return scalars


def _show_graph_legend(  # pylint: disable=too-many-branches
    graph_artwork: GraphArtwork, graph_render_config: GraphRenderConfig
) -> None:
    """Render legend that describe the metrics"""
    graph_width = graph_render_config.size[0] * html_size_per_ex
    font_size_style = "font-size: %dpt;" % graph_render_config.font_size

    scalars = _get_scalars(graph_artwork, graph_render_config)

    if graph_render_config.show_vertical_axis or graph_render_config.show_controls:
        legend_margin_left = 49
    else:
        legend_margin_left = 0

    style = []
    legend_width = graph_width - legend_margin_left

    # In case there is no margin show: Add some to the legend since it looks
    # ugly when there is no space between the outer graph border and the legend
    if not graph_render_config.show_margin:
        legend_width -= 5 * 2
        style.append("margin: 8px 5px 5px 5px")

    style.append("width:%dpx" % legend_width)

    if legend_margin_left:
        style.append("margin-left:%dpx" % legend_margin_left)

    html.open_table(class_="legend", style=style)

    # Render the title row
    html.open_tr()
    html.th("")
    for scalar, title, inactive in scalars:
        classes = ["scalar", scalar]
        if inactive and graph_artwork.step != 60:
            descr = _(
                'This graph is based on data consolidated with the function "%s". The '
                'values in this column are the "%s" values of the "%s" values '
                "aggregated in %s steps. Assuming a check interval of 1 minute, the %s "
                "values here are based on the %s value out of %d raw values."
            ) % (
                graph_artwork.definition.consolidation_function,
                scalar,
                graph_artwork.definition.consolidation_function,
                get_step_label(graph_artwork.step),
                scalar,
                graph_artwork.definition.consolidation_function,
                (graph_artwork.step / 60),
            )

            descr += (
                "\n\n"
                + _('Click here to change the graphs consolidation function to "%s".') % scalar
            )

            classes.append("inactive")
        else:
            descr = ""

        html.th(title, class_=classes, style=font_size_style, title=descr)
    html.close_tr()

    # Render the curve related rows
    for curve in order_graph_curves_for_legend_and_mouse_hover(
        graph_artwork.definition, graph_artwork.curves
    ):
        html.open_tr()
        html.open_td(style=font_size_style)
        html.write_html(render_color_icon(curve["color"]))
        html.write_text(curve["title"])
        html.close_td()

        for scalar, title, inactive in scalars:
            if scalar == "pin" and not _show_pin_time(graph_artwork, graph_render_config):
                continue

            classes = ["scalar"]
            if inactive and graph_artwork.step != 60:
                classes.append("inactive")

            html.td(curve["scalars"][scalar][1], class_=classes, style=font_size_style)

        html.close_tr()

    # Render scalar values
    if graph_artwork.horizontal_rules:
        first = True
        for horizontal_rule in graph_artwork.horizontal_rules:
            html.open_tr(class_=["scalar"] + (["first"] if first else []))
            html.open_td(style=font_size_style)
            html.write_html(render_color_icon(horizontal_rule.color))
            html.write_text(str(horizontal_rule.title))
            html.close_td()

            # A colspan of 5 has to be used here, since the pin that is added by a click into
            # the graph introduces a new column.
            html.td(
                horizontal_rule.rendered_value,
                colspan=5,
                class_="scalar",
                style=font_size_style,
            )
            html.close_tr()
            first = False

    html.close_table()


@dataclass(frozen=True, kw_only=True)
class Bounds:
    top: int
    right: int
    bottom: int
    left: int


def _graph_padding_styles(show_margin: bool) -> str:
    bounds = _graph_margin_ex(show_margin)
    return (
        "padding: "
        f"{bounds.top:.2f}ex "
        f"{bounds.right:.2f}ex "
        f"{bounds.bottom:.2f}ex "
        f"{bounds.left:.2f}ex;"
    )


def _graph_margin_ex(
    show_margin: bool,
    *,
    top: int = 8,
    right: int = 16,
    bottom: int = 4,
    left: int = 8,
) -> Bounds:
    return (
        Bounds(
            top=int(round(top / html_size_per_ex)),
            right=int(round(right / html_size_per_ex)),
            bottom=int(round(bottom / html_size_per_ex)),
            left=int(round(left / html_size_per_ex)),
        )
        if show_margin
        else Bounds(
            top=0,
            right=0,
            bottom=0,
            left=0,
        )
    )


# NOTE
# No AjaxPage, as ajax-pages have a {"result_code": [1|0], "result": ..., ...} result structure,
# while these functions do not have that. In order to preserve the functionality of the JS side
# of things, we keep it.
# TODO: Migrate this to a real AjaxPage
class AjaxGraph(cmk.gui.pages.Page):
    @classmethod
    def ident(cls) -> str:
        return "ajax_graph"

    def page(self) -> PageResult:  # pylint: disable=useless-return
        """Registered as `ajax_graph`."""
        response.set_content_type("application/json")
        try:
            context_var = request.get_str_input_mandatory("context")
            context = json.loads(context_var)
            response_data = _render_ajax_graph(context)
            response.set_data(json.dumps(response_data))
        except Exception as e:
            logger.error("Ajax call ajax_graph.py failed: %s\n%s", e, traceback.format_exc())
            if active_config.debug:
                raise
            response.set_data("ERROR: %s" % e)
        return None


def _render_ajax_graph(context: Mapping[str, Any]) -> dict[str, Any]:
    graph_data_range = GraphDataRange.model_validate(context["data_range"])
    graph_render_config = GraphRenderConfig.model_validate(context["render_config"])
    graph_recipe = GraphRecipe.model_validate(context["definition"])

    start_time_var = request.var("start_time")
    end_time_var = request.var("end_time")
    step_var = request.var("step")
    if start_time_var is not None and end_time_var is not None and step_var is not None:
        start_time = int(float(start_time_var))
        end_time = int(float(end_time_var))
        # since step can be relatively small, we round
        step: int | str = int(round(float(step_var)))
    else:
        start_time, end_time = graph_data_range.time_range
        step = graph_data_range.step

    resize_x_var = request.var("resize_x")
    resize_y_var = request.var("resize_y")

    if resize_x_var is not None and resize_y_var is not None:
        render_opt_x, render_opt_y = graph_render_config.size
        size_x = int(max(min_resize_width, float(resize_x_var) / html_size_per_ex + render_opt_x))
        size_y = int(max(min_resize_height, float(resize_y_var) / html_size_per_ex + render_opt_y))
        user.save_file("graph_size", (size_x, size_y))
        graph_render_config.size = (size_x, size_y)

    range_from_var = request.var("range_from")
    range_to_var = request.var("range_to")
    if range_from_var is not None and range_to_var is not None:
        vertical_range: tuple[float, float] | None = (float(range_from_var), float(range_to_var))
    else:
        vertical_range = None

    if request.has_var("pin"):
        save_graph_pin()

    if request.has_var("consolidation_function"):
        graph_recipe = graph_recipe.model_copy(
            update={"consolidation_function": request.var("consolidation_function")}
        )

    graph_data_range = GraphDataRange(
        time_range=(start_time, end_time),
        vertical_range=vertical_range,
        step=step,
    )

    # Persist the current data range for the graph editor.
    if graph_render_config.editing and (
        specification_id := context.get("definition", {}).get("specification", {}).get("id")
    ):
        UserGraphDataRangeStore(user).save(specification_id, graph_data_range)

    graph_artwork = compute_graph_artwork(
        graph_recipe,
        graph_data_range,
        graph_render_config.size,
    )

    with output_funnel.plugged():
        _show_graph_html_content(graph_artwork, graph_data_range, graph_render_config)
        html_code = HTML(output_funnel.drain())

    return {
        "html": html_code,
        "graph": graph_artwork.model_dump(),
        "context": {
            "graph_id": context["graph_id"],
            "definition": graph_recipe.model_dump(),
            "data_range": graph_data_range.model_dump(),
            "render_config": graph_render_config.model_dump(),
        },
    }


def _user_graph_data_range_file_name(custom_graph_id: str) -> str:
    return f"graph_range_{custom_graph_id}"


class UserGraphDataRangeStore:
    def __init__(self, user_: LoggedInUser) -> None:
        self.user = user_

    def save(self, custom_graph_id: str, graph_data_range: GraphDataRange) -> None:
        self.user.save_file(
            _user_graph_data_range_file_name(custom_graph_id),
            graph_data_range.model_dump(),
        )

    def load(self, custom_graph_id: str) -> GraphDataRange | None:
        return (
            GraphDataRange.model_validate(raw_range)
            if (
                raw_range := self.user.load_file(
                    _user_graph_data_range_file_name(custom_graph_id), None
                )
            )
            else None
        )

    def remove(self, custom_graph_id: str) -> None:
        (
            profile_dir
            / self.user.ident
            / f"{_user_graph_data_range_file_name(custom_graph_id)}.mk"
        ).unlink(missing_ok=True)


def _resolve_graph_recipe_with_error_handling(
    graph_specification: GraphSpecification,
) -> Sequence[GraphRecipe] | HTML:
    try:
        return graph_specification.recipes()
    except MKLivestatusNotFoundError:
        return render_graph_error_html(
            "%s\n\n%s: %r"
            % (
                _("Cannot fetch data via Livestatus"),
                _("The graph specification is"),
                graph_specification,
            ),
            _("Cannot calculate graph recipes"),
        )
    except Exception as e:
        return render_graph_error_html(e, _("Cannot calculate graph recipes"))


def render_graphs_from_specification_html(
    graph_specification: GraphSpecification,
    graph_data_range: GraphDataRange,
    graph_render_config: GraphRenderConfig,
    *,
    render_async: bool = True,
    graph_display_id: str = "",
) -> HTML:
    graph_recipes = _resolve_graph_recipe_with_error_handling(graph_specification)
    if isinstance(graph_recipes, HTML):
        return graph_recipes  # This is to html.write the exception

    return _render_graphs_from_definitions(
        graph_recipes,
        graph_data_range,
        graph_render_config,
        render_async=render_async,
        graph_display_id=graph_display_id,
    )


def _render_graphs_from_definitions(
    graph_recipes: Sequence[GraphRecipe],
    graph_data_range: GraphDataRange,
    graph_render_config: GraphRenderConfig,
    *,
    render_async: bool = True,
    graph_display_id: str = "",
) -> HTML:
    output = HTML()
    for graph_recipe in graph_recipes:
        recipe_specific_render_config = graph_render_config.model_copy(
            update=dict(graph_recipe.render_options)
        )
        recipe_specific_data_range = graph_data_range.model_copy(
            update=dict(graph_recipe.data_range or {})
        )

        if render_async:
            output += _render_graph_container_html(
                graph_recipe,
                recipe_specific_data_range,
                recipe_specific_render_config,
                graph_display_id=graph_display_id,
            )
        else:
            output += _render_graph_content_html(
                graph_recipe,
                recipe_specific_data_range,
                recipe_specific_render_config,
                graph_display_id=graph_display_id,
            )
    return output


# cmk.graphs.load_graph_content will call ajax_render_graph_content() via JSON to finally load the graph
def _render_graph_container_html(
    graph_recipe: GraphRecipe,
    graph_data_range: GraphDataRange,
    graph_render_config: GraphRenderConfig,
    *,
    graph_display_id: str,
) -> HTML:
    # Estimate size of graph. This will not be the exact size of the graph, because
    # this does calculate the size of the canvas area and does not take e.g. the legend
    # into account. We would need the graph_artwork to calculate that, but this is something
    # we don't have in this early stage.
    graph_width = graph_render_config.size[0] * html_size_per_ex
    graph_height = graph_render_config.size[1] * html_size_per_ex

    content = HTMLWriter.render_div("", class_="title") + HTMLWriter.render_div(
        "", class_="content", style="width:%dpx;height:%dpx" % (graph_width, graph_height)
    )

    output = HTMLWriter.render_div(
        HTMLWriter.render_div(content, class_=["graph", "loading_graph"]),
        class_="graph_load_container",
    )
    output += HTMLWriter.render_javascript(
        "cmk.graphs.load_graph_content(%s, %s, %s, %s)"
        % (
            json.dumps(graph_recipe.model_dump()),
            json.dumps(graph_data_range.model_dump()),
            json.dumps(graph_render_config.model_dump()),
            json.dumps(graph_display_id),
        )
    )

    if "cmk.graphs.register_delayed_graph_listener" not in html.final_javascript_code():
        html.final_javascript("cmk.graphs.register_delayed_graph_listener()")

    return output


class AjaxRenderGraphContent(AjaxPage):
    @classmethod
    def ident(cls) -> str:
        return "ajax_render_graph_content"

    def page(self) -> PageResult:
        # Called from javascript code via JSON to initially render a graph
        """Registered as `ajax_render_graph_content`."""
        api_request = request.get_request()
        return _render_graph_content_html(
            GraphRecipe.model_validate(api_request["graph_recipe"]),
            GraphDataRange.model_validate(api_request["graph_data_range"]),
            GraphRenderConfig.model_validate(api_request["graph_render_config"]),
            graph_display_id=api_request["graph_display_id"],
        )


def _render_graph_content_html(
    graph_recipe: GraphRecipe,
    graph_data_range: GraphDataRange,
    graph_render_config: GraphRenderConfig,
    *,
    graph_display_id: str = "",
) -> HTML:
    output = HTML()

    try:
        graph_artwork = compute_graph_artwork(
            graph_recipe,
            graph_data_range,
            graph_render_config.size,
            graph_display_id=graph_display_id,
        )
        main_graph_html = _render_graph_or_error_html(
            graph_artwork, graph_data_range, graph_render_config
        )

        if graph_render_config.show_time_range_previews:
            output += HTMLWriter.render_div(
                main_graph_html
                + _render_time_range_selection(
                    graph_recipe,
                    graph_render_config,
                    graph_display_id=graph_display_id,
                ),
                class_="graph_with_timeranges",
            )
        else:
            output += main_graph_html

    except MKLivestatusNotFoundError:
        output += render_graph_error_html(
            _("Cannot fetch data via Livestatus"), _("Cannot create graph")
        )
    except MKMissingDataError as e:
        return html.render_message(str(e))

    except Exception as e:
        output += render_graph_error_html(e, _("Cannot create graph"))
    return output


def _render_time_range_selection(
    graph_recipe: GraphRecipe,
    graph_render_config: GraphRenderConfig,
    *,
    graph_display_id: str,
) -> HTML:
    now = int(time.time())
    graph_render_config = copy.deepcopy(graph_render_config)
    rows = []
    for timerange_attrs in active_config.graph_timeranges:
        duration = timerange_attrs["duration"]
        assert isinstance(duration, int)

        graph_render_config.size = (20, 4)
        graph_render_config.font_size = SizePT(6.0)
        graph_render_config.onclick = "cmk.graphs.change_graph_timerange(graph, %d)" % duration
        graph_render_config.fixed_timerange = (
            True  # Do not follow timerange changes of other graphs
        )
        graph_render_config.explicit_title = timerange_attrs["title"]
        graph_render_config.show_legend = False
        graph_render_config.show_controls = False
        graph_render_config.preview = True
        graph_render_config.resizable = False
        graph_render_config.interaction = False

        timerange = now - duration, now
        graph_data_range = GraphDataRange(
            time_range=timerange,
            step=2 * estimate_graph_step_for_html(timerange, graph_render_config.size[1]),
        )

        graph_artwork = compute_graph_artwork(
            graph_recipe,
            graph_data_range,
            graph_render_config.size,
            graph_display_id=graph_display_id,
        )
        rows.append(
            HTMLWriter.render_td(
                _render_graph_html(graph_artwork, graph_data_range, graph_render_config),
                title=_("Change graph time range to: %s") % timerange_attrs["title"],
            )
        )
    return HTMLWriter.render_table(
        HTML().join(HTMLWriter.render_tr(content) for content in rows), class_="timeranges"
    )


def make_graph_data_range(
    time_range: tuple[int, int],
    width_in_ex: int,
) -> GraphDataRange:
    return GraphDataRange(
        time_range=time_range,
        step=estimate_graph_step_for_html(time_range, width_in_ex),
    )


def estimate_graph_step_for_html(
    time_range: tuple[int, int],
    width_in_ex: int,
) -> int:
    steps_per_ex = html_size_per_ex * 4
    number_of_steps = width_in_ex * steps_per_ex
    return int((time_range[1] - time_range[0]) / number_of_steps)


# .
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


# NOTE
# No AjaxPage, as ajax-pages have a {"result_code": [1|0], "result": ..., ...} result structure,
# while these functions do not have that. In order to preserve the functionality of the JS side
# of things, we keep it.
# TODO: Migrate this to a real AjaxPage
class AjaxGraphHover(cmk.gui.pages.Page):
    @classmethod
    def ident(cls) -> str:
        return "ajax_graph_hover"

    def page(self) -> PageResult:  # pylint: disable=useless-return
        """Registered as `ajax_graph_hover`."""
        response.set_content_type("application/json")
        try:
            context_var = request.get_str_input_mandatory("context")
            context = json.loads(context_var)
            hover_time = request.get_integer_input_mandatory("hover_time")
            response_data = _render_ajax_graph_hover(context, hover_time)
            response.set_data(json.dumps(response_data))
        except Exception as e:
            logger.error("Ajax call ajax_graph_hover.py failed: %s\n%s", e, traceback.format_exc())
            if active_config.debug:
                raise
            response.set_data("ERROR: %s" % e)
        return None


def _render_ajax_graph_hover(
    context: Mapping[str, Any],
    hover_time: int,
) -> dict[str, object]:
    graph_data_range = GraphDataRange.model_validate(context["data_range"])
    graph_recipe = GraphRecipe.model_validate(context["definition"])

    curves = compute_graph_artwork_curves(graph_recipe, graph_data_range)

    return {
        "rendered_hover_time": cmk.utils.render.date_and_time(hover_time),
        "curve_values": list(
            compute_curve_values_at_timestamp(
                order_graph_curves_for_legend_and_mouse_hover(graph_recipe, curves),
                graph_recipe.unit,
                hover_time,
            )
        ),
    }


# Estimates the height of the graph legend in pixels
# TODO: This is not acurate! Especially when the font size is changed this does not lead to correct
# results. But this is a more generic problem of the html_size_per_ex which is hard coded instead
# of relying on the font as it should.
def _graph_legend_height_ex(
    graph_render_config: GraphRenderConfig, graph_artwork: GraphArtwork
) -> float:
    if not _graph_legend_enabled(graph_render_config, graph_artwork):
        return 0.0
    # Add header line + spacing: '3.0'
    return 3.0 + (len(list(graph_artwork.curves)) + len(graph_artwork.horizontal_rules)) * 1.3


# .
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
    def choices(cls) -> list[tuple[str, str]]:
        return [
            (GraphDestinations.dashlet, _("Dashboard element")),
            (GraphDestinations.view, _("View")),
            (GraphDestinations.report, _("Report")),
            (GraphDestinations.notification, _("Notification")),
        ]


def _graph_title_height_ex(config: GraphRenderConfig) -> SizeEx:
    if config.show_title in [False, "inline"]:
        return SizeEx(0)
    return SizeEx(1)


def host_service_graph_dashlet_cmk(
    graph_specification: GraphSpecification,
    graph_render_config: GraphRenderConfig,
    *,
    graph_display_id: str = "",
) -> HTML | None:
    width_var = request.get_float_input_mandatory("width", 0.0)
    width = int(width_var / html_size_per_ex)

    height_var = request.get_float_input_mandatory("height", 0.0)
    height = int(height_var / html_size_per_ex)

    bounds = _graph_margin_ex(graph_render_config.show_margin)
    height -= _graph_title_height_ex(graph_render_config)
    height -= bounds.top + bounds.bottom
    width -= bounds.left + bounds.right

    graph_render_config.size = (width, height)

    time_range: TimerangeValue = json.loads(request.get_str_input_mandatory("timerange"))

    end_time: float
    start_time: float
    # Age and Range like ["age", 300] and ['date', [1661896800, 1661896800]]
    if isinstance(time_range, list):
        # compute_range needs tuple for computation
        timerange_tuple: tuple[str, Any] = (time_range[0], time_range[1])
        start_time, end_time = Timerange.compute_range(timerange_tuple).range
    # Age like 14400 and y1, d1,...
    else:
        start_time, end_time = Timerange.compute_range(time_range).range

    graph_data_range = make_graph_data_range((start_time, end_time), graph_render_config.size[1])

    graph_recipes = _resolve_graph_recipe_with_error_handling(graph_specification)
    if isinstance(graph_recipes, HTML):
        return graph_recipes  # This is to html.write the exception
    if graph_recipes:
        graph_recipe = graph_recipes[0]
    else:
        raise MKGeneralException(_("Failed to calculate a graph recipe."))

    # When the legend is enabled, we need to reduce the height by the height of the legend to
    # make the graph fit into the dashlet area.
    if graph_render_config.show_legend:
        # TODO FIXME: This graph artwork is calulated twice. Once here and once in render_graphs_from_specification_html()
        graph_artwork = compute_graph_artwork(
            graph_recipe,
            graph_data_range,
            graph_render_config.size,
        )
        if graph_artwork.curves:
            legend_height = _graph_legend_height_ex(
                graph_render_config,
                graph_artwork,
            )
            graph_render_config.size = (width, int(height - legend_height))

    html_code = _render_graphs_from_definitions(
        [graph_recipe],
        graph_data_range,
        graph_render_config,
        render_async=False,
        graph_display_id=graph_display_id,
    )
    html.write_html(html_code)
    return None
