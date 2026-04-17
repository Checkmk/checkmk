#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import functools
import time
from collections.abc import Callable, Iterator

from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.utils.urls import makeuri, urlencode_vars
from cmk.utils import dateutils
from cmk.utils.servicename import ServiceName

from .columns import availability_columns
from .computation import cell_active, check_av_levels, history_url_of
from .options import get_outage_statistic_options, prepare_avo_timeformats
from .type_defs import (
    AVData,
    AVEntry,
    AVIconSpec,
    AVLayoutTable,
    AVLayoutTableRow,
    AVLayoutTimeline,
    AVLayoutTimelineRow,
    AVObjectCells,
    AVObjectType,
    AVOptions,
    AVOutageStatisticsAggregations,
    AVOutageStatisticsStates,
    AVRowCells,
    AVTimeFormats,
    AVTimelineLabelling,
    AVTimelineRows,
    AVTimelineSpan,
    AVTimelineStyle,
    AVTimeRange,
    AVTimeStamp,
)


# .
#   .--Layout--------------------------------------------------------------.
#   |                  _                            _                      |
#   |                 | |    __ _ _   _  ___  _   _| |_                    |
#   |                 | |   / _` | | | |/ _ \| | | | __|                   |
#   |                 | |__| (_| | |_| | (_) | |_| | |_                    |
#   |                 |_____\__,_|\__, |\___/ \__,_|\__|                   |
#   |                             |___/                                    |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'
# When grouping is enabled, this function is called once for each group
# TODO: range_title sollte hier ueberfluessig sein
# TODO: Hier jetzt nicht direkt HTML erzeugen, sondern eine saubere
# Datenstruktur füllen, welche die Daten so repräsentiert, dass sie
# nur noch 1:1 dargestellt werden müssen.
# Beispiel für einen Rückgabewert:
# {
#    "title" : "Host group foobar",
#    "headers" : [ "OK, "CRIT", "Downtime" ],
#    "rows" : [ ... ],
#    "summary" : [ ("84.50%", "crit"), ("15.50%", "crit"), ("0.00%", "p"),  ("0.00%", "p") ],
# }
# row ist ein dict: {
#    "cells" : [ ("84.50%", "crit"), ("15.50%", "crit"), ("0.00%", "p"),  ("0.00%", "p") ],
#    "urls" : { "timeline": "view.py..." },
#    "object" : ( "Host123", "Foobar" ),
# }
def layout_availability_table(
    what: AVObjectType,
    group_title: str | None,
    availability_table: AVData,
    avoptions: AVOptions,
) -> AVLayoutTable:
    time_range: AVTimeRange = avoptions["range"][0]
    from_time, until_time = time_range
    total_duration = until_time - from_time
    timeformats = prepare_avo_timeformats(avoptions["timeformat"])
    show_timeline = avoptions["show_timeline"]
    labelling = avoptions["labelling"]
    av_levels = avoptions["av_levels"]
    show_summary = avoptions.get("summary")
    summary: dict[str, float] = {}
    summary_counts: dict[str, int] = {}
    unmonitored_objects = 0
    av_table: AVLayoutTable = {
        "title": group_title,
        "rows": [],
    }

    # Titles for the columns that specify the object
    av_table["object_titles"] = object_column_titles(labelling, what)

    # Headers for availability cells
    os_aggrs, os_states = get_outage_statistic_options(avoptions)
    av_table["cell_titles"] = _availability_cell_headers(
        avoptions, os_aggrs, os_states, timeformats, what
    )

    summary["ok_level"] = 0

    # Actual rows
    for entry in availability_table:
        site = entry["site"]
        host = entry["host"]
        service = entry["service"]

        row: AVLayoutTableRow = {}
        av_table["rows"].append(row)

        # Iconbuttons with URLs
        if "omit_buttons" not in labelling:
            urls = omit_urls(host, service, site, time_range, what)
        else:
            urls = []
        row["urls"] = urls
        row["object"] = get_object_cells(what, entry, labelling)

        # Inline timeline
        if show_timeline:
            row["timeline"] = layout_timeline(
                what, entry["timeline"], entry["considered_duration"], avoptions, style="inline"
            )

        # Actuall cells with availability data
        cells: AVRowCells = []
        row["cells"] = cells

        for timeformat, render_number in timeformats:
            for sid, css, _sname, _help_txt in availability_columns(what):
                if not cell_active(sid, avoptions):
                    continue

                ssid = f"{sid}-{timeformat}"
                number = entry["states"].get(sid, 0)
                considered_duration = entry["considered_duration"]
                if not number:
                    css = "unused"
                else:
                    if show_summary:
                        summary.setdefault(ssid, 0.0)
                        if timeformat.startswith("percentage"):
                            if considered_duration > 0:
                                summary[ssid] += float(number) / considered_duration
                        else:
                            summary[ssid] += number

                    # Apply visual availability levels (render OK in yellow/red, if too low)
                    if av_levels and sid in ("ok", "up"):
                        css = "state%d" % check_av_levels(number, av_levels, considered_duration)

                css = css + " state narrow number"
                cells.append((render_number(number, considered_duration), css))

                # Statistics?
                x_cnt, x_min, x_max = entry["statistics"].get(sid, (None, None, None))
                if sid in os_states:
                    statistics = []
                    for aggr in os_aggrs:
                        if x_cnt is not None:
                            if aggr == "avg":
                                r = render_number(
                                    int(number / x_cnt), considered_duration
                                )  # fixed: true-division
                            elif aggr == "min":
                                r = render_number(x_min, considered_duration)
                            elif aggr == "max":
                                r = render_number(x_max, considered_duration)
                            else:
                                r = str(x_cnt)
                                summary_counts.setdefault(ssid, 0)
                                summary_counts[ssid] += x_cnt
                            statistics.append((r, css))
                        else:
                            statistics.append(("", ""))
                    cells.extend(statistics)

        # If timeline == [] and states == {} then this objects has complete unmonitored state
        if entry["timeline"] == [] and entry["states"] == {}:
            unmonitored_objects += 1

        # regardless of timeformat the percentage value should be taken for summary levels
        # verification since the percentage value takes the considered duration as reference duration
        if show_summary and av_levels:
            summary["ok_level"] += float(entry["states"].get("ok", 0)) / (
                entry["considered_duration"]
                if entry["considered_duration"]
                else entry["total_duration"]
            )

    # Summary line. It has the same format as each entry in cells
    # We ignore unmonitored objects
    len_availability_table = len(availability_table) - unmonitored_objects
    if show_summary and len_availability_table > 0:
        summary_cells: AVRowCells = []

        for timeformat, render_number in timeformats:
            for sid, css, _sname, _help_txt in availability_columns(what):
                ssid = f"{sid}-{timeformat}"
                if not cell_active(sid, avoptions):
                    continue

                number = summary.get(ssid, 0)
                if not number:
                    css = "unused"
                else:
                    if show_summary == "average" or timeformat.startswith("percentage"):
                        number = _availability_value(
                            len_availability_table,
                            number,
                            total_duration,
                            percentage=timeformat.startswith("percentage"),
                        )

                    if av_levels and sid in ("ok", "up"):
                        if sid == "ok":
                            check_value = _availability_value(
                                len_availability_table,
                                summary["ok_level"],
                                total_duration,
                                percentage=True,
                            )
                        else:
                            check_value = number
                        css = "state%d" % check_av_levels(check_value, av_levels, total_duration)

                css = css + " state narrow number"
                summary_cells.append((render_number(number, int(total_duration)), css))
                if sid in os_states:
                    for aggr in os_aggrs:
                        if aggr == "cnt":
                            count = summary_counts.get(ssid, 0)
                            if show_summary == "average":
                                text = "%.2f" % (float(count) / len_availability_table)
                            else:
                                text = str(count)
                            summary_cells.append((text, css))
                        else:
                            summary_cells.append(("", ""))
        av_table["summary"] = summary_cells

    return av_table


