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
# ails.  You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

import availability, table
from valuespec import *

# TODO: considered_duration und total_duration. Hab ich das wirklich richtig?
# In der Timeline ist das evtl. falsch. Die considered_duration müsste im
# allgemeinen kleiner sein.
# TODO: Koordinaten in inline-Timelines fehlen noch
# TODO: CSV-Export geht nicht mehr

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

# Get availability options without rendering the valuespecs
def get_availability_options_from_url():
    html.plug()
    avoptions = render_availability_options()
    html.drain()
    html.unplug()
    return avoptions


def render_availability_options():
    if html.var("_reset") and html.check_transaction():
        config.save_user_file("avoptions", {})
        for varname in html.vars.keys():
            if varname.startswith("avo_"):
                html.del_var(varname)
            html.del_var("avoptions")

    avoptions = availability.get_default_avoptions()

    # Users of older versions might not have all keys set. The following
    # trick will merge their options with our default options.
    avoptions.update(config.load_user_file("avoptions", {}))

    is_open = False
    html.begin_form("avoptions")
    html.hidden_field("avoptions", "set")
    if html.var("avoptions") == "set":
        for name, height, show_in_reporting, vs in availability.avoption_entries:
            try:
                avoptions[name] = vs.from_html_vars("avo_" + name)
            except MKUserError, e:
                html.add_user_error(e.varname, e.message)
                is_open = True

    range_vs = None
    for name, height, show_in_reporting, vs in availability.avoption_entries:
        if name == 'rangespec':
            range_vs = vs

    try:
        range, range_title = range_vs.compute_range(avoptions["rangespec"])
        avoptions["range"] = range, range_title
    except MKUserError, e:
        html.add_user_error(e.varname, e.message)

    if html.has_user_errors():
        html.show_user_errors()

    html.write('<div class="view_form" id="avoptions" %s>'
            % (not is_open and 'style="display: none"' or '') )
    html.write("<table border=0 cellspacing=0 cellpadding=0 class=filterform><tr><td>")

    for name, height, show_in_reporting, vs in availability.avoption_entries:
        html.write('<div class="floatfilter %s %s">' % (height, name))
        html.write('<div class=legend>%s</div>' % vs.title())
        html.write('<div class=content>')
        vs.render_input("avo_" + name, avoptions.get(name))
        html.write("</div>")
        html.write("</div>")

    html.write("</td></tr>")

    html.write("<tr><td>")
    html.button("apply", _("Apply"), "submit")
    html.button("_reset", _("Reset to defaults"), "submit")
    html.write("</td></tr></table>")
    html.write("</div>")

    html.hidden_fields()
    html.end_form()

    if html.form_submitted():
        config.save_user_file("avoptions", avoptions)

    # Convert outage-options from service to host
    states = avoptions["outage_statistics"][1]
    for os, oh in [ ("ok","up"), ("crit","down"), ("unknown", "unreach") ]:
        if os in states:
            states.append(oh)

    return avoptions


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
def render_availability_page(view, datasource, filterheaders, display_options, only_sites, limit):
    if handle_edit_annotations():
        return

    avoptions = get_availability_options_from_url()
    time_range, range_title = avoptions["range"]

    # We make reports about hosts, services or BI aggregates
    if "service" in datasource["infos"]:
        what = "service"
    elif "aggr_name" in datasource["infos"]:
        what = "bi"
    else:
        what = "host"

    # We have two display modes:
    # - Show availability table (stats) "table"
    # - Show timeline                   "timeline"
    # --> controlled by URL variable "av_mode"
    av_mode = html.var("av_mode", "table")
    if av_mode == "timeline":
        title = _("Availability Timeline")
    else:
        title = _("Availability")
        html.add_status_icon("download_csv", _("Export as CSV"), html.makeuri([("output_format", "csv_export")]))

    # This is combined with the object selection
    # - Show all objects
    # - Show one specific object
    # --> controlled by URL variables "av_site", "av_host" and "av_service"
    # --> controlled by "av_aggr" in case of BI aggregate
    title += " - "
    if html.var("av_host"):
        av_object = (html.var("av_site"), html.var("av_host"), html.var("av_service"))
        title += av_object[1]
        if av_object[2]:
            title += " - " + av_object[2]
    elif html.var("av_aggr"):
        av_object = (None, None, html.var("av_aggr"))
        title += av_object[2]
    else:
        av_object = None
        title += view_title(view)

    title += " - " + range_title

    # Prepare CSV ouput (TODO: move this into own page)
    if html.output_format == "csv_export":
        do_csv = True
        av_output_csv_mimetype(title)
    else:
        do_csv = False


    if 'H' in display_options:
        html.body_start(title, stylesheets=["pages","views","status"], force=True)
    if 'T' in display_options:
        html.top_heading(title)

    handle_delete_annotations()

    # Remove variables for editing annotations, otherwise they will make it into the uris
    html.del_all_vars("editanno_")
    html.del_all_vars("anno_")
    if html.var("filled_in") == "editanno":
        html.del_var("filled_in")

    if 'B' in display_options:
        html.begin_context_buttons()
        togglebutton("avoptions", html.has_user_errors(), "painteroptions", _("Configure details of the report"))
        html.context_button(_("Status View"), html.makeuri([("mode", "status")]), "status")
        if config.reporting_available():
            html.context_button(_("Export as PDF"), html.makeuri([], filename="report_instant.py"), "report")

        if av_mode == "timeline" or av_object:
            html.context_button(_("Availability"), html.makeuri([("av_mode", "availability"), ("av_host", ""), ("av_aggr", "")]), "availability")
        elif not av_object:
            html.context_button(_("Timeline"), html.makeuri([("av_mode", "timeline")]), "timeline")

        elif av_mode == "timeline" and what != "bi":
            history_url = availability.history_url_of(av_object, time_range)
            html.context_button(_("History"), history_url, "history")
        html.end_context_buttons()

    if not do_csv:
        # Render the avoptions again to get the HTML code, because the HTML vars have changed
        # above (anno_ and editanno_ has been removed, which must not be part of the form
        avoptions = render_availability_options()

    if not html.has_user_errors():
        av_rawdata = availability.get_availability_rawdata(what, filterheaders, only_sites,
                                                           av_object, av_mode == "timeline", avoptions)
        do_render_availability(what, av_rawdata, av_mode, av_object, avoptions)

    if 'Z' in display_options:
        html.bottom_footer()
    if 'H' in display_options:
        html.body_end()


