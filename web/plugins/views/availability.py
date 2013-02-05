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

import table
from valuespec import *

# Function building the availability view
def render_availability(view, datasource, filterheaders, display_options, 
                        only_sites, limit):
    timeline = not not html.var("timeline")
    if timeline:
        tl_site = html.var("timeline_site")
        tl_host = html.var("timeline_host")
        tl_service = html.var("timeline_service")
        title = _("Timeline of") + " " + tl_host
        if tl_service:
            title += ", " + tl_service
        timeline = (tl_site, tl_host, tl_service)

    else:
        title = _("Availability: ") + view_title(view)
    if 'H' in display_options:
        html.body_start(title, stylesheets=["pages","views","status"])
    if 'T' in display_options:
        html.top_heading(title)
    if 'B' in display_options:
        html.begin_context_buttons()
        togglebutton("avoptions", False, "painteroptions", _("Configure details of the report"))
        html.context_button(_("Status View"), html.makeuri([("mode", "status")]), "status")
        if timeline:
            html.context_button(_("Availability"), html.makeuri([("timeline", "")]), "availability")
        html.end_context_buttons()

    avoptions = render_availability_options()
    if not html.has_user_errors():
        do_render_availability(datasource, filterheaders, avoptions, only_sites, limit, timeline)

    if 'Z' in display_options:
        html.bottom_footer()
    if 'H' in display_options:
        html.body_end()

avoption_entries = [
  # Time range selection
  ( "rangespec",
    "double",
    CascadingDropdown(
        title = _("Time range"),
        choices = [

            ( "d0",  _("Today") ),
            ( "d1",  _("Yesterday") ),

            ( "w0",  _("This week") ),
            ( "w1",  _("Last week") ),

            ( "m0",  _("This month") ),
            ( "m1",  _("Last month") ),

            ( "y0",  _("This year") ),
            ( "y1",  _("Last year") ),

            ( "age", _("The last..."), Age() ),
            ( "date", _("Explicit date..."), 
                Tuple(
                    orientation = "horizontal",
                    title_br = False,
                    elements = [
                        AbsoluteDate(title = _("From:")),
                        AbsoluteDate(title = _("To:")),
                    ],
                ),
            ),
        ],
        default_value = "m1",
    )
  ),

  # How to deal with downtimes, etc.
  ( "consider", 
    "double",
    Dictionary( 
       title = _("Status Classification"),
       columns = 2,
       elements = [
           ( "downtime", 
              Checkbox(label = _("Consider scheduled downtimes")),
           ),
           ( "host_down", 
              Checkbox(label = _("Consider times where the host is down")),
           ),
           ( "notification_period", 
              Checkbox(label = _("Consider notification period")),
           ),
           ( "unmonitored",
              Checkbox(label = _("Consider unmonitored time")),
           ),
       ],
       optional_keys = False,
    ),
  ),

  # Format of numbers
  ( "timeformat",
    "single",
    DropdownChoice(
        title = _("Format time ranges as"),
        choices = [
            ("percentage_0", _("Percentage - XX %") ),
            ("percentage_1", _("Percentage - XX.X %") ),
            ("percentage_2", _("Percentage - XX.XX %") ),
            ("percentage_3", _("Percentage - XX.XXX %") ),
            ("seconds",      _("Seconds") ),
            ("minutes",      _("Minutes") ),
            ("hours",        _("Hours") ),
            ("hhmmss",       _("HH:MM:SS") ),
        ],
    )
  ),


  # Optionally group some states togehter
  ( "state_grouping", 
    "single",
    Dictionary( 
       title = _("Status Grouping"),
       columns = 2,
       elements = [
           ( "warn_is_ok", 
              Checkbox(label = _("Treat WARN as OK")),
           ),
           ( "unknown_is_crit", 
              Checkbox(label = _("Treat UNKNOWN as CRIT")),
           ),
       ],
       optional_keys = False,
    ),
  ),
]


