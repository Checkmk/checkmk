#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
import itertools
from typing import List, TYPE_CHECKING, Set, Tuple, Iterator

import cmk.utils.version as cmk_version
import cmk.utils.render
from cmk.utils.defines import (
    host_state_name,
    service_state_name,
)

import cmk.gui.config as config

import cmk.gui.availability as availability
from cmk.gui.availability import (
    AVObjectType,
    AVOptions,
    AVObjectSpec,
    AVSpan,
    AVMode,
    AVRowCells,
    AVObjectCells,
    AVData,
    AVRawData,
    AVEntry,
    AVTimeRange,
    AVOptionValueSpecs,
)
from cmk.gui.table import table_element, Table

import cmk.gui.bi as bi
from cmk.gui.i18n import _
from cmk.gui.globals import html, request
from cmk.gui.htmllib import HTML
from cmk.gui.breadcrumb import BreadcrumbItem, Breadcrumb
from cmk.gui.page_menu import (
    PageMenu,
    PageMenuDropdown,
    PageMenuTopic,
    PageMenuEntry,
    PageMenuSidePopup,
    make_simple_link,
    make_simple_form_page_menu,
)

from cmk.gui.exceptions import MKUserError

from cmk.gui.valuespec import (
    ValueSpec,
    Checkbox,
    TextAreaUnicode,
    TextAscii,
    Dictionary,
    TextUnicode,
    Optional,
    AbsoluteDate,
    DropdownChoice,
    MonitoringState,
    HostState,
)

from cmk.gui.plugins.views import (
    view_title,
    display_options,
    format_plugin_output,
)

from cmk.gui.utils.urls import makeuri, make_confirm_link

from cmk.gui.visuals import page_menu_dropdown_add_to_visual

if TYPE_CHECKING:
    from cmk.gui.type_defs import (
        FilterHeaders,
        Rows,
        HTTPVariables,
    )
    from cmk.gui.views import View

# Variable name conventions
# av_rawdata: a two tier dict: (site, host) -> service -> list(spans)
#   In case of BI (site, host) is (None, aggr_group), service is aggr_name
# availability_table: a list of dicts. Each dicts describes the availability
#   information of one object (seconds being OK, CRIT, etc.)

#   .--Options-------------------------------------------------------------.
#   |                   ___        _   _                                   |
#   |                  / _ \ _ __ | |_(_) ___  _ __  ___                   |
#   |                 | | | | '_ \| __| |/ _ \| '_ \/ __|                  |
#   |                 | |_| | |_) | |_| | (_) | | | \__ \                  |
#   |                  \___/| .__/ \__|_|\___/|_| |_|___/                  |
#   |                       |_|                                            |
#   +----------------------------------------------------------------------+
#   |  Handling of all options for tuning availability computation and     |
#   |  display.                                                            |
#   '----------------------------------------------------------------------'


def get_availability_options_from_request(what: AVObjectType) -> AVOptions:
    avoptions = availability.get_default_avoptions()

    # Users of older versions might not have all keys set. The following
    # trick will merge their options with our default options.
    avoptions.update(config.user.load_file("avoptions", {}))

    avoption_entries = availability.get_av_display_options(what)
    if html.request.var("avoptions") == "set":
        for name, _height, _show_in_reporting, vs in avoption_entries:
            try:
                avoptions[name] = vs.from_html_vars("avo_" + name)
                vs.validate_value(avoptions[name], "avo_" + name)
            except MKUserError as e:
                html.add_user_error(e.varname, e)

    range_vs = availability.vs_rangespec()
    try:
        range_, range_title = range_vs.compute_range(avoptions["rangespec"])
        avoptions["range"] = range_, range_title
    except MKUserError as e:
        html.add_user_error(e.varname, e)

    if html.request.var("_unset_logrow_limit") == "1":
        avoptions["logrow_limit"] = 0

    if html.form_submitted():
        config.user.save_file("avoptions", avoptions)

    return avoptions


def _handle_availability_option_reset() -> None:
    if html.request.var("_reset"):
        config.user.save_file("avoptions", {})
        html.request.del_vars("avo_")
        html.request.del_var("avoptions")


def _show_availability_options(option_type: str, what: AVObjectType, avoptions: AVOptions,
                               valuespecs: AVOptionValueSpecs) -> None:
    html.begin_form("avoptions")
    html.hidden_field("avoptions", "set")

    _show_availability_options_controls()

    container_id = "av_options_%s" % option_type
    html.open_div(id_=container_id, class_="side_popup_content")
    if html.has_user_errors():
        html.show_user_errors()

    for name, height, _show_in_reporting, vs in valuespecs:
        html.render_floating_option(name, height, "avo_", vs, avoptions.get(name))
    html.close_div()

    html.hidden_fields()
    html.end_form()


def _show_availability_options_controls() -> None:
    html.open_div(class_="side_popup_controls")

    html.open_div(class_="update_buttons")
    html.button("apply", _("Apply"), "submit")
    reset_url = makeuri(
        request,
        [("_reset", "1")],
        remove_prefix="avo_",
        delvars=["apply", "filled_in"],
    )
    html.buttonlink(reset_url, _("Reset"))
    html.close_div()

    html.close_div()


#.
#   .--Rendering-----------------------------------------------------------.
#   |            ____                _           _                         |
#   |           |  _ \ ___ _ __   __| | ___ _ __(_)_ __   __ _             |
#   |           | |_) / _ \ '_ \ / _` |/ _ \ '__| | '_ \ / _` |            |
#   |           |  _ <  __/ | | | (_| |  __/ |  | | | | | (_| |            |
#   |           |_| \_\___|_| |_|\__,_|\___|_|  |_|_| |_|\__, |            |
#   |                                                    |___/             |
#   +----------------------------------------------------------------------+
#   |  Rendering availability data into HTML.                              |
#   '----------------------------------------------------------------------'

