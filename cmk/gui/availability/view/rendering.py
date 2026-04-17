#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import time
from collections.abc import Iterator

import cmk.ccc.version as cmk_version
from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.gui import availability
from cmk.gui.availability import (
    AVData,
    AVEntry,
    AVGroups,
    AVLayoutTimeline,
    AVMode,
    AVObjectSpec,
    AVObjectType,
    AVOptions,
    AVOptionValueSpecs,
    AVRawData,
    AVTimelineStyle,
    AVTimeRange,
)
from cmk.gui.bi.foldable_tree_renderer import (
    FoldableTreeRendererTree,
)
from cmk.gui.breadcrumb import Breadcrumb, BreadcrumbItem
from cmk.gui.config import active_config
from cmk.gui.display_options import display_options
from cmk.gui.exceptions import MKUserError
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.page_menu import (
    make_external_link,
    make_simple_link,
    PageMenu,
    PageMenuDropdown,
    PageMenuEntry,
    PageMenuSidePopup,
    PageMenuTopic,
)
from cmk.gui.painter.v0.helpers import format_plugin_output
from cmk.gui.table import table_element
from cmk.gui.top_heading import top_heading
from cmk.gui.type_defs import FilterHeader, IconNames, Rows, StaticIcon
from cmk.gui.utils import escaping
from cmk.gui.utils.html import HTML
from cmk.gui.utils.output_funnel import output_funnel
from cmk.gui.utils.urls import makeuri
from cmk.gui.utils.user_errors import user_errors
from cmk.gui.valuespec import ValueSpec
from cmk.gui.view import View
from cmk.gui.visuals import page_menu_topic_add_to, view_title
from cmk.utils import paths
from cmk.utils.servicename import ServiceName

from .annotations import _handle_edit_annotations, handle_delete_annotations, show_annotations
from .csv import _output_csv

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


def _save_availability_options_after_update(avoptions: AVOptions) -> None:
    if html.form_submitted():
        user.save_file("avoptions", avoptions)


def _handle_availability_option_reset() -> None:
    if request.var("_reset"):
        user.save_file("avoptions", {})
        request.del_vars("avo_")
        request.del_var("avoptions")


def _show_availability_options(
    option_type: str, what: AVObjectType, avoptions: AVOptions, valuespecs: AVOptionValueSpecs
) -> None:
    form_name = "avoptions_%s" % option_type
    with html.form_context(form_name):
        html.hidden_field("avoptions", "set")

        _show_availability_options_controls()

        container_id = "av_options_%s" % option_type
        html.open_div(id_=container_id, class_="side_popup_content")
        if user_errors and html.form_submitted(form_name):
            html.show_user_errors()

        for name, height, _show_in_reporting, vs in valuespecs:

            def renderer(
                name: str = name, vs: ValueSpec[object] = vs, avoptions: AVOptions = avoptions
            ) -> None:
                vs.render_input("avo_" + name, avoptions.get(name))

            html.render_floating_option(name, height, vs.title(), renderer)
        html.close_div()

        html.hidden_fields()


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