def av_output_csv_mimetype(title):
    html.req.content_type = "text/csv; charset=UTF-8"
    filename = '%s-%s.csv' % (title, time.strftime('%Y-%m-%d_%H-%M-%S', time.localtime(time.time())))
    if type(filename) == unicode:
        filename = filename.encode("utf-8")
    html.req.headers_out['Content-Disposition'] = 'Attachment; filename="%s"' % filename


def do_render_availability(what, av_rawdata, av_mode, av_object, avoptions):
    av_data = availability.compute_availability(what, av_rawdata, avoptions)

    if av_mode == "timeline":
        render_availability_timelines(what, av_data, avoptions)
    else:
        availability_tables = availability.compute_availability_groups(what, av_data, avoptions)
        render_availability_tables(availability_tables, what, avoptions)

    annotations = load_annotations()
    render_annotations(annotations, av_rawdata, what, avoptions, omit_service = av_object != None)


# style is either inline (just the timeline bar) or "standalone" (the complete page)
# TODO: Diese Funktion entfällt. Bitte layout_timeline verwenden.
def ZXXXX_render_timeline(timeline_rows, from_time, until_time, considered_duration,
                    timeline, range_title, render_number, what, timewarpcode, avoptions, fetch, style):

    if not timeline_rows:
        if fetch:
            return []
        else:
            html.write('<div class=info>%s</div>' % _("No information available"))
            return

    # Timeformat: show date only if the displayed time range spans over
    # more than one day.
    time_format = "%H:%M:%S"
    if time.localtime(from_time)[:3] != time.localtime(until_time-1)[:3]:
        time_format = "%Y-%m-%d " + time_format
    def render_date(ts):
        if avoptions["datetime_format"] == "epoch":
            return str(int(ts))
        else:
            return time.strftime(time_format, time.localtime(ts))

    # Render graphical representation
    # Make sure that each cell is visible, if possible
    min_percentage = min(100.0 / len(timeline_rows), style == "inline" and 0.0 or 0.5)
    rest_percentage = 100 - len(timeline_rows) * min_percentage
    if not fetch:
        html.write('<div class="timelinerange %s">' % style)
    if style == "standalone":
        html.write('<div class=from>%s</div><div class=until>%s</div></div>' % (
            render_date(from_time), render_date(until_time)))

    if not fetch:
        html.write('<table class="timeline %s">' % style)
        html.write('<tr class=timeline>')
    chaos_begin = None
    chaos_end = None
    chaos_count = 0
    chaos_width = 0

    def output_chaos_period(chaos_begin, chaos_end, chaos_count, chaos_width):
        if fetch:
            html.write("|chaos:%s" % chaos_width)
        else:
            title = _("%d chaotic state changes from %s until %s (%s)") % (
                chaos_count,
                render_date(chaos_begin), render_date(chaos_end),
                render_number(chaos_end - chaos_begin, considered_duration))
            html.write('<td style="width: %.3f%%" title="%s" class="chaos"></td>' % (
                       max(0.2, chaos_width), html.attrencode(title)))

    for row_nr, (row, state_id) in enumerate(timeline_rows):
        for sid, css, sname, help in availability.availability_columns[what]:
            if sid == state_id:
                title = _("From %s until %s (%s) %s") % (
                    render_date(row["from"]), render_date(row["until"]),
                    render_number(row["duration"], considered_duration),
                    help and help or sname)
                if "log_output" in row and row["log_output"]:
                    title += " - " + row["log_output"]
                width = rest_percentage * row["duration"] / considered_duration

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
                elif chaos_begin:
                    # Only output chaos phases with a certain length
                    if chaos_count >= 4:
                        output_chaos_period(chaos_begin, chaos_end, chaos_count, chaos_width)

                    chaos_begin = None
                    chaos_count = 0
                    chaos_width = 0

                width += min_percentage
                if fetch:
                    html.write("|%s:%s" % (css, width))
                else:
                    html.write('<td onmouseover="timeline_hover(%d, 1);" onmouseout="timeline_hover(%d, 0);" '
                               'style="width: %.3f%%" title="%s" class="%s"></td>' % (
                               row_nr, row_nr, width, html.attrencode(title), css))

    if chaos_count > 1:
        output_chaos_period(chaos_begin, chaos_end, chaos_count, chaos_width)
    if not fetch:
        html.write('</tr></table>')

    if style == "inline":
        if not fetch:
            render_timeline_choords(from_time, until_time, width=500)
        return

    # Render timewarped BI aggregate (might be empty)
    html.write(timewarpcode)

    # Render Table
    table.begin("av_timeline", "", css="timelineevents")
    for row_nr, (row, state_id) in enumerate(timeline_rows):
        table.row()
        table.cell(_("Links"), css="buttons")
        if what == "bi":
            url = html.makeuri([("timewarp", str(int(row["from"])))])
            if html.var("timewarp") and int(html.var("timewarp")) == int(row["from"]):
                html.disabled_icon_button("timewarp_off")
            else:
                html.icon_button(url, _("Time warp - show BI aggregate during this time period"), "timewarp")
        else:
            url = html.makeuri([("anno_site", tl_site),
                                ("anno_host", tl_host),
                                ("anno_service", tl_service),
                                ("anno_from", row["from"]),
                                ("anno_until", row["until"])])
            html.icon_button(url, _("Create an annotation for this period"), "annotation")

        table.cell(_("From"), render_date(row["from"]), css="nobr narrow")
        table.cell(_("Until"), render_date(row["until"]), css="nobr narrow")
        table.cell(_("Duration"), render_number(row["duration"], considered_duration), css="narrow number")
        for sid, css, sname, help in availability_columns[what]:
            if sid == state_id:
                table.cell(_("State"), sname, css=css + " state narrow")
                break
        else:
            table.cell(_("State"), "(%s/%s)" % (sid,sname))
        table.cell(_("Last Known Plugin Output"), row["log_output"])

    table.end()

    # Legend for timeline
    if "display_timeline_legend" in avoptions["labelling"]:
        render_timeline_legend(what)