# Hints:
# There are several modes for displaying data
# 1. Availability table
# 2. Timeline view with chronological events of one object
# There are two types of data sources
# a. Hosts/Services (identified by site, host and service)
# b. BI aggregates (identified by aggr_groups and aggr_name)
# The code flow for these four combinations is different
#


# Render the page showing availability table or timelines. It
# is (currently) called by views.py, when showing a view but
# availability mode is activated.
def show_availability_page(view: 'View', filterheaders: 'FilterHeaders') -> None:
    config.user.need_permission("general.see_availability")

    # We make reports about hosts, services or BI aggregates
    if "service" in view.datasource.infos:
        what = "service"
    elif "aggr_name" in view.datasource.infos:
        what = "bi"
    else:
        what = "host"

    _handle_availability_option_reset()
    avoptions = get_availability_options_from_request(what)
    time_range: AVTimeRange = avoptions["range"][0]
    range_title: str = avoptions["range"][1]

    # We have two display modes:
    # - Show availability table (stats) "availability"
    # - Show timeline                   "timeline"
    # --> controlled by URL variable "av_mode"
    av_mode = html.request.get_ascii_input_mandatory("av_mode", "availability")

    if av_mode == "timeline":
        title = _("Availability Timeline")
    else:
        title = _("Availability")

    # This is combined with the object selection
    # - Show all objects
    # - Show one specific object
    # --> controlled by URL variables "av_site", "av_host" and "av_service"
    # --> controlled by "av_aggr" in case of BI aggregate
    title += " - "
    av_object: AVObjectSpec = None
    if html.request.var("av_host"):
        av_object = (html.request.get_str_input_mandatory("av_site"),
                     html.request.get_str_input_mandatory("av_host"),
                     html.request.get_unicode_input_mandatory("av_service"))
        title += av_object[1]
        if av_object[2]:
            title += " - " + av_object[2]
    elif html.request.var("av_aggr"):
        av_object = (None, None, html.request.get_unicode_input_mandatory("av_aggr"))
        title += av_object[2]
    else:
        title += view_title(view.spec)

    title += " - " + range_title

    breadcrumb = view.breadcrumb()
    breadcrumb.append(BreadcrumbItem(
        title=title,
        url=breadcrumb[-1].url + "&mode=availability",
    ))

    if handle_edit_annotations(breadcrumb):
        return

    # Deletion must take place before computation, since it affects the outcome
    with html.plugged():
        handle_delete_annotations()
        confirmation_html_code = html.drain()

    # Remove variables for editing annotations, otherwise they will make it into the uris
    html.request.del_vars("anno_")
    if html.request.var("filled_in") == "editanno":
        html.request.del_var("filled_in")
    # Re-read the avoptions again, because the HTML vars have changed above (anno_ and editanno_ has
    # been removed, which must not be part of the form
    avoptions = get_availability_options_from_request(what)

    # Now compute all data, we need this also for CSV export
    if not html.has_user_errors():
        include_long_output = av_mode == "timeline" \
                and "timeline_long_output" in avoptions["labelling"]
        av_rawdata, has_reached_logrow_limit = availability.get_availability_rawdata(
            what,
            view.context,
            filterheaders,
            view.only_sites,
            av_object=av_object,
            include_output=av_mode == "timeline",
            include_long_output=include_long_output,
            avoptions=avoptions)
        av_data = availability.compute_availability(what, av_rawdata, avoptions)

    # Do CSV ouput
    if html.output_format == "csv_export" and config.user.may("general.csv_export"):
        _output_csv(what, av_mode, av_data, avoptions)
        return

    if display_options.enabled(display_options.H):
        html.body_start(title, force=True)

    if display_options.enabled(display_options.T):
        html.top_heading(title,
                         breadcrumb,
                         page_menu=_page_menu_availability(breadcrumb, view, what, av_mode,
                                                           av_object, time_range, avoptions)
                         if display_options.enabled(display_options.B) else None)

    if html.has_user_errors():
        html.final_javascript("cmk.page_menu.open_popup('avoptions');")

    html.write(confirmation_html_code)

    if not html.has_user_errors():
        # If we abolish the limit we have to fetch the data again
        # with changed logrow_limit = 0, which means no limit
        if has_reached_logrow_limit:
            text = _(
                "Your query matched more than %d log entries. "
                "<b>Note:</b> The number of shown rows does not necessarily reflect the "
                "matched entries and the result might be incomplete. ") % avoptions["logrow_limit"]
            text += html.render_a(
                _('Repeat query without limit.'),
                makeuri(request, [("_unset_logrow_limit", "1"), ("avo_logrow_limit", 0)]))
            html.show_warning(text)

        do_render_availability(what, av_rawdata, av_data, av_mode, av_object, avoptions)

    if display_options.enabled(display_options.Z):
        html.bottom_footer()

    if display_options.enabled(display_options.H):
        html.body_end()


def _page_menu_availability(breadcrumb: Breadcrumb, view, what: AVObjectType, av_mode: AVMode,
                            av_object: AVObjectSpec, time_range: AVTimeRange,
                            avoptions: AVOptions) -> PageMenu:
    menu = PageMenu(
        dropdowns=[
            PageMenuDropdown(
                name="availability",
                title=_("Availability"),
                topics=[
                    PageMenuTopic(
                        title=_("Options"),
                        entries=[
                            PageMenuEntry(
                                title=_("Change display options"),
                                icon_name="painteroptions",
                                item=PageMenuSidePopup(
                                    _render_avoptions_form(
                                        "display", what, avoptions,
                                        availability.get_av_display_options(what)),),
                                name="avoptions_display",
                            ),
                            PageMenuEntry(
                                title=_("Change computation options"),
                                icon_name="av_computation",
                                item=PageMenuSidePopup(
                                    _render_avoptions_form(
                                        "computation", what, avoptions,
                                        availability.get_av_computation_options()),),
                                name="avoptions_computation",
                            )
                        ],
                    ),
                    PageMenuTopic(
                        title=_("Display mode"),
                        entries=list(
                            _page_menu_entries_av_mode(what, av_mode, av_object, time_range)),
                    ),
                ],
            )
        ] + page_menu_dropdown_add_to_visual(add_type="availability", name=view.name) + [
            PageMenuDropdown(
                name="related",
                title=_("Related"),
                topics=[
                    PageMenuTopic(
                        title=_("Monitoring"),
                        entries=[
                            PageMenuEntry(
                                title=_("Status view"),
                                icon_name="status",
                                item=make_simple_link(makeuri(request, [("mode", "status")])),
                            ),
                        ],
                    ),
                ],
            ),
            PageMenuDropdown(
                name="export",
                title=_("Export"),
                topics=[
                    PageMenuTopic(
                        title=_("Data"),
                        entries=list(_page_menu_entries_export_data()),
                    ),
                    PageMenuTopic(
                        title=_("Reports"),
                        entries=list(_page_menu_entries_export_reporting()),
                    ),
                ],
            ),
        ],
        breadcrumb=breadcrumb,
    )

    return menu