def render_availability_options():
    avoptions = config.load_user_file("avoptions", {
        "range"          : (time.time() - 86400, time.time()),
        "consider"       : {
            "downtime"            : True,
            "host_down"           : True,
            "notification_period" : True,
            "unmonitored"         : True,
        },
        "timeformat"     : "percentage_2",
        "rangespec"      : "d0",
        "state_grouping" : {
            "warn_is_ok"      : False,
            "unknown_is_crit" : False,
        },
    })

    is_open = False
    html.begin_form("avoptions")
    html.write('<div class="view_form" id="avoptions" %s>' 
            % (not is_open and 'style="display: none"' or '') )
    html.write("<table border=0 cellspacing=0 cellpadding=0 class=filterform><tr><td>")

    if html.form_submitted():
        for name, height, vs in avoption_entries:
            try:
                avoptions[name] = vs.from_html_vars("avo_" + name)
            except MKUserError, e:
                html.add_user_error(e.varname, e.message)
    
    try:
        range, range_title = compute_range(avoptions["rangespec"])
        avoptions["range"] = range, range_title
    except MKUserError, e:
        html.add_user_error(e.varname, e.message)

    if html.has_user_errors():
        html.show_user_errors()

    for name, height, vs in avoption_entries:
        html.write('<div class="floatfilter %s %s">' % (height, name))
        html.write('<div class=legend>%s</div>' % vs.title())
        html.write('<div class=content>')
        vs.render_input("avo_" + name, avoptions.get(name))
        html.write("</div>")
        html.write("</div>")
    
    html.write("</td></tr>")

    html.write("<tr><td>")
    html.button("apply", _("Apply"), "submit")
    html.write("</td></tr></table>")
    html.write("</div>")

    html.hidden_fields()
    html.end_form()

    if html.form_submitted():
        config.save_user_file("avoptions", avoptions)

    return avoptions

month_names = [
  _("January"), _("February"), _("March"), _("April"),
  _("May"), _("June"), _("July"), _("August"),
  _("September"), _("October"), _("November"), _("December")
]

def compute_range(rangespec):
    now = time.time()
    if rangespec[0] == 'age':
        from_time = now - rangespec[1]
        until_time = now
        title = _("The last ") + Age().value_to_text(rangespec[1])
        return (from_time, until_time), title
    elif rangespec[0] == 'date':
        from_time, until_time = rangespec[1]
        if from_time > until_time:
            raise MKUserError("avo_rangespec_9_0_year", _("The end date must be after the start date"))
        until_time += 86400 # Consider *end* of this day
        title = AbsoluteDate().value_to_text(from_time) + " ... " + \
                AbsoluteDate().value_to_text(until_time)
        return (from_time, until_time), title

    else:
        # year, month, day_of_month, hour, minute, second, day_of_week, day_of_year, is_daylightsavingtime
        broken = list(time.localtime(now))
        broken[3:6] = 0, 0, 0 # set time to 00:00:00
        midnight = time.mktime(broken)

        until_time = now
        if rangespec[0] == 'd': # this/last Day
            from_time = time.mktime(broken)
            titles = _("Today"), _("Yesterday")

        elif rangespec[0] == 'w': # week
            from_time = midnight - (broken[6]) * 86400
            titles = _("This week"), _("Last week")

        elif rangespec[0] == 'm': # month
            broken[2] = 1
            from_time = time.mktime(broken)
            titles = month_names[broken[1] - 1] + " " + str(broken[0]), \
                     month_names[(broken[1] + 10) % 12] + " " + str(broken[0])

        elif rangespec[0] == 'y': # year
            broken[1:3] = [1, 1]
            from_time = time.mktime(broken)
            titles = str(broken[0]), str(broken[0]-1)

        if rangespec[1] == '0':
            return (from_time, now), titles[0]

        else: # last (previous)
            if rangespec[0] == 'd':
                return (from_time - 86400, from_time), titles[1]
            elif rangespec[0] == 'w':
                return (from_time - 7 * 86400, from_time), titles[1]

            until_time = from_time
            from_broken = list(time.localtime(from_time))
            if rangespec[0] == 'y':
                from_broken[0] -= 1
            else: # m
                from_broken[1] -= 1
                if from_broken[1] == 0:
                    from_broken[1] = 12
                    from_broken[0] -= 1
            return (time.mktime(from_broken), until_time), titles[1]