def render_timeline_choords(from_time, until_time, width):
    duration = until_time - from_time
    def render_choord(t, title):
        pixel = width * (t - from_time) / float(duration)
        html.write('<div title="%s" class="timelinechoord" style="left: %dpx"></div>' % (title, pixel))

    # Now comes the difficult part: decide automatically, whether to use
    # hours, days, weeks or months. Days and weeks needs to take local time
    # into account. Months are irregular.
    hours = duration / 3600
    if hours < 12:
        scale = "hours"
    elif hours < 24:
        scale = "2hours"
    elif hours < 48:
        scale = "6hours"
    elif hours < 24 * 14:
        scale = "days"
    elif hours < 24 * 60:
        scale = "weeks"
    else:
        scale = "months"

    broken = list(time.localtime(from_time))
    while True:
        next_choord, title = find_next_choord(broken, scale)
        if next_choord >= until_time:
            break
        render_choord(next_choord, title)

# Elements in broken:
# 0: year
# 1: month (1 = January)
# 2: day of month
# 3: hour
# 4: minute
# 5: second
# 6: day of week (0 = monday)
# 7: day of year
# 8: isdst (0 or 1)
def find_next_choord(broken, scale):
    broken[4:6] = [0, 0] # always set min/sec to 00:00
    old_dst = broken[8]

    if scale == "hours":
        epoch = time.mktime(broken)
        epoch += 3600
        broken[:] = list(time.localtime(epoch))
        title = time.strftime("%H:%M",  broken)

    elif scale == "2hours":
        broken[3] = broken[3] / 2 * 2
        epoch = time.mktime(broken)
        epoch += 2 * 3600
        broken[:] = list(time.localtime(epoch))
        title = valuespec.weekdays[broken[6]] + time.strftime(" %H:%M", broken)

    elif scale == "6hours":
        broken[3] = broken[3] / 6 * 6
        epoch = time.mktime(broken)
        epoch += 6 * 3600
        broken[:] = list(time.localtime(epoch))
        title = valuespec.weekdays[broken[6]] + time.strftime(" %H:%M", broken)

    elif scale == "days":
        broken[3] = 0
        epoch = time.mktime(broken)
        epoch += 24 * 3600
        broken[:] = list(time.localtime(epoch))
        title = valuespec.weekdays[broken[6]] + time.strftime(", %d.%m. 00:00", broken)

    elif scale == "weeks":
        broken[3] = 0
        at_00 = int(time.mktime(broken))
        at_monday = at_00 - 86400 * broken[6]
        epoch = at_monday + 7 * 86400
        broken[:] = list(time.localtime(epoch))
        title = valuespec.weekdays[broken[6]] + time.strftime(", %d.%m.", broken)

    else: # scale == "months":
        broken[3] = 0
        broken[2] = 0
        broken[1] += 1
        if broken[1] > 12:
            broken[1] = 1
            broken[0] += 1
        epoch = time.mktime(broken)
        title = "%s %d" % (valuespec.month_names[broken[1]-1], broken[0])

    dst = broken[8]
    if old_dst == 1 and dst == 0:
        epoch += 3600
    elif old_dst == 0 and dst == 1:
        epoch -= 3600
    return epoch, title