def _render_avoptions_form(option_type: str, what: AVObjectType, avoptions: AVOptions,
                           valuespecs: AVOptionValueSpecs) -> str:
    with html.plugged():
        _show_availability_options(option_type, what, avoptions, valuespecs)
        return html.drain()


def _page_menu_entries_av_mode(what: AVObjectType, av_mode: AVMode, av_object: AVObjectSpec,
                               time_range: AVTimeRange) -> Iterator[PageMenuEntry]:

    if av_mode == "timeline" or av_object:
        yield PageMenuEntry(
            title=_("Availability"),
            icon_name="availability",
            item=make_simple_link(
                makeuri(request, [("av_mode", "availability"), ("av_host", ""), ("av_aggr", "")])),
        )
        return

    if what != "bi" and not av_object:
        yield PageMenuEntry(
            title=_("Timeline"),
            icon_name="timeline",
            item=make_simple_link(makeuri(request, [("av_mode", "timeline")])),
        )
        return

    if av_mode == "timeline" and what != "bi":
        history_url = availability.history_url_of(av_object, time_range)
        yield PageMenuEntry(
            title=_("History"),
            icon_name="history",
            item=make_simple_link(history_url),
        )


def _page_menu_entries_export_data() -> Iterator[PageMenuEntry]:
    if not config.user.may("general.csv_export"):
        return

    yield PageMenuEntry(
        title=_("Export CSV"),
        icon_name="download_csv",
        item=make_simple_link(makeuri(request, [("output_format", "csv_export")])),
    )


def _page_menu_entries_export_reporting() -> Iterator[PageMenuEntry]:
    if not config.reporting_available():
        return

    if not config.user.may("general.reporting") or not config.user.may("general.instant_reports"):
        return

    yield PageMenuEntry(
        title=_("This view as PDF"),
        icon_name="report",
        item=make_simple_link(makeuri(request, [], filename="report_instant.py")),
    )


def do_render_availability(what: AVObjectType, av_rawdata: AVRawData, av_data: AVData,
                           av_mode: AVMode, av_object: AVObjectSpec, avoptions: AVOptions) -> None:
    if av_mode == "timeline":
        render_availability_timelines(what, av_data, avoptions)
    else:
        availability_tables = availability.compute_availability_groups(what, av_data, avoptions)
        render_availability_tables(availability_tables, what, avoptions)

    annotations = availability.load_annotations()
    show_annotations(annotations, av_rawdata, what, avoptions, omit_service=av_object is not None)


def render_availability_tables(availability_tables, what, avoptions):
    if not availability_tables:
        html.show_message(_("No matching hosts/services."))
        return

    for group_title, availability_table in availability_tables:
        render_availability_table(group_title, availability_table, what, avoptions)

    # Legend for Availability levels
    av_levels = avoptions["av_levels"]
    if av_levels and "omit_av_levels" not in avoptions["labelling"]:
        warn, crit = av_levels
        html.open_div(class_="avlegend levels")
        html.h3(_("Availability levels"))

        html.div(_("OK"), class_="state state0")
        html.div("> %.3f%%" % warn, class_="level")
        html.div(_("WARN"), class_="state state1")
        html.div("> %.3f%%" % crit, class_="level")
        html.div(_("CRIT"), class_="state state2")
        html.div("< %.3f%%" % crit, class_="level")

        html.close_div()

    # Legend for timeline
    if "display_timeline_legend" in avoptions["labelling"] and avoptions["show_timeline"]:
        render_timeline_legend(what)


def render_availability_timelines(what: AVObjectType, av_data: AVData,
                                  avoptions: AVOptions) -> None:
    for timeline_nr, av_entry in enumerate(av_data):
        _render_availability_timeline(what, av_entry, avoptions, timeline_nr)