def _availability_value(
    len_availability_table: int, number: float, total_duration: float, percentage: bool = False
) -> float:
    result: float = number / len_availability_table
    if percentage:
        result *= total_duration
    return result


def omit_urls(
    host: HostName,
    service: ServiceName,
    site: SiteId,
    time_range: AVTimeRange,
    what: AVObjectType,
) -> list[AVIconSpec]:
    urls: list[AVIconSpec] = []
    if what != "bi":
        timeline_url = makeuri(
            request,
            [
                ("av_mode", "timeline"),
                ("av_site", site),
                ("av_host", host),
                ("av_service", service),
            ],
        )
    else:
        timeline_url = makeuri(
            request,
            [
                ("av_mode", "timeline"),
                ("av_aggr_group", host),
                ("aggr_name", service),
                ("view_name", "aggr_single"),
            ],
        )
    urls.append(("timeline", _("Timeline"), timeline_url))
    if what != "bi":
        urls.append(
            ("history", _("Event History"), history_url_of((site, host, service), time_range))
        )
    return urls


def object_column_titles(labelling: AVTimelineLabelling, what: AVObjectType) -> list[str]:
    titles = []
    if what == "bi":
        titles.append(_("Aggregate"))
    else:
        # in service availability we can only omit the host. In the
        # host availability this is only possible if the alias is
        # being displayed, Otherwise the table wouldn't make sense
        # and the pdf renderer would crash
        if "omit_host" not in labelling or (what == "host" and "show_alias" not in labelling):
            titles.append(_("Host"))
        if "show_alias" in labelling:
            titles.append(_("Alias"))

        if what != "host":
            titles.append(_("Service"))
    return titles