def render_availability_tables(availability_tables, what, avoptions):

    if not availability_tables:
        html.message(_("No matching hosts/services."))
        return

    for group_name, availability_table in availability_tables:
        render_availability_table(group_name, availability_table, what, avoptions)

    # Legend for Availability levels
    av_levels = avoptions["av_levels"]
    if av_levels:
        warn, crit = av_levels
        html.write('<div class="avlegend levels">')
        html.write('<h3>%s</h3>' % _("Availability levels"))
        html.write('<div class="state state0">%s</div><div class=level>&ge; %.3f%%</div>' % (_("OK"), warn))
        html.write('<div class="state state1">%s</div><div class=level>&ge; %.3f%%</div>' % (_("WARN"), crit))
        html.write('<div class="state state2">%s</div><div class=level>&lt; %.3f%%</div>' % (_("CRIT"), crit))
        html.write('</div>')

    # Legend for timeline
    if "display_timeline_legend" in avoptions["labelling"] and avoptions["show_timeline"]:
        render_timeline_legend(what)


def render_availability_timelines(what, av_data, avoptions):
    for av_entry in av_data:
        render_availability_timeline(what, av_entry, avoptions)


def render_availability_timeline(what, av_entry, avoptions):

    html.write("<h3>%s %s</h3>" % (_("Timeline of"), availability.object_title(what, av_entry)))

    timeline_rows = av_entry["timeline"]
    if not timeline_rows:
        html.write('<div class=info>%s</div>' % _("No information available"))
        return

    timeline_layout = availability.layout_timeline(what, timeline_rows, avoptions, "standalone")
    render_timeline_bar(timeline_layout, "standalone")
    render_date = timeline_layout["render_date"]
    render_number = availability.render_number_function(avoptions)


    # TODO: Hier fehlt bei BI der Timewarpcode (also der Baum im Zauberzustand)
    # if what == "bi":
    #    render_timewarp(

    # Table with detailed events
    table.begin("av_timeline", "", css="timelineevents")
    for row_nr, row in enumerate(timeline_layout["table"]):
        table.row()
        table.cell(_("Links"), css="buttons")
        if what == "bi":
            url = html.makeuri([("timewarp", str(int(row["from"])))])
            if html.var("timewarp") and int(html.var("timewarp")) == int(row["from"]):
                html.disabled_icon_button("timewarp_off")
            else:
                html.icon_button(url, _("Time warp - show BI aggregate during this time period"), "timewarp")
        else:
            url = html.makeuri([("anno_site", av_entry["site"]),
                                ("anno_host", av_entry["host"]),
                                ("anno_service", av_entry["service"]),
                                ("anno_from", row["from"]),
                                ("anno_until", row["until"])])
            html.icon_button(url, _("Create an annotation for this period"), "annotation")

        table.cell(_("From"),     row["from_text"],     css="nobr narrow")
        table.cell(_("Until"),    row["until_text"],    css="nobr narrow")
        table.cell(_("Duration"), row["duration_text"], css="narrow number")
        table.cell(_("State"),    row["state_name"],    css=row["css"] + " state narrow")
        table.cell(_("Last Known Plugin Output"), row.get("log_output", ""))

    table.end()

    # Legend for timeline
    if "display_timeline_legend" in avoptions["labelling"]:
        render_timeline_legend(what)