def _render_availability_timeline(what: AVObjectType, av_entry: AVEntry, avoptions: AVOptions,
                                  timeline_nr: int) -> None:
    html.open_h3()
    html.write("%s %s" % (_("Timeline of"), availability.object_title(what, av_entry)))
    html.close_h3()

    timeline_rows = av_entry["timeline"]

    if not timeline_rows:
        html.div(_("No information available"), class_="info")
        return

    timeline_layout = availability.layout_timeline(
        what,
        timeline_rows,
        av_entry["considered_duration"],
        avoptions,
        "standalone",
    )

    render_timeline_bar(timeline_layout, "standalone", timeline_nr)

    # Table with detailed events
    with table_element("av_timeline", "", css="timelineevents", sortable=False,
                       searchable=False) as table:
        for row_nr, row in enumerate(timeline_layout["table"]):
            table.row(
                id_="timetable_%d_entry_%d" % (timeline_nr, row_nr),
                onmouseover="cmk.availability.timetable_hover(%d, %d, 1);" % (timeline_nr, row_nr),
                onmouseout="cmk.availability.timetable_hover(%d, %d, 0);" % (timeline_nr, row_nr))

            table.cell(_("Links"), css="buttons")
            if what == "bi":
                url = makeuri(request, [("timewarp", str(int(row["from"])))])
                if html.request.var("timewarp") and html.request.get_integer_input_mandatory(
                        "timewarp") == int(row["from"]):
                    html.disabled_icon_button("timewarp_off")
                else:
                    html.icon_button(url,
                                     _("Time warp - show BI aggregate during this time period"),
                                     "timewarp")
            else:
                url = makeuri(
                    request,
                    [
                        ("anno_site", av_entry["site"]),
                        ("anno_host", av_entry["host"]),
                        ("anno_service", av_entry["service"]),
                        ("anno_from", str(row["from"])),
                        ("anno_until", str(row["until"])),
                    ],
                )
                html.icon_button(url, _("Create an annotation for this period"), "annotation")

            table.cell(_("From"), row["from_text"], css="nobr narrow")
            table.cell(_("Until"), row["until_text"], css="nobr narrow")
            table.cell(_("Duration"), row["duration_text"], css="narrow number")
            table.cell(_("State"), row["state_name"], css=row["css"] + " state narrow")

            if "omit_timeline_plugin_output" not in avoptions["labelling"]:
                table.cell(_("Last known summary"),
                           format_plugin_output(row.get("log_output", ""), row))

            if "timeline_long_output" in avoptions["labelling"]:
                table.cell(_("Last known details"),
                           format_plugin_output(row.get("long_log_output", ""), row))

    # Legend for timeline
    if "display_timeline_legend" in avoptions["labelling"]:
        render_timeline_legend(what)


def render_timeline_legend(what: AVObjectType) -> None:
    html.open_div(class_="avlegend timeline")

    html.h3(_('Timeline colors'))
    html.div(_("UP") if what == "host" else _("OK"), class_="state state0")

    if what != "host":
        html.div(_("WARN"), class_="state state1")

    html.div(_("DOWN") if what == "host" else _("CRIT"), class_="state state2")
    html.div(_("UNREACH") if what == "host" else _("UNKNOWN"), class_="state state3")
    html.div(_("Flapping"), class_="state flapping")

    if what != "host":
        html.div(_("H.Down"), class_="state hostdown")

    html.div(_("Downtime"), class_="state downtime")
    html.div(_("OO/Service"), class_="state ooservice")
    html.div(_("unmonitored"), class_="state unmonitored")

    html.close_div()


def render_availability_table(group_title, availability_table, what, avoptions):
    av_table = availability.layout_availability_table(what, group_title, availability_table,
                                                      avoptions)

    # TODO: If summary line is activated, then sorting should now move that line to the
    # top. It should also stay at the bottom. This would require an extension to the
    # table.py module.
    with table_element("av_items",
                       av_table["title"],
                       css="availability",
                       searchable=False,
                       limit=None,
                       omit_headers="omit_headers" in avoptions["labelling"]) as table:

        show_urls, show_timeline = False, False
        for row in av_table["rows"]:
            table.row()

            # Column with icons
            timeline_url = None
            if row["urls"]:
                show_urls = True
                table.cell("", css="buttons")
                for image, tooltip, url in row["urls"]:
                    html.icon_button(url, tooltip, image)
                    if image == "timeline":
                        timeline_url = url

            # Column with host/service or aggregate name
            for title, (name, url) in zip(av_table["object_titles"], row["object"]):
                table.cell(title, html.render_a(name, url))

            if "timeline" in row:
                show_timeline = True
                table.cell(_("Timeline"), css="timeline")
                html.open_a(href=timeline_url)
                render_timeline_bar(row["timeline"], "inline")
                html.close_a()

            # Columns with the actual availability data
            for (title, help_txt), (text, css) in zip(av_table["cell_titles"], row["cells"]):
                table.cell(title, text, css=css, help_txt=help_txt)

        if "summary" in av_table:
            table.row(css="summary", fixed=True)
            if show_urls:
                table.cell("", "")  # Empty cell in URLs column
            table.cell("", _("Summary"), css="heading")
            for _x in range(1, len(av_table["object_titles"])):
                table.cell("", "")  # empty cells, of more object titles than one
            if show_timeline:
                table.cell("", "")

            for (title, help_txt), (text, css) in zip(av_table["cell_titles"], av_table["summary"]):
                table.cell(title, text, css="heading " + css, help_txt=help_txt)


def render_timeline_bar(timeline_layout, style, timeline_nr=0):
    render_date = timeline_layout["render_date"]
    time_range: AVTimeRange = timeline_layout["range"]
    from_time, until_time = time_range
    html.open_div(class_=["timelinerange", style])

    if style == "standalone":
        html.div(render_date(from_time), class_="from")
        html.div(render_date(until_time), class_="until")

    if "time_choords" in timeline_layout:
        timebar_width = 500  # CSS width of inline timebar
        for position, title in timeline_layout["time_choords"]:
            pixel = timebar_width * position
            html.div('', title=title, class_="timelinechoord", style="left: %dpx" % pixel)

    html.open_table(id_="timeline_%d" % timeline_nr, class_=["timeline", style])
    html.open_tr(class_="timeline")
    for row_nr, title, width, css in timeline_layout["spans"]:

        td_attrs = {
            "style": "width: %.3f%%" % width,
            "title": title,
            "class": css,
        }

        if row_nr is not None:
            td_attrs.update({"id_": "timeline_%d_entry_%d" % (timeline_nr, row_nr)})

            if style == "standalone":
                td_attrs.update({
                    "onmouseover": "cmk.availability.timeline_hover(%d, %d, 1);" %
                                   (timeline_nr, row_nr),
                    "onmouseout": "cmk.availability.timeline_hover(%d, %d, 0);" %
                                  (timeline_nr, row_nr),
                })

        html.td('', **td_attrs)

    html.close_tr()
    html.close_table()

    html.close_div()