# .
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
def show_availability_page(
    view: View,
    filterheaders: FilterHeader,
    *,
    debug: bool,
) -> None:
    user.need_permission("general.see_availability")

    # We make reports about hosts, services or BI aggregates
    what: AVObjectType
    if "service" in view.datasource.infos:
        what = "service"
    elif "aggr_name" in view.datasource.infos:
        what = "bi"
    else:
        what = "host"

    _handle_availability_option_reset()
    avoptions = availability.get_availability_options_from_request(what)
    _save_availability_options_after_update(avoptions)
    time_range: AVTimeRange = avoptions["range"][0]
    range_title: str = avoptions["range"][1]

    # We have two display modes:
    # - Show availability table (stats) "availability"
    # - Show timeline                   "timeline"
    # --> controlled by URL variable "av_mode"
    av_mode = request.get_ascii_input_mandatory("av_mode", "availability")

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
    if request.var("av_host"):
        av_object = (
            SiteId(request.get_str_input_mandatory("av_site")),
            request.get_validated_type_input_mandatory(HostName, "av_host"),
            ServiceName(request.get_str_input_mandatory("av_service")),
        )
        title += av_object[1]
        if av_object[2]:
            title += " - " + av_object[2]
    elif request.var("av_aggr"):
        av_object = (None, None, request.get_str_input_mandatory("av_aggr"))
        title += av_object[2]
    else:
        title += view_title(view.spec, view.context)

    title += " - " + range_title

    breadcrumb = view.breadcrumb()
    assert breadcrumb[-1].url is not None
    breadcrumb.append(
        BreadcrumbItem(
            title=title,
            url=breadcrumb[-1].url + "&mode=availability",
        )
    )

    if _handle_edit_annotations(breadcrumb, debug=debug):
        return

    # Deletion must take place before computation, since it affects the outcome
    with output_funnel.plugged():
        handle_delete_annotations()
        confirmation_html_code = HTML.without_escaping(output_funnel.drain())

    # Remove variables for editing annotations, otherwise they will make it into the uris
    request.del_vars("anno_")
    if request.var("filled_in") == "editanno":
        request.del_var("filled_in")
    # Re-read the avoptions again, because the HTML vars have changed above (anno_ and editanno_ has
    # been removed, which must not be part of the form
    avoptions = availability.get_availability_options_from_request(what)
    _save_availability_options_after_update(avoptions)

    # Now compute all data, we need this also for CSV export
    av_rawdata: AVRawData = {}
    av_data: AVData = []
    has_reached_logrow_limit: bool = False
    if not user_errors:
        include_long_output = (
            av_mode == "timeline" and "timeline_long_output" in avoptions["labelling"]
        )
        av_rawdata, has_reached_logrow_limit = availability.get_availability_rawdata(
            what,
            view.context,
            filterheaders,
            view.only_sites,
            av_object=av_object,
            include_output=av_mode == "timeline",
            include_long_output=include_long_output,
            avoptions=avoptions,
            view_process_tracking=view.process_tracking,
        )
        av_data = availability.compute_availability(what, av_rawdata, avoptions)

    # Do CSV ouput
    if html.output_format == "csv_export" and user.may("general.csv_export"):
        _output_csv(what, av_mode, av_data, avoptions)
        return

    if display_options.enabled(display_options.H):
        html.body_start(
            title,
            force=True,
            lang=user.language,
            inject_js_profiling_code=active_config.inject_js_profiling_code,
            load_frontend_vue=active_config.load_frontend_vue,
            custom_style_sheet=active_config.custom_style_sheet,
            screenshotmode=active_config.screenshotmode,
            inline_help_as_text=user.inline_help_as_text,
        )

    if display_options.enabled(display_options.T):
        top_heading(
            html,
            request,
            title,
            breadcrumb,
            page_menu=(
                _page_menu_availability(
                    breadcrumb, view, what, av_mode, av_object, time_range, avoptions
                )
                if display_options.enabled(display_options.B)
                else None
            ),
            browser_reload=html.browser_reload,
            debug=debug,
            hide_suggestions=not user.get_tree_state("suggestions", "all", True),
            user_role_ids=user.role_ids,
        )
        html.begin_page_content()

    if user_errors:
        form_name = request.get_ascii_input_mandatory("filled_in")
        if form_name in ("avoptions_display", "avoptions_computation"):
            html.final_javascript(
                "cmk.page_menu.open_popup(%s);" % json.dumps("popup_" + form_name)
            )

    missing_single_infos = view.missing_single_infos
    if missing_single_infos:
        raise MKUserError(
            None,
            _(
                "Unable to render this availability view, because we miss some required context "
                "information (%s). Please update the filters on the source view or add the "
                "missing HTTP request variables to your request"
            )
            % ", ".join(sorted(missing_single_infos)),
        )

    html.write_html(confirmation_html_code)

    if not user_errors:
        # If we abolish the limit we have to fetch the data again
        # with changed logrow_limit = 0, which means no limit
        if has_reached_logrow_limit:
            text = escaping.escape_to_html_permissive(
                _(
                    "Your query matched more than %d log entries. "
                    "<b>Note:</b> The number of shown rows does not necessarily reflect the "
                    "matched entries and the result might be incomplete. "
                )
                % avoptions["logrow_limit"]
            )
            text += HTMLWriter.render_a(
                _("Repeat query without limit."),
                makeuri(request, [("_unset_logrow_limit", "1"), ("avo_logrow_limit", 0)]),
            )
            html.show_warning(text)
        do_render_availability(what, av_rawdata, av_data, av_mode, av_object, avoptions)

    if display_options.enabled(display_options.T):
        html.end_page_content()

    if display_options.enabled(display_options.H):
        html.body_end()