def render_timeline_legend(what):
    html.write('<div class="avlegend timeline">')
    html.write('<h3>%s</h3>' % _('Timeline colors'))
    html.write('<div class="state state0">%s</div>' % (what == "host" and _("UP") or _("OK")))
    if what != "host":
        html.write('<div class="state state1">%s</div>'    % _("WARN"))
    html.write('<div class="state state2">%s</div>' % (what == "host" and _("DOWN") or _("CRIT")))
    html.write('<div class="state state3">%s</div>' % (what == "host" and _("UNREACH") or _("UNKNOWN")))
    html.write('<div class="state flapping">%s</div>' % _("Flapping"))
    if what != "host":
        html.write('<div class="state hostdown">%s</div>' % _("H.Down"))
    html.write('<div class="state downtime">%s</div>' % _("Downtime"))
    html.write('<div class="state ooservice">%s</div>' % _("OO/Service"))
    html.write('<div class="state unmonitored">%s</div>' % _("unmonitored"))
    html.write('</div>')


def render_availability_table(group_title, availability_table, what, avoptions):

    av_table = availability.layout_availability_table(what, group_title, availability_table, avoptions)

    # TODO: If summary line is activated, then sorting should now move that line to the
    # top. It should also stay at the bottom. This would require an extension to the
    # table.py module.
    table.begin("av_items", av_table["title"], css="availability",
        searchable = False, limit = None,
        omit_headers = "omit_headers" in avoptions["labelling"])

    for row in av_table["rows"]:
        table.row()

        # Column with icons
        timeline_url = None
        if row["urls"]:
            table.cell("", css="buttons")
            for image, tooltip, url in row["urls"]:
                html.icon_button(url, tooltip, image)
                if image == "timeline":
                    timeline_url = url

        # Column with host/service or aggregate name
        for title, (name, url) in zip(av_table["object_titles"], row["object"]):
            table.cell(title, '<a href="%s">%s</a>' % (url, name))

        if "timeline" in row:
            table.cell(_("Timeline"), css="timeline")
            html.write('<a href="%s">' % timeline_url)
            render_timeline_bar(row["timeline"], "inline")
            html.write('</a>')

        # Columns with the actual availability data
        for (title, help), (text, css) in zip(av_table["cell_titles"], row["cells"]):
            table.cell(title, text, css="narrow number " + css, help=help)

    if "summary" in av_table:
        table.row(css="summary")
        if row["urls"]:
            table.cell("", "") # Empty cell in URLs column
        table.cell("", _("Summary"), css="heading")
        for x in range(1, len(av_table["object_titles"])):
            table.cell("", "") # empty cells, of more object titles than one
        if "timeline" in row:
            table.cell("", "")

        for (title, help), (text, css) in zip(av_table["cell_titles"], av_table["summary"]):
            table.cell(title, text, css="heading number " + css, help=help)

    return table.end() # returns Table data if fetch == True