#.
#   .--BI------------------------------------------------------------------.
#   |                              ____ ___                                |
#   |                             | __ )_ _|                               |
#   |                             |  _ \| |                                |
#   |                             | |_) | |                                |
#   |                             |____/___|                               |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Special code for Business Intelligence availability                 |
#   '----------------------------------------------------------------------'


def _get_bi_availability(avoptions, aggr_rows, timewarp):

    logrow_limit = avoptions["logrow_limit"]
    if logrow_limit == 0:
        livestatus_limit = None
    else:
        livestatus_limit = (len(aggr_rows) * logrow_limit) + 1

    timeline_containers, fetched_rows = availability.get_timeline_containers(
        aggr_rows, avoptions, timewarp, livestatus_limit)

    has_reached_logrow_limit = livestatus_limit and fetched_rows > livestatus_limit

    spans: List[AVSpan] = []
    for timeline_container in timeline_containers:
        spans.extend(timeline_container.timeline)

    av_rawdata = availability.spans_by_object(spans)

    return timeline_containers, av_rawdata, has_reached_logrow_limit


# Render availability of a BI aggregate. This is currently
# no view and does not support display options
# TODO: Why should we handle this in a special way? Probably because we cannot
# get the list of BI aggregates from the statehist table but use the views
# logic for getting the aggregates. As soon as we have cleaned of the visuals,
# filters, contexts etc we can unify the code!
def show_bi_availability(view: "View", aggr_rows: 'Rows') -> None:
    config.user.need_permission("general.see_availability")

    av_mode = html.request.get_ascii_input_mandatory("av_mode", "availability")

    _handle_availability_option_reset()
    avoptions = get_availability_options_from_request("bi")

    title = view_title(view.spec)
    if av_mode == "timeline":
        title = _("Timeline of") + " " + title
    else:
        title = _("Availability of") + " " + title

    if html.output_format != "csv_export":
        html.body_start(title)

        breadcrumb = view.breadcrumb()
        breadcrumb.append(
            BreadcrumbItem(
                title=title,
                url=breadcrumb[-1].url + "&mode=availability",
            ))

        av_object: AVObjectSpec = None
        if html.request.var("av_aggr"):
            av_object = (None, None, html.request.get_unicode_input_mandatory("av_aggr"))

        # Dummy time_range, this is not needed for the BI
        page_menu = _page_menu_availability(breadcrumb, view, "bi", av_mode, av_object, (0.0, 0.0),
                                            avoptions)

        # This hack is needed because of some BI specific link. May be generalized in the future
        if av_mode != "timeline" and len(aggr_rows) == 1:
            dropdown = page_menu.get_dropdown_by_name("availability",
                                                      deflt=PageMenuDropdown(
                                                          name="availability",
                                                          title=_("Availability"),
                                                          topics=[]))
            if not dropdown:
                raise RuntimeError("Dropdown \"availability\" missing")

            aggr_name = aggr_rows[0]["aggr_name"]
            aggr_group = aggr_rows[0]["aggr_group"]
            timeline_url = makeuri(
                request,
                [
                    ("av_mode", "timeline"),
                    ("av_aggr_name", aggr_name),
                    ("av_aggr_group", aggr_group),
                ],
            )

            dropdown.topics[-1].entries.append(
                PageMenuEntry(
                    title=_("Timeline"),
                    icon_name="timeline",
                    item=make_simple_link(timeline_url),
                ))

        html.top_heading(title, breadcrumb, page_menu)

        avoptions = get_availability_options_from_request("bi")

    if not html.has_user_errors():

        # iterate all aggregation rows
        timewarpcode = HTML()
        timewarp = html.request.get_integer_input("timewarp")

        timeline_containers, av_rawdata, has_reached_logrow_limit = _get_bi_availability(
            avoptions, aggr_rows, timewarp)

        for timeline_container in timeline_containers:
            tree = timeline_container.aggr_tree
            these_spans = timeline_container.timeline
            timewarp_tree_state = timeline_container.timewarp_state

            # render selected time warp for the corresponding aggregation row (should be matched by only one)
            if timewarp and timewarp_tree_state:
                state, assumed_state, node, _subtrees = timewarp_tree_state
                eff_state = state
                if assumed_state is not None:
                    eff_state = assumed_state
                row = {
                    "aggr_tree": tree,
                    "aggr_treestate": timewarp_tree_state,
                    "aggr_state": state,  # state disregarding assumptions
                    "aggr_assumed_state": assumed_state,  # is None, if there are no assumptions
                    "aggr_effective_state": eff_state,  # is assumed_state, if there are assumptions, else real state
                    "aggr_name": node["title"],
                    "aggr_output": eff_state["output"],
                    "aggr_hosts": node["reqhosts"],
                    "aggr_group": html.request.var("aggr_group"),
                }

                renderer = bi.FoldableTreeRendererTree(
                    row,
                    omit_root=False,
                    expansion_level=config.user.bi_expansion_level,
                    only_problems=False,
                    lazy=False)
                tdclass, htmlcode = renderer.css_class(), renderer.render()

                with html.plugged():
                    # TODO: SOMETHING IS WRONG IN HERE (used to be the same situation in original code!)
                    # FIXME: WHAT is wrong in here??

                    html.open_h3()
                    # render icons for back and forth
                    button_back_shown = False
                    button_forth_shown = False
                    if int(these_spans[0]["from"]) == timewarp:
                        html.disabled_icon_button("back_off")
                        button_back_shown = True

                    previous_span = None
                    for span in these_spans:
                        if not button_back_shown and int(
                                span["from"]) == timewarp and previous_span is not None:
                            html.icon_button(
                                makeuri(request, [("timewarp", str(int(previous_span["from"])))]),
                                _("Jump one phase back"), "back")
                            button_back_shown = True
                        # Multiple followup spans can have the same "from" time
                        # We only show one forth-arrow with an actual time difference
                        elif not button_forth_shown and previous_span and int(
                                previous_span["from"]) == timewarp and int(
                                    span["from"]) != timewarp:
                            html.icon_button(
                                makeuri(
                                    request,
                                    [("timewarp", str(int(span["from"])))],
                                ), _("Jump one phase forth"), "forth")
                            button_forth_shown = True
                        previous_span = span
                    if not button_forth_shown:
                        html.disabled_icon_button("forth_off")

                    html.write_text(" &nbsp; ")
                    html.icon_button(makeuri(request, [("timewarp", "")]), _("Close Timewarp"),
                                     "closetimewarp")
                    html.write_text("%s %s" %
                                    (_("Timewarp to "),
                                     time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timewarp))))
                    html.close_h3()

                    html.open_table(class_=["data", "table", "timewarp"])
                    html.open_tr(class_=["data", "odd0"])
                    html.open_td(class_=tdclass)
                    html.write_html(htmlcode)
                    html.close_td()
                    html.close_tr()
                    html.close_table()

                    timewarpcode += html.drain()

        av_data = availability.compute_availability("bi", av_rawdata, avoptions)

        # If we abolish the limit we have to fetch the data again
        # with changed logrow_limit = 0, which means no limit
        if has_reached_logrow_limit:
            text = _(
                "Your query matched more than %d log entries. "
                "<b>Note:</b> The shown data does not necessarily reflect the "
                "matched entries and the result might be incomplete. ") % avoptions["logrow_limit"]
            text += html.render_a(_('Repeat query without limit.'),
                                  makeuri(request, [("_unset_logrow_limit", "1")]))
            html.show_warning(text)

        if html.output_format == "csv_export" and config.user.may("general.csv_export"):
            _output_csv("bi", av_mode, av_data, avoptions)
            return

        html.write(timewarpcode)
        do_render_availability("bi", av_rawdata, av_data, av_mode, None, avoptions)

    html.bottom_footer()
    html.body_end()