def get_availability_data(datasource, filterheaders, range, only_sites, limit, timeline):
    has_service = "service" in datasource["infos"]
    av_filter = "Filter: time >= %d\nFilter: time <= %d\n" % range
    if timeline:
        tl_site, tl_host, tl_service = timeline
        av_filter += "Filter: host_name = %s\nFilter: service_description = %s\n" % (
                tl_host, tl_service)
        only_sites = [ tl_site ]
    elif has_service:
        av_filter += "Filter: service_description !=\n"
    else:
        av_filter += "Filter: service_description =\n"


    query = "GET statehist\n" + av_filter

    # Add Columns needed for object identification
    columns = [ "host_name", "host_alias", "service_description" ]

    # Columns for availability
    columns += [
      "duration", "from", "until", "state", "host_down", "in_downtime", 
      "in_host_downtime", "in_notification_period", # "is_flapping", 
      "log_output" ]
    if timeline:
        columns.append("log_output")

    add_columns = datasource.get("add_columns", [])
    rows = do_query_data(query, columns, add_columns, None, filterheaders, only_sites, limit)
    return rows
            

host_availability_columns = [
 ( "up",                        "state0",        _("UP"),       None ),
 ( "down",                      "state2",        _("DOWN"),     None ),
 ( "unreach",                   "state3",        _("UNREACH"),  None ),
 ( "in_downtime",               "downtime",      _("Downtime"), _("The host was in a scheduled downtime") ),
 ( "outof_notification_period", "",              _("OO/Notif"), _("Out of Notification Period") ),
 ( "unmonitored",               "unmonitored",   _("N/A"),      _("During this time period no monitoring data is available") ),
]

service_availability_columns = [
 ( "ok",                        "state0",        _("OK"),       None ),
 ( "warn",                      "state1",        _("WARN"),     None ),
 ( "crit",                      "state2",        _("CRIT"),     None ),
 ( "unknown",                   "state3",        _("UNKNOWN"),  None ),
 ( "host_down",                 "hostdown",      _("H.Down"),   _("The host was down") ),
 ( "in_downtime",               "downtime",      _("Downtime"), _("The host or service was in a scheduled downtime") ),
 ( "outof_notification_period", "",              _("OO/Notif"), _("Out of Notification Period") ),
 ( "unmonitored",               "unmonitored",   _("N/A"),      _("During this time period no monitoring data is available") ),
]