def render_timeline_bar(timeline_layout, style):
    render_date = timeline_layout["render_date"]
    from_time, until_time = timeline_layout["range"]
    if style == "standalone":
        html.write('<div class="timelinerange %s">' % style)
        html.write('<div class=from>%s</div><div class=until>%s</div></div>' % (
            render_date(from_time), render_date(until_time)))

    html.write('<table class="timeline %s">' % style)
    html.write('<tr class=timeline>')
    for row_nr, title, width, css in timeline_layout["spans"]:
        if style == "standalone":
            hovercode = ' onmouseover="timeline_hover(this, %d, 1);" onmouseout="timeline_hover(this, %d, 0);"' % (row_nr, row_nr)
        else:
            hovercode = ""

        html.write('<td%s style="width: %.3f%%" title="%s" class="%s"></td>' % (
                     hovercode, width, html.attrencode(title), css))
    html.write("</tr></table>")

    # TODO: Choords. Diese müssen aber noch berechnet werden!
    # render_timeline_choords(from_time, until_time, width=500)


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

# Render availability of a BI aggregate. This is currently
# no view and does not support display options
# TODO: Why should we handle this in a special way? Probably because we cannot
# get the list of BI aggregates from the statehist table but use the views
# logic for getting the aggregates. As soon as we have cleaned of the visuals,
# filters, contexts etc we can unify the code!
def render_bi_availability(title, aggr_rows):
    html.add_status_icon("download_csv", _("Export as CSV"), html.makeuri([("output_format", "csv_export")]))
    av_mode = html.var("av_mode", "availability")

    timeline = html.var("timeline")
    if timeline:
        title = _("Timeline of ") + title
    else:
        title = _("Availability of ") + title
    if html.output_format != "csv_export":
        html.body_start(title, stylesheets=["pages","views","status", "bi"], javascripts=['bi'])
        html.top_heading(title)
        html.begin_context_buttons()
        togglebutton("avoptions", False, "painteroptions", _("Configure details of the report"))
        html.context_button(_("Status View"), html.makeuri([("mode", "status")]), "status")
        if timeline:
            html.context_button(_("Availability"), html.makeuri([("timeline", "")]), "availability")
        elif len(aggr_rows) == 1:
            aggr_name = aggr_rows[0]["aggr_name"]
            aggr_group = aggr_rows[0]["aggr_group"]
            timeline_url = html.makeuri([("timeline", "1"), ("av_aggr_name", aggr_name), ("av_aggr_group", aggr_group)])
            html.context_button(_("Timeline"), timeline_url, "timeline")
        html.end_context_buttons()

    html.plug()
    avoptions = render_availability_options()
    time_range, range_title = avoptions["range"]
    avoptions_html = html.drain()
    html.unplug()

    if html.output_format == "csv_export":
        av_output_csv_mimetype(title)
    else:
        html.write(avoptions_html)

    timewarpcode = ""

    if not html.has_user_errors():
        spans = []
        for aggr_row in aggr_rows:
            tree = aggr_row["aggr_tree"]
            reqhosts = tree["reqhosts"]
            try:
                timewarp = int(html.var("timewarp"))
            except:
                timewarp = None
            these_spans, timewarp_tree_state = availability.get_bi_spans(tree, aggr_row["aggr_group"], avoptions, timewarp)
            spans += these_spans
            if timewarp and timewarp_tree_state:
                state, assumed_state, node, subtrees = timewarp_tree_state
                eff_state = state
                if assumed_state != None:
                    eff_state = assumed_state
                row = {
                        "aggr_tree"            : tree,
                        "aggr_treestate"       : timewarp_tree_state,
                        "aggr_state"           : state,          # state disregarding assumptions
                        "aggr_assumed_state"   : assumed_state,  # is None, if there are no assumptions
                        "aggr_effective_state" : eff_state,      # is assumed_state, if there are assumptions, else real state
                        "aggr_name"            : node["title"],
                        "aggr_output"          : eff_state["output"],
                        "aggr_hosts"           : node["reqhosts"],
                        "aggr_function"        : node["func"],
                        "aggr_group"           : html.var("aggr_group"),
                }
                tdclass, htmlcode = bi.render_tree_foldable(row, boxes=False, omit_root=False,
                                         expansion_level=bi.load_ex_level(), only_problems=False, lazy=False)
                html.plug()
                html.write('<h3>')

                # render icons for back and forth
                if int(these_spans[0]["from"]) == timewarp:
                    html.disabled_icon_button("back_off")
                have_forth = False
                previous_span = None
                for span in these_spans:
                    if int(span["from"]) == timewarp and previous_span != None:
                        html.icon_button(html.makeuri([("timewarp", str(int(previous_span["from"])))]), _("Jump one phase back"), "back")
                    elif previous_span and int(previous_span["from"]) == timewarp and span != these_spans[-1]:
                        html.icon_button(html.makeuri([("timewarp", str(int(span["from"])))]), _("Jump one phase forth"), "forth")
                        have_forth = True
                    previous_span = span
                if not have_forth:
                    html.disabled_icon_button("forth_off")

                html.write(" &nbsp; ")
                html.icon_button(html.makeuri([("timewarp", "")]), _("Close Timewarp"), "closetimewarp")
                timewarpcode = html.drain()
                html.unplug()
                timewarpcode += '%s %s</h3>' % (_("Timewarp to "), time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timewarp))) + \
                               '<table class="data table timewarp"><tr class="data odd0"><td class="%s">' % tdclass + \
                               htmlcode + \
                               '</td></tr></table>'
            else:
                timewarpcode = ""

        html.write(timewarpcode)
        av_rawdata = availability.spans_by_object(spans)
        do_render_availability("bi", av_rawdata, av_mode, None, avoptions)# ,  timewarpcode)

    if html.output_format != "csv_export":
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
#   '----------------------------------------------------------------------'