#.
#   .--Annotations---------------------------------------------------------.
#   |         _                      _        _   _                        |
#   |        / \   _ __  _ __   ___ | |_ __ _| |_(_) ___  _ __  ___        |
#   |       / _ \ | '_ \| '_ \ / _ \| __/ _` | __| |/ _ \| '_ \/ __|       |
#   |      / ___ \| | | | | | | (_) | || (_| | |_| | (_) | | | \__ \       |
#   |     /_/   \_\_| |_|_| |_|\___/ \__\__,_|\__|_|\___/|_| |_|___/       |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  This code deals with retrospective annotations and downtimes.       |
#   |  Here is just the code for editing and displaying them. The code     |
#   |  for loading, saving and using them is in the availability module.   |
#   '----------------------------------------------------------------------'


def get_relevant_annotations(annotations, by_host, what, avoptions):
    time_range: AVTimeRange = avoptions["range"][0]
    from_time, until_time = time_range

    annos_to_render = []
    annos_rendered: Set[int] = set()

    for site_host, avail_entries in by_host.items():
        for service in avail_entries.keys():
            for search_what in ["host", "service"]:
                if what == "host" and search_what == "service":
                    continue  # Service annotations are not relevant for host

                if search_what == "host":
                    site_host_svc = site_host[0], site_host[1], None
                else:
                    site_host_svc = site_host[0], site_host[1], service  # service can be None

                for annotation in annotations.get(site_host_svc, []):
                    if _annotation_affects_time_range(annotation["from"], annotation["until"],
                                                      from_time, until_time):
                        if id(annotation) not in annos_rendered:
                            annos_to_render.append((site_host_svc, annotation))
                            annos_rendered.add(id(annotation))

    return annos_to_render


def get_annotation_date_render_function(annotations, avoptions):
    timestamps = list(
        itertools.chain.from_iterable([(a[1]["from"], a[1]["until"]) for a in annotations] +
                                      [avoptions["range"][0]]))

    multi_day = len({time.localtime(t)[:3] for t in timestamps}) > 1
    if multi_day:
        return cmk.utils.render.date_and_time
    return cmk.utils.render.time_of_day


def _annotation_affects_time_range(annotation_from, annotation_until, from_time, until_time):
    return not (annotation_until < from_time or annotation_from > until_time)


def show_annotations(annotations, av_rawdata, what, avoptions, omit_service):
    annos_to_render = get_relevant_annotations(annotations, av_rawdata, what, avoptions)
    render_date = get_annotation_date_render_function(annos_to_render, avoptions)

    with table_element(title=_("Annotations"), omit_if_empty=True) as table:
        for (site_id, host, service), annotation in annos_to_render:
            table.row()
            table.cell("", css="buttons")
            anno_vars = [
                ("anno_site", site_id),
                ("anno_host", host),
                ("anno_service", service or ""),
                ("anno_from", int(annotation["from"])),
                ("anno_until", int(annotation["until"])),
            ]
            edit_url = makeuri(request, anno_vars)
            html.icon_button(edit_url, _("Edit this annotation"), "edit")
            del_anno: 'HTTPVariables' = [("_delete_annotation", "1")]
            delete_url = make_confirm_link(
                url=html.makeactionuri(del_anno + anno_vars),
                message=_("Are you sure that you want to delete this annotation?"),
            )
            html.icon_button(delete_url, _("Delete this annotation"), "delete")

            if not omit_service:
                if "omit_host" not in avoptions["labelling"]:
                    host_url = "view.py?" + html.urlencode_vars([("view_name", "hoststatus"),
                                                                 ("site", site_id), ("host", host)])
                    table.cell(_("Host"), html.render_a(host, host_url))

                if what == "service":
                    if service:
                        service_url = "view.py?" + html.urlencode_vars([("view_name", "service"),
                                                                        ("site", site_id),
                                                                        ("host", host),
                                                                        ("service", service)])
                        # TODO: honor use_display_name. But we have no display names here...
                        service_name = service
                        table.cell(_("Service"), html.render_a(service_name, service_url))
                    else:
                        table.cell(_("Service"), "")  # Host annotation in service table

            table.cell(_("From"), render_date(annotation["from"]), css="nobr narrow")
            table.cell(_("Until"), render_date(annotation["until"]), css="nobr narrow")
            table.cell("", css="buttons")
            if annotation.get("downtime") is True:
                html.icon("downtime",
                          _("This period has been reclassified as a scheduled downtime"))
            elif annotation.get("downtime") is False:
                html.icon(
                    "nodowntime",
                    _("This period has been reclassified as a not being a scheduled downtime"))
            recl_host_state = annotation.get("host_state")
            if recl_host_state is not None:
                html.icon(
                    "status",
                    _("This period has been reclassified in host state to state: %s" %
                      host_state_name(recl_host_state)))
            recl_svc_state = annotation.get("service_state")
            if recl_svc_state is not None:
                html.icon(
                    "status",
                    _("This period has been reclassified in service state to state: %s" %
                      service_state_name(recl_svc_state)))

            table.cell(_("Annotation"), html.render_text(annotation["text"]))
            table.cell(_("Author"), annotation["author"])
            table.cell(_("Entry"), render_date(annotation["date"]), css="nobr narrow")
            if not cmk_version.is_raw_edition():
                table.cell(_("Hide in report"),
                           _("Yes") if annotation.get("hide_from_report") else _("No"))