def _page_menu_availability(
    breadcrumb: Breadcrumb,
    view: View,
    what: AVObjectType,
    av_mode: AVMode,
    av_object: AVObjectSpec,
    time_range: AVTimeRange,
    avoptions: AVOptions,
) -> PageMenu:
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
                                icon_name=StaticIcon(IconNames.painteroptions),
                                item=PageMenuSidePopup(
                                    _render_avoptions_form(
                                        "display",
                                        what,
                                        avoptions,
                                        availability.get_av_display_options(what),
                                    ),
                                ),
                                name="avoptions_display",
                            ),
                            PageMenuEntry(
                                title=_("Change computation options"),
                                icon_name=StaticIcon(IconNames.av_computation),
                                item=PageMenuSidePopup(
                                    _render_avoptions_form(
                                        "computation",
                                        what,
                                        avoptions,
                                        availability.get_av_computation_options(),
                                    ),
                                ),
                                name="avoptions_computation",
                            ),
                        ],
                    ),
                    PageMenuTopic(
                        title=_("Display mode"),
                        entries=list(
                            _page_menu_entries_av_mode(what, av_mode, av_object, time_range)
                        ),
                    ),
                ],
            )
        ]
        + [
            PageMenuDropdown(
                name="export",
                title=_("Export"),
                topics=page_menu_topic_add_to(
                    visual_type="availability", name=view.name, source_type="availability"
                )
                + [
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


def _render_avoptions_form(
    option_type: str, what: AVObjectType, avoptions: AVOptions, valuespecs: AVOptionValueSpecs
) -> HTML:
    with output_funnel.plugged():
        _show_availability_options(option_type, what, avoptions, valuespecs)
        return HTML.without_escaping(output_funnel.drain())


def _page_menu_entries_av_mode(
    what: AVObjectType, av_mode: AVMode, av_object: AVObjectSpec, time_range: AVTimeRange
) -> Iterator[PageMenuEntry]:
    if av_mode == "timeline" or av_object:
        yield PageMenuEntry(
            title=_("Table"),
            icon_name=StaticIcon(IconNames.availability),
            item=make_simple_link(
                makeuri(request, [("av_mode", "availability")], delvars=["av_host", "av_aggr"])
            ),
            is_shortcut=True,
            shortcut_title=_("View table"),
        )
        return

    if what != "bi":
        yield PageMenuEntry(
            title=_("Timeline"),
            icon_name=StaticIcon(IconNames.timeline),
            item=make_simple_link(makeuri(request, [("av_mode", "timeline")])),
            is_shortcut=True,
            shortcut_title=_("View timeline"),
        )
        return


def _page_menu_entries_export_data() -> Iterator[PageMenuEntry]:
    if not user.may("general.csv_export"):
        return

    yield PageMenuEntry(
        title=_("Export CSV"),
        icon_name=StaticIcon(IconNames.download_csv),
        item=make_simple_link(makeuri(request, [("output_format", "csv_export")])),
    )


def _page_menu_entries_export_reporting() -> Iterator[PageMenuEntry]:
    if cmk_version.edition(paths.omd_root) is cmk_version.Edition.COMMUNITY:
        return

    if not user.may("general.reporting") or not user.may("general.instant_reports"):
        return

    yield PageMenuEntry(
        title=_("This view as PDF"),
        icon_name=StaticIcon(IconNames.report),
        item=make_external_link(makeuri(request, [], filename="report_instant.py")),
    )


def do_render_availability(
    what: AVObjectType,
    av_rawdata: AVRawData,
    av_data: AVData,
    av_mode: AVMode,
    av_object: AVObjectSpec,
    avoptions: AVOptions,
) -> None:
    availability_tables = availability.compute_availability_groups(what, av_data, avoptions)
    if av_mode == "timeline":
        render_availability_timelines(what, availability_tables, avoptions)
    else:
        render_availability_tables(availability_tables, what, avoptions)

    annotations = availability.load_annotations()
    show_annotations(annotations, av_rawdata, what, avoptions, omit_service=av_object is not None)


def render_availability_tables(
    availability_tables: AVGroups, what: AVObjectType, avoptions: AVOptions
) -> None:
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

        html.div(HTMLWriter.render_span(_("OK")), class_="state state0")
        html.div("> %.3f%%" % warn, class_="level")
        html.div(HTMLWriter.render_span(_("WARN")), class_="state state1")
        html.div("> %.3f%%" % crit, class_="level")
        html.div(HTMLWriter.render_span(_("CRIT")), class_="state state2")
        html.div("< %.3f%%" % crit, class_="level")

        html.close_div()

    # Legend for timeline
    if "display_timeline_legend" in avoptions["labelling"] and avoptions["show_timeline"]:
        render_timeline_legend(what)


def render_availability_timelines(
    what: AVObjectType, av_groups: AVGroups, avoptions: AVOptions
) -> None:
    for group_title, av_data in av_groups:
        for timeline_nr, av_entry in enumerate(av_data):
            _render_availability_timeline(what, av_entry, avoptions, timeline_nr)


def _render_availability_timeline(
    what: AVObjectType, av_entry: AVEntry, avoptions: AVOptions, timeline_nr: int
) -> None:
    html.h3(_("Timeline of %s") % availability.object_title(what, av_entry))

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
    with table_element(
        "av_timeline",
        "",
        css="timelineevents",
        sortable=False,
        searchable=False,
        limit=active_config.table_row_limit,
    ) as table:
        for row_nr, row in enumerate(timeline_layout["table"]):
            table.row(
                id_="timetable_%d_entry_%d" % (timeline_nr, row_nr),
                onmouseover="cmk.availability.timetable_hover(%d, %d, 1);" % (timeline_nr, row_nr),
                onmouseout="cmk.availability.timetable_hover(%d, %d, 0);" % (timeline_nr, row_nr),
            )

            table.cell(_("Links"), css=["buttons"])
            if what == "bi":
                url = makeuri(request, [("timewarp", str(int(row["from"])))])
                if request.var("timewarp") and request.get_integer_input_mandatory(
                    "timewarp"
                ) == int(row["from"]):
                    html.disabled_icon_button(StaticIcon(IconNames.timewarp_off))
                else:
                    html.icon_button(
                        url,
                        _("Time warp - show BI aggregate during this time period"),
                        StaticIcon(IconNames.timewarp),
                    )
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
                html.icon_button(
                    url, _("Create an annotation for this period"), StaticIcon(IconNames.annotation)
                )

            table.cell(_("From"), row["from_text"], css=["nobr narrow"])
            table.cell(_("Until"), row["until_text"], css=["nobr narrow"])
            table.cell(_("Duration"), row["duration_text"], css=["narrow number"])
            table.cell(
                _("State"),
                HTMLWriter.render_span(row["state_name"], class_=["state_rounded_fill"]),
                css=row["css"] + " state narrow",
            )

            if "omit_timeline_plugin_output" not in avoptions["labelling"]:
                table.cell(
                    _("Summary at last status change"),
                    format_plugin_output(row.get("log_output", ""), request=request, row=row),
                )

            if "timeline_long_output" in avoptions["labelling"]:
                table.cell(
                    _("Last known details"),
                    format_plugin_output(row.get("long_log_output", ""), request=request, row=row),
                )

    # Legend for timeline
    if "display_timeline_legend" in avoptions["labelling"]:
        render_timeline_legend(what)


def render_timeline_legend(what: AVObjectType) -> None:
    html.open_div(class_="avlegend timeline")

    html.h3(_("Timeline colors"))
    html.div(HTMLWriter.render_span(_("UP") if what == "host" else _("OK")), class_="state state0")

    if what != "host":
        html.div(HTMLWriter.render_span(_("WARN")), class_="state state1")

    html.div(
        HTMLWriter.render_span(_("DOWN") if what == "host" else _("CRIT")), class_="state state2"
    )
    html.div(
        HTMLWriter.render_span(_("UNREACH") if what == "host" else _("UNKNOWN")),
        class_="state state3",
    )
    html.div(HTMLWriter.render_span(_("Flapping")), class_="state flapping")

    if what != "host":
        html.div(HTMLWriter.render_span(_("H.Down")), class_="state hostdown")

    html.div(HTMLWriter.render_span(_("Downtime")), class_="state downtime")
    html.div(HTMLWriter.render_span(_("Chaotic")), class_="state chaos")
    html.div(HTMLWriter.render_span(_("OO/Service")), class_="state ooservice")
    html.div(HTMLWriter.render_span(_("unmonitored")), class_="state unmonitored")

    html.close_div()


def render_availability_table(
    group_title: str | None, availability_table: AVData, what: AVObjectType, avoptions: AVOptions
) -> None:
    av_table = availability.layout_availability_table(
        what, group_title, availability_table, avoptions
    )

    # TODO: If summary line is activated, then sorting should now move that line to the
    # top. It should also stay at the bottom. This would require an extension to the
    # table.py module.
    with table_element(
        "av_items",
        av_table["title"],
        css="availability",
        searchable=False,
        omit_headers="omit_headers" in avoptions["labelling"],
        limit=0,
    ) as table:
        show_urls, show_timeline = False, False
        for row in av_table["rows"]:
            table.row()

            # Column with icons
            timeline_url = None
            if row["urls"]:
                show_urls = True
                table.cell("", css=["buttons"])
                for image, tooltip, url in row["urls"]:
                    html.icon_button(url, tooltip, image)
                    if image == "timeline":
                        timeline_url = url

            # Column with host/service or aggregate name
            for title, (name, url) in zip(av_table["object_titles"], row["object"]):
                table.cell(title, HTMLWriter.render_a(name, url))

            if "timeline" in row:
                show_timeline = True
                table.cell(_("Timeline"), css=["timeline"])
                html.open_a(href=timeline_url)
                render_timeline_bar(row["timeline"], "inline")
                html.close_a()

            # Columns with the actual availability data
            for (title, help_txt), (text, css) in zip(av_table["cell_titles"], row["cells"]):
                table.cell(title, HTMLWriter.render_span(text), css=css, help_txt=help_txt)

        if "summary" in av_table:
            table.row(css=["summary"], fixed=True)
            if show_urls:
                table.cell("", "")  # Empty cell in URLs column
            table.cell("", _("Summary"), css=["heading"])
            for _x in range(1, len(av_table["object_titles"])):
                table.cell("", "")  # empty cells, of more object titles than one
            if show_timeline:
                table.cell("", "")

            for (title, help_txt), (text, css) in zip(av_table["cell_titles"], av_table["summary"]):
                table.cell(
                    title, HTMLWriter.render_span(text), css="heading " + css, help_txt=help_txt
                )


def render_timeline_bar(
    timeline_layout: AVLayoutTimeline, style: AVTimelineStyle, timeline_nr: int = 0
) -> None:
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
            html.div("", title=title, class_="timelinechoord", style="left: %dpx" % pixel)

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
                td_attrs.update(
                    {
                        "onmouseover": "cmk.availability.timeline_hover(%d, %d, 1);"
                        % (timeline_nr, row_nr),
                        "onmouseout": "cmk.availability.timeline_hover(%d, %d, 0);"
                        % (timeline_nr, row_nr),
                    }
                )

        html.td("", **td_attrs)

    html.close_tr()
    html.close_table()

    html.close_div()


# .
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


# Render availability of a BI aggregate. This is currently
# no view and does not support display options
# TODO: Why should we handle this in a special way? Probably because we cannot
# get the list of BI aggregates from the statehist table but use the views
# logic for getting the aggregates. As soon as we have cleaned of the visuals,
# filters, contexts etc we can unify the code!
def show_bi_availability(
    view: View,
    aggr_rows: Rows,
    *,
    debug: bool,
) -> None:
    user.need_permission("general.see_availability")

    av_mode = request.get_ascii_input_mandatory("av_mode", "availability")

    _handle_availability_option_reset()
    avoptions = availability.get_availability_options_from_request("bi")
    _save_availability_options_after_update(avoptions)

    title = view_title(view.spec, view.context)
    if av_mode == "timeline":
        title = _("Timeline of") + " " + title
    else:
        title = _("Availability of") + " " + title

    if html.output_format != "csv_export":
        html.body_start(
            title,
            lang=user.language,
            inject_js_profiling_code=active_config.inject_js_profiling_code,
            load_frontend_vue=active_config.load_frontend_vue,
            custom_style_sheet=active_config.custom_style_sheet,
            screenshotmode=active_config.screenshotmode,
            inline_help_as_text=user.inline_help_as_text,
        )

        breadcrumb = view.breadcrumb()
        assert breadcrumb[-1].url is not None
        breadcrumb.append(
            BreadcrumbItem(
                title=title,
                url=breadcrumb[-1].url + "&mode=availability",
            )
        )

        av_object: AVObjectSpec = None
        if request.var("av_aggr"):
            av_object = (None, None, request.get_str_input_mandatory("av_aggr"))

        # Dummy time_range, this is not needed for the BI
        page_menu = _page_menu_availability(
            breadcrumb, view, "bi", av_mode, av_object, (0.0, 0.0), avoptions
        )

        # This hack is needed because of some BI specific link. May be generalized in the future
        if av_mode != "timeline" and len(aggr_rows) == 1:
            dropdown = page_menu.get_dropdown_by_name(
                "availability",
                deflt=PageMenuDropdown(name="availability", title=_("Availability"), topics=[]),
            )
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
                    icon_name=StaticIcon(IconNames.timeline),
                    item=make_simple_link(timeline_url),
                    is_shortcut=True,
                    shortcut_title=_("View timeline"),
                )
            )

        top_heading(
            html,
            request,
            title,
            breadcrumb,
            page_menu,
            browser_reload=html.browser_reload,
            debug=debug,
            hide_suggestions=not user.get_tree_state("suggestions", "all", True),
            user_role_ids=user.role_ids,
        )

        avoptions = availability.get_availability_options_from_request("bi")
        _save_availability_options_after_update(avoptions)

    if not user_errors:
        # iterate all aggregation rows
        timewarpcode = HTML.empty()
        timewarp = request.get_integer_input("timewarp")

        # The timewarp is used to display an aggregation at a specific timestamp
        # This rarely works with timestamps bordering the range specified in avoptions["range"],
        # Most of the time, timewarp timestamps are dynamic (last x-hours), whereas
        # the timewarp timestamp is an explict timestamp from the previous page rendering
        # We fix this by restricting the value to the available range
        if timewarp is not None:
            from_time, until_time = avoptions["range"][0]
            timewarp = int(min(until_time, max(from_time, timewarp)))

        (
            timeline_containers,
            av_rawdata,
            has_reached_logrow_limit,
        ) = availability.get_bi_availability(avoptions, aggr_rows, timewarp)
        view.process_tracking.amount_rows_after_limit = len(av_rawdata)

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
                    "aggr_group": request.var("aggr_group"),
                }

                renderer = FoldableTreeRendererTree(
                    row,
                    omit_root=False,
                    expansion_level=user.bi_expansion_level,
                    only_diff=False,
                    only_problems=False,
                    lazy=False,
                )
                tdclass, htmlcode = renderer.css_class(), renderer.render()

                with output_funnel.plugged():
                    # TODO: SOMETHING IS WRONG IN HERE (used to be the same situation in original code!)
                    # FIXME: WHAT is wrong in here??

                    html.open_h3()
                    # render icons for back and forth
                    button_back_shown = False
                    button_forth_shown = False
                    if int(these_spans[0]["from"]) == timewarp:
                        html.disabled_icon_button(StaticIcon(IconNames.back_off))
                        button_back_shown = True

                    previous_span = None
                    for span in these_spans:
                        if (
                            not button_back_shown
                            and int(span["from"]) == timewarp
                            and previous_span is not None
                        ):
                            html.icon_button(
                                makeuri(request, [("timewarp", str(int(previous_span["from"])))]),
                                _("Jump one phase back"),
                                StaticIcon(IconNames.back),
                            )
                            button_back_shown = True
                        # Multiple followup spans can have the same "from" time
                        # We only show one forth-arrow with an actual time difference
                        elif (
                            not button_forth_shown
                            and previous_span
                            and int(previous_span["from"]) == timewarp
                            and int(span["from"]) != timewarp
                        ):
                            html.icon_button(
                                makeuri(
                                    request,
                                    [("timewarp", str(int(span["from"])))],
                                ),
                                _("Jump one phase forth"),
                                StaticIcon(IconNames.forth),
                            )
                            button_forth_shown = True
                        previous_span = span
                    if not button_forth_shown:
                        html.disabled_icon_button(StaticIcon(IconNames.forth_off))

                    html.write_text_permissive(" &nbsp; ")
                    html.icon_button(
                        makeuri(request, [], delvars=["timewarp"]),
                        _("Close timewarp"),
                        StaticIcon(IconNames.closetimewarp),
                    )
                    html.write_text_permissive(
                        "%s %s"
                        % (
                            _("Timewarp to "),
                            time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timewarp)),
                        )
                    )
                    html.close_h3()

                    html.open_table(class_=["data", "table", "timewarp"])
                    html.open_tr(class_=["data", "odd0"])
                    html.open_td(class_=tdclass)
                    html.write_html(htmlcode)
                    html.close_td()
                    html.close_tr()
                    html.close_table()

                    timewarpcode += HTML.without_escaping(output_funnel.drain())

        av_data = availability.compute_availability("bi", av_rawdata, avoptions)

        # If we abolish the limit we have to fetch the data again
        # with changed logrow_limit = 0, which means no limit
        if has_reached_logrow_limit:
            text = (
                _(
                    "Your query matched more than %d log entries. "
                    "<b>Note:</b> The shown data does not necessarily reflect the "
                    "matched entries and the result might be incomplete. "
                )
                % avoptions["logrow_limit"]
            )
            text += HTMLWriter.render_a(
                _("Repeat query without limit."), makeuri(request, [("_unset_logrow_limit", "1")])
            )
            html.show_warning(text)

        if html.output_format == "csv_export" and user.may("general.csv_export"):
            _output_csv("bi", av_mode, av_data, avoptions)
            return

        html.write_html(timewarpcode)
        do_render_availability("bi", av_rawdata, av_data, av_mode, None, avoptions)

    html.body_end()