# Example for annotations:
# {
#   ( "mysite", "foohost", "myservice" ) : # service might be None
#       [
#         {
#            "from"       : 1238288548,
#            "until"      : 1238292845,
#            "text"       : u"Das ist ein Text über mehrere Zeilen, oder was weiß ich",
#            "downtime"   : True, # Treat as scheduled Downtime,
#            "date"       : 12348854885, # Time of entry
#            "author"     : "mk",
#         },
#         # ... further entries
#      ]
# }


def save_annotations(annotations):
    file(defaults.var_dir + "/web/statehist_annotations.mk", "w").write(repr(annotations) + "\n")

def load_annotations(lock = False):
    path = defaults.var_dir + "/web/statehist_annotations.mk"
    if os.path.exists(path):
        if lock:
            aquire_lock(path)
        return eval(file(path).read())
    else:
        return {}

def update_annotations(site_host_svc, annotation):
    annotations = load_annotations(lock = True)
    entries = annotations.get(site_host_svc, [])
    new_entries = []
    for entry in entries:
        if  entry["from"] == annotation["from"] \
            and entry["until"] == annotation["until"]:
            continue # Skip existing entries with same identity
        new_entries.append(entry)
    new_entries.append(annotation)
    annotations[site_host_svc] = new_entries
    save_annotations(annotations)


def find_annotation(annotations, site_host_svc, fromtime, untiltime):
    entries = annotations.get(site_host_svc)
    if not entries:
        return None
    for annotation in entries:
        if annotation["from"] == fromtime \
            and annotation["until"] == untiltime:
            return annotation
    return None

def delete_annotation(annotations, site_host_svc, fromtime, untiltime):
    entries = annotations.get(site_host_svc)
    if not entries:
        return
    found = None
    for nr, annotation in enumerate(entries):
        if annotation["from"] == fromtime \
            and annotation["until"] == untiltime:
            found = nr
            break
    if found != None:
        del entries[nr]