def edit_annotation(breadcrumb: Breadcrumb) -> bool:
    site_id, hostname, host_state, service, service_state, fromtime, \
            untiltime, site_host_svc = _handle_anno_request_vars()

    # Find existing annotation with this specification
    annotations = availability.load_annotations()
    annotation = availability.find_annotation(annotations, site_host_svc, host_state, service_state,
                                              fromtime, untiltime)

    if annotation:
        value = annotation.copy()
        value.setdefault("host_state", None)
        value.setdefault("service_state", None)
    else:
        value = {
            "host_state": None,
            "service_state": None,
            "from": fromtime,
            "until": untiltime,
            "text": "",
        }

    value["host"] = hostname
    value["service"] = service
    value["site"] = site_id

    if html.check_transaction():
        try:
            vs = _vs_annotation()
            value = vs.from_html_vars("_editanno")
            vs.validate_value(value, "_editanno")

            site_host_svc = (value["site"], value["host"], value["service"])
            del value["site"]
            del value["host"]
            value["date"] = time.time()
            value["author"] = config.user.id
            availability.update_annotations(site_host_svc, value, replace_existing=annotation)
            html.request.del_var("filled_in")
            return False
        except MKUserError as e:
            html.user_error(e)

    title = _("Edit annotation of ") + hostname
    if service:
        title += "/" + service

    html.body_start(title)

    breadcrumb = _edit_annotation_breadcrumb(breadcrumb, title)
    html.top_heading(title, breadcrumb, _edit_annotation_page_menu(breadcrumb))

    html.begin_form("editanno", method="GET")
    _vs_annotation().render_input_as_form("_editanno", value)
    html.hidden_fields()
    html.end_form()

    html.bottom_footer()
    html.body_end()
    return True


def _edit_annotation_breadcrumb(breadcrumb: Breadcrumb, title: str) -> Breadcrumb:
    breadcrumb.append(BreadcrumbItem(
        title=title,
        url=makeuri(request, []),
    ))
    return breadcrumb


def _edit_annotation_page_menu(breadcrumb: Breadcrumb) -> PageMenu:
    return make_simple_form_page_menu(breadcrumb, form_name="editanno", button_name="save")


def _validate_reclassify_of_states(value, varprefix):
    host_state = value.get("host_state")
    if host_state is not None:
        if not value.get("host"):
            raise MKUserError("_editanno_p_host",
                              _('Please set a hostname for host state reclassification'))

    service_state = value.get("service_state")
    if service_state is not None:
        if not value.get("service"):
            raise MKUserError(
                "_editanno_p_service_value",
                _('Please set a service description for service state reclassification'))


def _vs_annotation():
    extra_elements: List[Tuple[str, ValueSpec]] = []
    if not cmk_version.is_raw_edition():
        extra_elements.append(("hide_from_report", Checkbox(title=_("Hide annotation in report"))))

    return Dictionary(
        elements=[
            ("site", TextAscii(title=_("Site"))),
            ("host", TextUnicode(title=_("Hostname"))),
            ("host_state",
             Optional(
                 HostState(),
                 sameline=True,
                 title=_("Host state"),
                 label=_("Reclassify host state of this period"),
             )),
            ("service",
             Optional(TextUnicode(allow_empty=False),
                      sameline=True,
                      title=_("Service"),
                      label=_("Service description"))),
            ("service_state",
             Optional(
                 MonitoringState(),
                 sameline=True,
                 title=_("Service state"),
                 label=_("Reclassify service state of this period"),
             )),
            ("from", AbsoluteDate(title=_("Start-Time"), include_time=True)),
            ("until", AbsoluteDate(title=_("End-Time"), include_time=True)),
            ("downtime",
             Optional(
                 DropdownChoice(choices=[
                     (True, _("regard as scheduled downtime")),
                     (False, _("do not regard as scheduled downtime")),
                 ],),
                 title=_("Scheduled downtime"),
                 label=_("Reclassify downtime of this period"),
             )),
            ("text", TextAreaUnicode(title=_("Annotation"), allow_empty=False)),
        ] + extra_elements,
        title=_("Edit annotation"),
        optional_keys=[],
        validate=_validate_reclassify_of_states,
    )


# Called at the beginning of every availability page
def handle_delete_annotations():
    if html.request.var("_delete_annotation"):
        _site_id, _hostname, _service, host_state, service_state, fromtime, \
                untiltime, site_host_svc = _handle_anno_request_vars()

        annotations = availability.load_annotations()
        annotation = availability.find_annotation(annotations, site_host_svc, host_state,
                                                  service_state, fromtime, untiltime)
        if not annotation:
            return

        availability.delete_annotation(annotations, site_host_svc, host_state, service_state,
                                       fromtime, untiltime)
        availability.save_annotations(annotations)