def _availability_cell_headers(
    avoptions: AVOptions,
    os_aggrs: AVOutageStatisticsAggregations,
    os_states: AVOutageStatisticsStates,
    timeformats: AVTimeFormats,
    what: AVObjectType,
) -> list[tuple[str, str | None]]:
    statistics_headers = {
        "min": _("Shortest"),
        "max": _("Longest"),
        "avg": _("Average"),
        "cnt": _("Count"),
    }
    cell_titles = []
    for _timeformat, _render in timeformats:
        for sid, _css, sname, help_txt in availability_columns(what):
            if not cell_active(sid, avoptions):
                continue
            if avoptions["av_mode"]:
                sname = _("Avail.")

            cell_titles.append((sname, help_txt))

            if sid in os_states:
                for aggr in os_aggrs:
                    title = statistics_headers[aggr]
                    cell_titles.append((title, None))
    return cell_titles


def get_object_cells(what: AVObjectType, av_entry: AVEntry, labelling: list[str]) -> AVObjectCells:
    host = av_entry["host"]
    service = av_entry["service"]

    objectcells: AVObjectCells = []
    if what == "bi":
        bi_url = "view.py?" + urlencode_vars(
            [("view_name", "aggr_single"), ("aggr_group", host), ("aggr_name", service)]
        )
        objectcells.append((service, bi_url))
        return objectcells

    host_url = "view.py?" + urlencode_vars(
        [("view_name", "hoststatus"), ("site", av_entry["site"]), ("host", host)]
    )
    if "omit_host" not in labelling or (what == "host" and "show_alias" not in labelling):
        objectcells.append((host, host_url))

    if "show_alias" in labelling:
        objectcells.append((av_entry["alias"], host_url))

    if what == "service":
        if "use_display_name" in labelling:
            service_name = av_entry["display_name"]
        else:
            service_name = service
        service_url = "view.py?" + urlencode_vars(
            [
                ("view_name", "service"),
                ("site", av_entry["site"]),
                ("host", host),
                ("service", service),
            ]
        )
        objectcells.append((service_name, service_url))

    return objectcells