def do_render_availability(datasource, filterheaders, avoptions, only_sites, limit, timeline):
    # Is this a host or a service datasource?
    has_service = "service" in datasource["infos"]

    range, range_title = avoptions["range"]
    rows = get_availability_data(datasource, filterheaders, range, only_sites, limit, timeline)

    # Sort by site/host and service, while keeping native order
    by_host = {}
    for row in rows:
        site_host = row["site"], row["host_name"]
        service = row["service_description"]
        by_host.setdefault(site_host, {})
        by_host[site_host].setdefault(service, []).append(row)

    # Now compute availability table. We have the following possible states:
    # 1. "unmonitored"
    # 2. "monitored"
    #    2.1 "outof_notification_period"
    #    2.2 "in_notification_period"
    #         2.2.1 "in_downtime" (also in_host_downtime)
    #         2.2.2 "not_in_downtime"
    #               2.2.2.1 "host_down"
    #               2.2.2.2 "host not down"
    #                    2.2.2.2.1 "ok"
    #                    2.2.2.2.2 "warn"
    #                    2.2.2.2.3 "crit"
    #                    2.2.2.2.4 "unknown"
    availability = []
    timeline_rows = []
    # Note: in case of timeline, we have data from exacly one host/service
    for site_host, site_host_entry in by_host.iteritems():
        for service, service_entry in site_host_entry.iteritems():
            states = {}
            considered_duration = 0
            for span in service_entry:
                state = span["state"]
                if state == -1:
                    s = "unmonitored"
                    if not avoptions["consider"]["unmonitored"]:
                        considered_duration -= span["duration"]
                elif span["in_notification_period"] == 0 and avoptions["consider"]["notification_period"]:
                    s = "outof_notification_period"
                elif (span["in_downtime"] or span["in_host_downtime"]) and avoptions["consider"]["downtime"]:
                    s = "in_downtime"
                elif span["host_down"] and avoptions["consider"]["host_down"]:
                    s = "host_down"
                else:
                    if has_service:
                        s = { 0: "ok", 1:"warn", 2:"crit", 3:"unknown" }[state]
                    else:
                        s = { 0: "up", 1:"down", 2:"unreach"}[state]
                    if avoptions["state_grouping"]["warn_is_ok"] and s == "warn":
                        s = "ok"
                    elif avoptions["state_grouping"]["unknown_is_crit"] and s == "unknown":
                        s = "crit"
                    # TODO: host_down as crit

                states.setdefault(s, 0)
                states[s] += span["duration"]
                considered_duration += span["duration"]
                if timeline:
                    timeline_rows.append((span, s))
            timeline_considered_duration = considered_duration
            availability.append([site_host[0], site_host[1], service, states, considered_duration])

    # Prepare number format function
    from_time, until_time = range
    duration = until_time - from_time
    timeformat = avoptions["timeformat"]
    if timeformat.startswith("percentage_"):
        def render_number(n, d):
            if not d:
                return _("n/a")
            else:
                return ("%." + timeformat[11:] + "f%%") % ( float(n) / float(d) * 100.0)
    elif timeformat == "seconds":
        def render_number(n, d):
            return "%d s" % n
    elif timeformat == "minutes":
        def render_number(n, d):
            return "%d min" % (n / 60)
    elif timeformat == "hours":
        def render_number(n, d):
            return "%d h" % (n / 3600)
    else:
        def render_number(n, d):
            minn, sec = divmod(n, 60)
            hours, minn = divmod(minn, 60)
            return "%02d:%02d:%02d" % (hours, minn, sec)

    if timeline:
        render_timeline(timeline_rows, from_time, until_time, considered_duration, timeline, range_title, render_number)
    else:
        render_availability_table(availability, from_time, until_time, range_title, has_service, avoptions, render_number)

def render_timeline(timeline_rows, from_time, until_time, considered_duration, timeline, range_title, render_number):
    # More rows with identical state
    merge_timeline(timeline_rows)

    # Timeformat: show date only if the displayed time range spans over
    # more than one day.
    format = "%H:%M:%S"
    if time.localtime(from_time)[:3] != time.localtime(until_time-1)[:3]:
        format = "%Y-%m-%d " + format
    def render_date(ts):
        return time.strftime(format, time.localtime(ts))

    tl_site, tl_host, tl_service = timeline
    title = _("Timeline of") + " " + tl_host
    if tl_service:
        title += ", " + tl_service
        availability_columns = service_availability_columns
    else:
        availability_columns = host_availability_columns
    title += " - " + range_title

    # Render graphical representation
    html.write('<h3>%s</h3>' % title)
    # Make sure that each cell is visible, if possible
    min_percentage = min(100.0 / len(timeline_rows), 1)
    rest_percentage = 100 - len(timeline_rows) * min_percentage
    html.write('<table class=timeline><tr>')
    for row, state_id in timeline_rows:
        for sid, css, sname, help in availability_columns:
            if sid == state_id:
                title = _("From %s until %s (%s) %s") % (
                    render_date(row["from"]), render_date(row["until"]),
                    render_number(row["duration"], considered_duration),
                    sname)
                if row["log_output"]:
                    title += " - " + row["log_output"]
                width = min_percentage + rest_percentage * row["duration"] / considered_duration
                html.write('<td style="width: %.1f%%" title="%s" class="%s"></td>' % (width, title, css))
    html.write('</tr></table>')


    # Render Table
    table.begin(_("Detailed list of states"), css="availability")
    for row, state_id in timeline_rows:
        table.row()
        table.cell(_("From"), render_date(row["from"]), css="nobr narrow")
        table.cell(_("Until"), render_date(row["until"]), css="nobr narrow")
        table.cell(_("Duration"), render_number(row["duration"], considered_duration), css="number")
        for sid, css, sname, help in availability_columns:
            if sid == state_id:
                table.cell(_("State"), sname, css=css + " state narrow")
        table.cell(_("Plugin output"), row["log_output"])

        # table.cell("TEST")
        # html.write(repr(row))
    table.end()