def handle_edit_annotations(breadcrumb: Breadcrumb) -> bool:
    # Avoid reshowing edit form after edit and reload
    if html.is_transaction() and not html.transaction_valid():
        return False
    if html.request.var("anno_host") and not html.request.var("_delete_annotation"):
        finished = edit_annotation(breadcrumb)
    else:
        finished = False

    return finished


def _handle_anno_request_vars():
    site_id = html.request.var("anno_site") or ""
    hostname = html.request.get_str_input_mandatory("anno_host")
    host_state = html.request.var("anno_host_state") or None
    service = html.request.var("anno_service") or None
    service_state = html.request.var("anno_service_state") or None
    fromtime = html.request.get_float_input_mandatory("anno_from")
    untiltime = html.request.get_float_input_mandatory("anno_until")

    site_host_svc = (site_id, hostname, service)

    return site_id, hostname, host_state, service, service_state, fromtime, \
            untiltime, site_host_svc


#.
#   .--CSV Export----------------------------------------------------------.
#   |         ____ ______     __  _____                       _            |
#   |        / ___/ ___\ \   / / | ____|_  ___ __   ___  _ __| |_          |
#   |       | |   \___ \\ \ / /  |  _| \ \/ / '_ \ / _ \| '__| __|         |
#   |       | |___ ___) |\ V /   | |___ >  <| |_) | (_) | |  | |_          |
#   |        \____|____/  \_/    |_____/_/\_\ .__/ \___/|_|   \__|         |
#   |                                       |_|                            |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


def _output_csv(what: AVObjectType, av_mode: AVMode, av_data: AVData, avoptions: AVOptions) -> None:
    if av_mode == "availability":
        _output_availability_csv(what, av_data, avoptions)
    elif av_mode == "timeline":
        _output_availability_timelines_csv(what, av_data, avoptions)
    else:
        raise NotImplementedError("Unhandled availability mode: %r" % av_mode)


def _output_availability_timelines_csv(what: AVObjectType, av_data: AVData,
                                       avoptions: AVOptions) -> None:
    _av_output_set_content_disposition("Checkmk-Availability-Timeline")
    for timeline_nr, av_entry in enumerate(av_data):
        _output_availability_timeline_csv(what, av_entry, avoptions, timeline_nr)


def _output_availability_timeline_csv(what: AVObjectType, av_entry: AVEntry, avoptions: AVOptions,
                                      timeline_nr: int) -> None:
    timeline_layout = availability.layout_timeline(
        what,
        av_entry["timeline"],
        av_entry["considered_duration"],
        avoptions,
        "standalone",
    )

    object_cells = availability.get_object_cells(what, av_entry, avoptions["labelling"])

    with table_element("av_timeline", "", output_format="csv",
                       omit_headers=timeline_nr != 0) as table:
        for row in timeline_layout["table"]:
            table.row()

            table.text_cell("object_type", what)
            for cell_index, objectcell in enumerate(object_cells):
                table.text_cell("object_name_%d" % cell_index, objectcell[0])

            table.text_cell("object_title", availability.object_title(what, av_entry))
            table.text_cell("from", row["from"])
            table.text_cell("from_text", row["from_text"])
            table.text_cell("until", row["until"])
            table.text_cell("until_text", row["until_text"])
            table.text_cell("state", row["state"])
            table.text_cell("state_name", row["state_name"])
            table.text_cell("duration_text", row["duration_text"])

            if "omit_timeline_plugin_output" not in avoptions["labelling"]:
                table.text_cell("log_output", row.get("log_output", ""))

            if "timeline_long_output" in avoptions["labelling"]:
                table.text_cell("long_log_output", row.get("long_log_output", ""))


def _output_availability_csv(what: AVObjectType, av_data: AVData, avoptions: AVOptions) -> None:
    def cells_from_row(table: Table, group_titles: List[str], group_cells: List[str],
                       object_titles: List[str], cell_titles: List[Tuple[str, str]],
                       row_object: AVObjectCells, row_cells: AVRowCells) -> None:
        for column_title, group_title in zip(group_titles, group_cells):
            table.cell(column_title, group_title)

        for title, (name, _url) in zip(object_titles, row_object):
            table.cell(title, name)

        for (title, _help), (text, _css) in zip(cell_titles, row_cells):
            table.cell(title, text)

    _av_output_set_content_disposition("Checkmk-Availability")
    availability_tables = availability.compute_availability_groups(what, av_data, avoptions)
    with table_element("av_items", output_format="csv") as table:
        for group_title, availability_table in availability_tables:
            av_table = availability.layout_availability_table(what, group_title, availability_table,
                                                              avoptions)
            pad = 0

            if group_title:
                group_titles, group_cells = [_("Group")], [group_title]
            else:
                group_titles, group_cells = [], []

            for row in av_table["rows"]:
                table.row()
                cells_from_row(
                    table,
                    group_titles,
                    group_cells,
                    av_table["object_titles"],
                    av_table["cell_titles"],
                    row["object"],
                    row["cells"],
                )
                # presumably all rows have the same width
                pad = len(row["object"]) - 1
            table.row()

            if "summary" in av_table:
                row_object: AVObjectCells = [(_("Summary"), "")]
                row_object += [(u"", "")] * pad
                cells_from_row(
                    table,
                    group_titles,
                    group_cells,
                    av_table["object_titles"],
                    av_table["cell_titles"],
                    row_object,
                    av_table["summary"],
                )


def _av_output_set_content_disposition(title: str) -> None:
    filename = '%s-%s.csv' % (
        title,
        time.strftime('%Y-%m-%d_%H-%M-%S', time.localtime(time.time())),
    )
    html.response.headers["Content-Disposition"] = "Attachment; filename=\"%s\"" % filename