# Compute layout of timeline independent of the output device (HTML, PDF, whatever)...
# style is either "inline" or "standalone"
# Output format:
# {
#    "spans" : [ spans... ],
#    "legend" : [ legendentries... ],
# }
def layout_timeline(
    what: AVObjectType,
    timeline_rows: AVTimelineRows,
    considered_duration: int,
    avoptions: AVOptions,
    style: AVTimelineStyle,
) -> AVLayoutTimeline:
    timeformats = prepare_avo_timeformats(avoptions["timeformat"])
    time_range: AVTimeRange = avoptions["range"][0]
    from_time, until_time = time_range
    total_duration = until_time - from_time
    # Timeformat: show date only if the displayed time range spans over
    # more than one day.
    time_format = "%H:%M:%S"
    if time.localtime(from_time)[:3] != time.localtime(until_time - 1)[:3]:
        time_format = "%Y-%m-%d " + time_format

    def render_date_func(time_format: str) -> Callable[[AVTimeStamp], str]:
        def render_date(ts: AVTimeStamp) -> str:
            if avoptions["dateformat"] == "epoch":
                return str(int(ts))
            return time.strftime(time_format, time.localtime(ts))

        return render_date

    render_date = render_date_func(time_format)
    spans: list[AVTimelineSpan] = []
    table: list[AVLayoutTimelineRow] = []
    timeline_layout: AVLayoutTimeline = {
        "range": time_range,
        "spans": spans,
        "time_choords": [],
        "render_date": render_date,
        "table": table,
    }

    # Render graphical representation
    # Make sure that each cell is visible, if possible
    if timeline_rows:
        min_percentage = min(100.0 / len(timeline_rows), style == "inline" and 0.0 or 0.5)
    else:
        min_percentage = 0
    rest_percentage = 100 - len(timeline_rows) * min_percentage

    chaos_begin = None
    chaos_end = None
    chaos_count = 0
    chaos_width = 0

    def apply_render_number_functions(n: AVTimeStamp, d: int) -> str:
        texts = []
        for _timeformat, render_number in timeformats:
            texts.append(render_number(n, d))
        return ", ".join(texts)

    def chaos_period(
        chaos_begin: AVTimeStamp, chaos_end: AVTimeStamp, chaos_count: int, chaos_width: int
    ) -> AVTimelineSpan:
        title = _("%d chaotic state changes from %s until %s (%s)") % (
            chaos_count,
            render_date(chaos_begin),
            render_date(chaos_end),
            apply_render_number_functions(chaos_end - chaos_begin, considered_duration),
        )
        return (None, title, chaos_width, "chaos")

    current_time = from_time
    for row_nr, (row, state_id) in enumerate(timeline_rows):
        this_from_time = row["from"]
        this_until_time = row["until"]
        # If timeline span begins after timeline beginning time, add
        # unmonitored span in front
        if this_from_time > current_time:  # GAP
            spans.append(
                (
                    None,
                    "",
                    100.0 * (this_from_time - current_time) / total_duration,
                    "unmonitored",
                )
            )
        current_time = this_until_time

        from_text = render_date(this_from_time)
        until_text = render_date(this_until_time)
        duration_text = apply_render_number_functions(row["duration"], considered_duration)

        for sid, css, sname, help_txt in availability_columns(what):
            if sid != state_id:
                continue

            title = _("From %s until %s (%s) %s") % (
                from_text,
                until_text,
                duration_text,
                help_txt and help_txt or sname,
            )
            if "log_output" in row and row["log_output"]:
                title += " - " + row["log_output"]
            width = rest_percentage * row["duration"] / total_duration  # fixed: true-division

            # Information for table of detailed events
            if style == "standalone":
                table.append(
                    {
                        "state": state_id,
                        "css": css,
                        "state_name": sname,
                        "from": row["from"],
                        "until": row["until"],
                        "from_text": from_text,
                        "until_text": until_text,
                        "duration_text": duration_text,
                        "site": row["site"],
                    }
                )
                if "log_output" in row and row["log_output"]:
                    table[-1]["log_output"] = row["log_output"]
                if "long_log_output" in row and row["long_log_output"]:
                    long_log_output = row["long_log_output"]
                    # see f062002476470213a35787cfd4dd5e676e3fa53d
                    if (
                        row["service_check_command"] == "check_mk-ps"
                        and row["service_custom_variables"].get("ESCAPE_PLUGIN_OUTPUT", "1") == "0"
                    ):
                        long_log_output = long_log_output.replace("&bsol%3B", "\\")
                    table[-1]["long_log_output"] = long_log_output

            # If the width is very small then we group several phases into
            # one single "chaos period".
            if style == "inline" and width < 0.05:
                if not chaos_begin:
                    chaos_begin = row["from"]
                chaos_width += width
                chaos_count += 1
                chaos_end = row["until"]
                continue

            # Chaos period has ended? One not-small phase:
            if chaos_begin and chaos_end:
                # Only output chaos phases with a certain length
                if chaos_count >= 4:
                    spans.append(chaos_period(chaos_begin, chaos_end, chaos_count, chaos_width))

                chaos_begin = None
                chaos_end = None
                chaos_count = 0
                chaos_width = 0

            width += min_percentage
            spans.append((row_nr, title, width, css))
    # If timeline span ends before the current time, fill it up with
    # unmonitored entry until end
    if avoptions["service_period"] == "honor" and current_time < until_time:  # GAP
        spans.append(
            (
                None,
                "",
                100.0 * (until_time - current_time) / total_duration,
                "unmonitored",
            )
        )

    if chaos_count > 1 and chaos_begin and chaos_end:
        spans.append(chaos_period(chaos_begin, chaos_end, chaos_count, chaos_width))

    if style == "inline":
        timeline_layout["time_choords"] = list(layout_timeline_choords(time_range))

    return timeline_layout