def render_annotations(annotations, by_host, what, avoptions, omit_service):
    (from_time, until_time), range_title = avoptions["range"]
    format = "%H:%M:%S"
    if time.localtime(from_time)[:3] != time.localtime(until_time-1)[:3]:
        format = "%Y-%m-%d " + format
    def render_date(ts):
        return time.strftime(format, time.localtime(ts))

    annos_to_render = []
    for site_host, avail_entries in by_host.iteritems():
        for service in avail_entries.keys():
            site_host_svc = site_host[0], site_host[1], (service or None)
            for annotation in annotations.get(site_host_svc, []):
                if (annotation["from"] >= from_time and annotation["from"] <= until_time) or \
                   (annotation["until"] >= from_time and annotation["until"] <= until_time):
                   annos_to_render.append((site_host_svc, annotation))

    annos_to_render.sort(cmp=lambda a,b: cmp(a[1]["from"], b[1]["from"]) or cmp(a[0], b[0]))

    labelling = avoptions["labelling"]

    table.begin(title = _("Annotations"), omit_if_empty = True)
    for (site_id, host, service), annotation in annos_to_render:
        table.row()
        table.cell("", css="buttons")
        anno_vars = [
          ( "anno_site", site_id ),
          ( "anno_host", host ),
          ( "anno_service", service or "" ),
          ( "anno_from", int(annotation["from"]) ),
          ( "anno_until", int(annotation["until"]) ),
        ]
        edit_url = html.makeuri(anno_vars)
        html.icon_button(edit_url, _("Edit this annotation"), "edit")
        delete_url = html.makeactionuri([("_delete_annotation", "1")] + anno_vars)
        html.icon_button(delete_url, _("Delete this annotation"), "delete")

        if not omit_service:
            if not "omit_host" in labelling:
                host_url = "view.py?" + html.urlencode_vars([("view_name", "hoststatus"), ("site", site_id), ("host", host)])
                table.cell(_("Host"), '<a href="%s">%s</a>' % (host_url, host))

            if service:
                service_url = "view.py?" + html.urlencode_vars([("view_name", "service"), ("site", site_id), ("host", host), ("service", service)])
                # TODO: honor use_display_name. But we have no display names here...
                service_name = service
                table.cell(_("Service"), '<a href="%s">%s</a>' % (service_url, service_name))

        table.cell(_("From"), render_date(annotation["from"]), css="nobr narrow")
        table.cell(_("Until"), render_date(annotation["until"]), css="nobr narrow")
        table.cell(_("Annotation"), html.attrencode(annotation["text"]))
        table.cell(_("Author"), annotation["author"])
        table.cell(_("Entry"), render_date(annotation["date"]), css="nobr narrow")
    table.end()



def edit_annotation():
    site_id = html.var("anno_site") or ""
    hostname = html.var("anno_host")
    service = html.var("anno_service") or None
    fromtime = float(html.var("anno_from"))
    untiltime = float(html.var("anno_until"))
    site_host_svc = (site_id, hostname, service)

    # Find existing annotation with this specification
    annotations = load_annotations()
    annotation = find_annotation(annotations, site_host_svc, fromtime, untiltime)
    if not annotation:
        annotation = {
        "from"    : fromtime,
        "until"   : untiltime,
        "text"    : "",
        }
    annotation["host"] = hostname
    annotation["service"] = service
    annotation["site"] = site_id

    html.plug()

    title = _("Edit annotation of ") + hostname
    if service:
        title += "/" + service
    html.body_start(title, stylesheets=["pages","views","status"])
    html.top_heading(title)

    html.begin_context_buttons()
    html.context_button(_("Abort"), html.makeuri([("anno_host", "")]), "abort")
    html.end_context_buttons()

    value = forms.edit_dictionary([
        ( "site",    TextAscii(title = _("Site")) ),
        ( "host",    TextUnicode(title = _("Hostname")) ),
        ( "service", Optional(TextUnicode(allow_empty=False), sameline = True, title = _("Service")) ),
        ( "from",    AbsoluteDate(title = _("Start-Time"), include_time = True) ),
        ( "until",   AbsoluteDate(title = _("End-Time"), include_time = True) ),
        ( "text",    TextAreaUnicode(title = _("Annotation"), allow_empty = False) ), ],
        annotation,
        varprefix = "editanno_",
        formname = "editanno",
        focus = "text")

    if value:
        site_host_svc = value["site"], value["host"], value["service"]
        del value["site"]
        del value["host"]
        value["date"] = time.time()
        value["author"] = config.user_id
        update_annotations(site_host_svc, value)
        html.drain() # omit previous HTML code, not needed
        html.unplug()
        html.del_all_vars(prefix = "editanno_")
        html.del_var("filled_in")
        return False

    html.unplug() # show HTML code

    html.bottom_footer()
    html.body_end()
    return True


# Called at the beginning of every availability page
def handle_delete_annotations():
    if html.var("_delete_annotation"):
        site_id = html.var("anno_site") or ""
        hostname = html.var("anno_host")
        service = html.var("anno_service") or None
        fromtime = float(html.var("anno_from"))
        untiltime = float(html.var("anno_until"))
        site_host_svc = (site_id, hostname, service)

        annotations = load_annotations()
        annotation = find_annotation(annotations, site_host_svc, fromtime, untiltime)
        if not annotation:
            return

        if not html.confirm(_("Are you sure that you want to delete the annotation '%s'?" % annotation["text"])):
            return

        delete_annotation(annotations, site_host_svc, fromtime, untiltime)
        save_annotations(annotations)

def handle_edit_annotations():
    if html.var("anno_host") and not html.var("_delete_annotation"):
        finished = edit_annotation()
    else:
        finished = False

    return finished