# Merge consecutive rows with same state
def merge_timeline(entries):
    n = 1
    while n < len(entries):
        if entries[n][1] == entries[n-1][1]:
            entries[n-1][0]["duration"] += entries[n][0]["duration"]
            entries[n-1][0]["until"] = entries[n][0]["until"]
            del entries[n]
        else:
            n += 1


def render_availability_table(availability, from_time, until_time, range_title, has_service, avoptions, render_number):
    # Render the stuff
    availability.sort()
    table.begin(_("Availability") + " " + range_title, css="availability")
    for site, host, service, states, considered_duration in availability:
        table.row()
        table.cell("", css="buttons")
        history_url_vars = [
            ("site", site),
            ("host", host),
            ("logtime_from_range", "unix"),  # absolute timestamp
            ("logtime_until_range", "unix"), # absolute timestamp
            ("logtime_from", str(int(from_time))),
            ("logtime_until", str(int(until_time)))]
        if has_service:
            history_url_vars += [
                ("service", service),
                ("view_name", "svcevents"),
            ]
        else:
            history_url_vars += [
                ("view_name", "hostevents"),
            ]

        timeline_url = html.makeuri([
               ("timeline", "yes"), 
               ("timeline_site", site), 
               ("timeline_host", host), 
               ("timeline_service", service)])
        html.icon_button(timeline_url, _("Timeline"), "timeline")
        history_url = "view.py?" + htmllib.urlencode_vars(history_url_vars)
        html.icon_button(history_url, _("Event History"), "history")
        host_url = "view.py?" + htmllib.urlencode_vars([("view_name", "hoststatus"), ("site", site), ("host", host)])
        table.cell(_("Host"), '<a href="%s">%s</a>' % (host_url, host))
        service_url = "view.py?" + htmllib.urlencode_vars([("view_name", "service"), ("site", site), ("host", host), ("service", service)])
        table.cell(_("Service"), '<a href="%s">%s</a>' % (service_url, service))
        if has_service:
            availability_columns = service_availability_columns
        else:
            availability_columns = host_availability_columns
        for sid, css, sname, help in availability_columns:
            if sid == "outof_notification_period" and not avoptions["consider"]["notification_period"]:
                continue
            elif sid == "in_downtime" and not avoptions["consider"]["downtime"]:
                continue
            elif sid == "host_down" and not avoptions["consider"]["host_down"]:
                continue
            elif sid == "unmonitored" and not avoptions["consider"]["unmonitored"]:
                continue
            elif sid == "warn" and avoptions["state_grouping"]["warn_is_ok"]:
                continue
            elif sid == "unknown" and avoptions["state_grouping"]["unknown_is_crit"]:
                continue
            number = states.get(sid, 0)
            if not number:
                css = ""
            table.cell(sname, render_number(number, considered_duration), css="number " + css, help=help)
    table.end()



# Av Options:
# Zeitspannen < X Minuten nicht werten
# Verhalten bei Flapping