def layout_timeline_choords(time_range: AVTimeRange) -> Iterator[tuple[float, str]]:
    from_time, until_time = time_range
    duration = until_time - from_time

    increment, render = _dispatch_scale(duration / 3600.0)

    ordinate = time.localtime(from_time)
    while True:
        ordinate = increment(ordinate)
        position = (time.mktime(ordinate) - from_time) / float(duration)  # ranges from 0.0 to 1.0
        if position >= 1.0:
            return
        yield position, render(ordinate)


def _dispatch_scale(
    hours: float,
) -> tuple[
    Callable[[time.struct_time], time.struct_time],
    Callable[[time.struct_time], str],
]:
    """decide automatically whether to use hours, days, weeks or months

    Days and weeks needs to take local time into account. Months are irregular.
    """
    if hours < 12:
        return _increment_hour, _render_hour

    if hours < 24:
        return _increment_2hours, _render_2hours

    if hours < 48:
        return _increment_6hours, _render_6hours

    if hours < 24 * 14:
        return _increment_day, _render_day

    if hours < 24 * 60:
        return _increment_week, _render_week

    return _increment_month, _render_month


def _render_hour(tst: time.struct_time) -> str:
    return time.strftime("%H:%M", tst)


def _render_2hours(tst: time.struct_time) -> str:
    return dateutils.weekday_name(tst.tm_wday) + time.strftime(" %H:%M", tst)


def _render_6hours(tst: time.struct_time) -> str:
    return dateutils.weekday_name(tst.tm_wday) + time.strftime(" %H:%M", tst)


def _render_day(tst: time.struct_time) -> str:
    return dateutils.weekday_name(tst.tm_wday) + time.strftime(", %d.%m. 00:00", tst)


def _render_week(tst: time.struct_time) -> str:
    return dateutils.weekday_name(tst.tm_wday) + time.strftime(", %d.%m.", tst)


def _render_month(tst: time.struct_time) -> str:
    return "%s %d" % (dateutils.month_name(tst.tm_mon - 1), tst.tm_year)


def _make_struct(year: int, month: int, day: int, hour: int, *, offset: int) -> time.struct_time:
    # do not 'shorten' to time.struct_time! This fixes tm_isdst, tm_wday and others
    return time.localtime(time.mktime((year, month, day, hour, 0, 0, 0, 0, 0)) + offset)


def _fix_dst_change(
    incrementor: Callable[[time.struct_time], time.struct_time],
) -> Callable[[time.struct_time], time.struct_time]:
    """Fix up one hour offset in case the incrementor crosses the DST switch"""

    @functools.wraps(incrementor)
    def wrapped(intime: time.struct_time) -> time.struct_time:
        outtime = incrementor(intime)
        if intime.tm_isdst == outtime.tm_isdst:
            return outtime
        shift = (intime.tm_isdst - outtime.tm_isdst) * 3600
        return time.localtime(time.mktime(outtime) + shift)

    return wrapped


@_fix_dst_change
def _increment_hour(tst: time.struct_time) -> time.struct_time:
    return _make_struct(tst.tm_year, tst.tm_mon, tst.tm_mday, tst.tm_hour, offset=3600)


@_fix_dst_change
def _increment_2hours(tst: time.struct_time) -> time.struct_time:
    return _make_struct(tst.tm_year, tst.tm_mon, tst.tm_mday, tst.tm_hour // 2 * 2, offset=7200)


@_fix_dst_change
def _increment_6hours(tst: time.struct_time) -> time.struct_time:
    return _make_struct(tst.tm_year, tst.tm_mon, tst.tm_mday, tst.tm_hour // 6 * 6, offset=6 * 3600)


@_fix_dst_change
def _increment_day(tst: time.struct_time) -> time.struct_time:
    return _make_struct(tst.tm_year, tst.tm_mon, tst.tm_mday, 0, offset=24 * 3600)


@_fix_dst_change
def _increment_week(tst: time.struct_time) -> time.struct_time:
    return _make_struct(tst.tm_year, tst.tm_mon, tst.tm_mday, 0, offset=86400 * (7 - tst.tm_wday))


@_fix_dst_change
def _increment_month(tst: time.struct_time) -> time.struct_time:
    return _make_struct(tst.tm_year + (tst.tm_mon == 12), (tst.tm_mon % 12) + 1, 1, 0, offset=0)
