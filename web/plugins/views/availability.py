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

    if handle_edit_annotations():
        return

    # We need the availability options now, but cannot display the
    # form code for that yet.
    html.plug()
    avoptions = render_availability_options()
    range, range_title = avoptions["range"]
    avoptions_html = html.drain()
    html.unplug()

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
    title += " - " + range_title

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
        if timeline:
            html.context_button(_("Availability"), html.makeuri([("timeline", "")]), "availability")
            history_url = history_url_of(tl_site, tl_host, tl_service, range[0], range[1])
            html.context_button(_("History"), history_url, "history")
        html.end_context_buttons()

    html.write(avoptions_html)

    if not html.has_user_errors():
        rows = get_availability_data(datasource, filterheaders, range, only_sites,
                                     limit, timeline, timeline or avoptions["show_timeline"], avoptions)
        what = "service" in datasource["infos"] and "service" or "host"
        do_render_availability(rows, what, avoptions, timeline, "")

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

  # Labelling and Texts
  ( "labelling",
    "double",
    ListChoice(
        title = _("Labelling Options"),
        choices = [
            ( "omit_host",               _("Do not display the host name")),
            ( "use_display_name",        _("Use alternative display name for services")),
            ( "omit_buttons",            _("Do not display icons for history and timeline")),
            ( "display_timeline_legend", _("Display legend for timeline")),
        ]
    )
  ),

  # How to deal with downtimes
  ( "downtimes",
    "double",
    Dictionary(
        title = _("Scheduled Downtimes"),
        columns = 2,
        elements = [
            ( "include",
              DropdownChoice(
                  choices = [
                    ( "honor", _("Honor scheduled downtimes") ),
                    ( "ignore", _("Ignore scheduled downtimes") ),
                    ( "exclude", _("Exclude scheduled downtimes" ) ),
                 ]
              )
            ),
            ( "exclude_ok",
              Checkbox(label = _("Treat phases of UP/OK as non-downtime"))
            ),
        ],
        optional_keys = False,
    )
  ),

  # How to deal with downtimes, etc.
  ( "consider",
    "double",
    Dictionary(
       title = _("Status Classification"),
       columns = 2,
       elements = [
           ( "flapping",
              Checkbox(label = _("Consider periods of flapping states")),
           ),
           ( "host_down",
              Checkbox(label = _("Consider times where the host is down")),
           ),
           ( "unmonitored",
              Checkbox(label = _("Include unmonitored time")),
           ),
       ],
       optional_keys = False,
    ),
  ),

  # Optionally group some states together
  ( "state_grouping",
    "double",
    Dictionary(
       title = _("Status Grouping"),
       columns = 2,
       elements = [
           ( "warn",
              DropdownChoice(
                  label = _("Treat Warning as: "),
                  choices = [
                    ( "ok",      _("OK") ),
                    ( "warn",    _("WARN") ),
                    ( "crit",    _("CRIT") ),
                    ( "unknown", _("UNKNOWN") ),
                  ]
                ),
           ),
           ( "unknown",
              DropdownChoice(
                  label = _("Treat Unknown as: "),
                  choices = [
                    ( "ok",      _("OK") ),
                    ( "warn",    _("WARN") ),
                    ( "crit",    _("CRIT") ),
                    ( "unknown", _("UNKNOWN") ),
                  ]
                ),
           ),
           ( "host_down",
              DropdownChoice(
                  label = _("Treat Host Down as: "),
                  choices = [
                    ( "ok",        _("OK") ),
                    ( "warn",      _("WARN") ),
                    ( "crit",      _("CRIT") ),
                    ( "unknown",   _("UNKNOWN") ),
                    ( "host_down", _("Host Down") ),
                  ]
                ),
           ),
       ],
       optional_keys = False,
    ),
  ),

  # Visual levels for the availability
  ( "av_levels",
    "double",
    Optional(
        Tuple(
            elements = [
                Percentage(title = _("Warning below"), default_value = 99, display_format="%.3f", size=7),
                Percentage(title = _("Critical below"), default_value = 95, display_format="%.3f", size=7),
            ]
        ),
        title = _("Visual levels for the availability (OK percentage)"),
    )
  ),


  # Show colummns for min, max, avg duration and count
  ( "outage_statistics",
    "double",
    Tuple(
        title = _("Outage statistics"),
        orientation = "horizontal",
        elements = [
            ListChoice(
                title = _("Aggregations"),
                choices = [
                  ( "min", _("minimum duration" )),
                  ( "max", _("maximum duration" )),
                  ( "avg", _("average duration" )),
                  ( "cnt", _("count" )),
                ]
            ),
            ListChoice(
                title = _("For these states:"),
                columns = 2,
                choices = [
                    ( "ok",                        _("OK/Up") ),
                    ( "warn",                      _("Warn") ),
                    ( "crit",                      _("Crit/Down") ),
                    ( "unknown",                   _("Unknown/Unreach") ),
                    ( "flapping",                  _("Flapping") ),
                    ( "host_down",                 _("Host Down") ),
                    ( "in_downtime",               _("Downtime") ),
                    ( "outof_notification_period", _("OO/Notif") ),
                ]
            )
        ]
    )
  ),

  # Omit all non-OK columns
  ( "av_mode",
    "single",
    Checkbox(
        title = _("Availability"),
        label = _("Just show the availability (i.e. OK/UP)"),
    ),
  ),

  # How to deal with the service periods
  ( "service_period",
    "single",
     DropdownChoice(
         title = _("Service Time"),
         choices = [
            ( "honor",    _("Base report only on service times") ),
            ( "ignore",   _("Include both service and non-service times" ) ),
            ( "exclude",  _("Base report only on non-service times" ) ),
         ]
     )
  ),

  # How to deal with times out of the notification period
  ( "notification_period",
    "single",
     DropdownChoice(
         title = _("Notification Period"),
         choices = [
            ( "honor", _("Distinguish times in and out of notification period") ),
            ( "exclude", _("Exclude times out of notification period" ) ),
            ( "ignore", _("Ignore notification period") ),
         ]
     )
  ),

  # Group by Host, Hostgroup or Servicegroup?
  ( "grouping",
    "single",
    DropdownChoice(
        title = _("Grouping"),
        choices = [
          ( None,             _("Do not group") ),
          ( "host",           _("By Host")       ),
          ( "host_groups",    _("By Host group") ),
          ( "service_groups", _("By Service group") ),
        ]
    )
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


  # Short time intervals
  ( "short_intervals",
    "single",
    Integer(
        title = _("Short Time Intervals"),
        minvalue = 0,
        unit = _("sec"),
        label = _("Ignore intervals shorter or equal"),
    ),
  ),

  # Merging
  ( "dont_merge",
    "single",
    Checkbox(
        title = _("Phase Merging"),
        label = _("Do not merge consecutive phases with equal state")),
  ),

  # Summary line
  ( "summary",
    "single",
    DropdownChoice(
        title = _("Summary line"),
        choices = [
            ( None,      _("Do not show a summary line") ),
            ( "sum",     _("Display total sum (for % the average)") ),
            ( "average", _("Display average") ),
        ],
        default_value = sum,
    )
  ),

  # Timeline
  ( "show_timeline",
    "single",
    Checkbox(
        title = _("Timeline"),
        label = _("Show timeline of each object directly in table")),
  ),

  # Timelimit
  ( "timelimit",
    "single",
    Age(
        title = _("Query Time Limit"),
        default_value = 30,
        unit = _("sec"),
        help = _("Limit the execution time of the query, in order to "
                 "avoid a hanging system."),
    ),
   )
]


def render_availability_options():
    if html.var("_reset") and html.check_transaction():
        config.save_user_file("avoptions", {})
        for varname in html.vars.keys():
            if varname.startswith("avo_"):
                html.del_var(varname)
            html.del_var("avoptions")

    avoptions = {
        "range"          : (time.time() - 86400, time.time()),
        "downtimes"      : {
            "include" : "honor",
            "exclude_ok" : False,
        },
        "notification_period" : "ignore",
        "service_period"      : "honor",
        "consider"       : {
            "flapping"            : True,
            "host_down"           : True,
            "unmonitored"         : True,
        },
        "timeformat"     : "percentage_2",
        "labelling"      : [],
        "rangespec"      : "d0",
        "state_grouping" : {
            "warn"      : "warn",
            "unknown"   : "unknown",
            "host_down" : "host_down",
        },
        "outage_statistics" : ([],[]),
        "short_intervals"   : 0,
        "dont_merge"        : False,
        "show_timeline"     : False,
        "summary"           : "sum",
        "av_levels"         : None,
        "av_mode"           : False,
        "grouping"          : None,
        "timelimit"         : 30,
    }

    # Users of older versions might not have all keys set. The following
    # trick will merge their options with our default options.
    avoptions.update(config.load_user_file("avoptions", {}))

    is_open = False
    html.begin_form("avoptions")
    html.hidden_field("avoptions", "set")
    if html.var("avoptions") == "set":
        for name, height, vs in avoption_entries:
            try:
                avoptions[name] = vs.from_html_vars("avo_" + name)
            except MKUserError, e:
                html.add_user_error(e.varname, e.message)
                is_open = True

    try:
        range, range_title = compute_range(avoptions["rangespec"])
        avoptions["range"] = range, range_title
    except MKUserError, e:
        html.add_user_error(e.varname, e.message)

    if html.has_user_errors():
        html.show_user_errors()

    html.write('<div class="view_form" id="avoptions" %s>'
            % (not is_open and 'style="display: none"' or '') )
    html.write("<table border=0 cellspacing=0 cellpadding=0 class=filterform><tr><td>")

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

month_names = [
  _("January"),   _("February"), _("March"),    _("April"),
  _("May"),       _("June"),     _("July"),     _("August"),
  _("September"), _("October"),  _("November"), _("December")
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
            last_year = broken[0] - ((broken[1] == 1) and 1 or 0)
            titles = month_names[broken[1] - 1] + " " + str(broken[0]), \
                     month_names[(broken[1] + 10) % 12] + " " + str(last_year)

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

def get_availability_data(datasource, filterheaders, range, only_sites, limit, single_object, include_output, avoptions):
    has_service = "service" in datasource["infos"]
    av_filter = "Filter: time >= %d\nFilter: time <= %d\n" % range
    if single_object:
        tl_site, tl_host, tl_service = single_object
        av_filter += "Filter: host_name = %s\nFilter: service_description = %s\n" % (
                tl_host, tl_service)
        only_sites = [ tl_site ]
    elif has_service:
        av_filter += "Filter: service_description !=\n"
    else:
        av_filter += "Filter: service_description =\n"

    query = "GET statehist\n" + av_filter
    query += "Timelimit: %d\n" % avoptions["timelimit"]

    # Add Columns needed for object identification
    columns = [ "host_name", "service_description" ]

    # Columns for availability
    columns += [
      "duration", "from", "until", "state", "host_down", "in_downtime",
      "in_host_downtime", "in_notification_period", "in_service_period", "is_flapping", ]
    if include_output:
        columns.append("log_output")
    if "use_display_name" in avoptions["labelling"]:
        columns.append("service_display_name")

    # If we group by host/service group then make sure that that information is available
    if avoptions["grouping"] not in [ None, "host" ]:
        columns.append(avoptions["grouping"])

    add_columns = datasource.get("add_columns", [])
    rows = do_query_data(query, columns, add_columns, None, filterheaders, only_sites, limit = None)
    return rows


host_availability_columns = [
 ( "up",                        "state0",        _("UP"),       None ),
 ( "down",                      "state2",        _("DOWN"),     None ),
 ( "unreach",                   "state3",        _("UNREACH"),  None ),
 ( "flapping",                  "flapping",      _("Flapping"), None ),
 ( "in_downtime",               "downtime",      _("Downtime"), _("The host was in a scheduled downtime") ),
 ( "outof_notification_period", "",              _("OO/Notif"), _("Out of Notification Period") ),
 ( "outof_service_period",      "ooservice",     _("OO/Service"), _("Out of Service Period") ),
 ( "unmonitored",               "unmonitored",   _("N/A"),      _("During this time period no monitoring data is available") ),
]

service_availability_columns = [
 ( "ok",                        "state0",        _("OK"),       None ),
 ( "warn",                      "state1",        _("WARN"),     None ),
 ( "crit",                      "state2",        _("CRIT"),     None ),
 ( "unknown",                   "state3",        _("UNKNOWN"),  None ),
 ( "flapping",                  "flapping",      _("Flapping"), None ),
 ( "host_down",                 "hostdown",      _("H.Down"),   _("The host was down") ),
 ( "in_downtime",               "downtime",      _("Downtime"), _("The host or service was in a scheduled downtime") ),
 ( "outof_notification_period", "",              _("OO/Notif"), _("Out of Notification Period") ),
 ( "outof_service_period",      "ooservice",     _("OO/Service"), _("Out of Service Period") ),
 ( "unmonitored",               "unmonitored",   _("N/A"),      _("During this time period no monitoring data is available") ),
]

bi_availability_columns = [
 ( "ok",                        "state0",        _("OK"),       None ),
 ( "warn",                      "state1",        _("WARN"),     None ),
 ( "crit",                      "state2",        _("CRIT"),     None ),
 ( "unknown",                   "state3",        _("UNKNOWN"),  None ),
 ( "unmonitored",               "unmonitored",   _("N/A"),      _("During this time period no monitoring data is available") ),
]


def do_render_availability(rows, what, avoptions, timeline, timewarpcode):
    # Sort by site/host and service, while keeping native order
    by_host = {}
    for row in rows:
        site_host = row["site"], row["host_name"]
        service = row["service_description"]
        by_host.setdefault(site_host, {})
        by_host[site_host].setdefault(service, []).append(row)

    # Load annotations
    annotations = load_annotations()

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
    os_aggrs, os_states = avoptions.get("outage_statistics", ([],[]))
    need_statistics = os_aggrs and os_states
    show_timeline = avoptions["show_timeline"] or timeline
    grouping = avoptions["grouping"]
    timeline_rows = [] # Need this as a global variable if just one service is affected
    total_duration = 0
    considered_duration = 0

    # Note: in case of timeline, we have data from exacly one host/service
    for site_host, site_host_entry in by_host.iteritems():
        for service, service_entry in site_host_entry.iteritems():

            if grouping == "host":
                group_ids = [site_host]
            elif grouping:
                group_ids = set([])
            else:
                group_ids = None

            # First compute timeline
            timeline_rows = []
            total_duration = 0
            considered_duration = 0
            for span in service_entry:
                # Information about host/service groups are in the actual entries
                if grouping and grouping != "host":
                    group_ids.update(span[grouping]) # List of host/service groups

                display_name = span.get("service_display_name", service)
                state = span["state"]
                consider = True

                if state == -1:
                    s = "unmonitored"
                    if not avoptions["consider"]["unmonitored"]:
                        consider = False

                elif avoptions["service_period"] != "ignore" and \
                    (( span["in_service_period"] and avoptions["service_period"] != "honor" )
                    or \
                    ( not span["in_service_period"] and avoptions["service_period"] == "honor" )):
                    s = "outof_service_period"
                    consider = False

                elif span["in_notification_period"] == 0 and avoptions["notification_period"] == "exclude":
                    consider = False

                elif span["in_notification_period"] == 0 and avoptions["notification_period"] == "honor":
                    s = "outof_notification_period"

                elif (span["in_downtime"] or span["in_host_downtime"]) and not \
                    (avoptions["downtimes"]["exclude_ok"] and state == 0) and not \
                    avoptions["downtimes"]["include"] == "ignore":
                    if avoptions["downtimes"]["include"] == "exclude":
                        consider = False
                    else:
                        s = "in_downtime"
                elif what != "host" and span["host_down"] and avoptions["consider"]["host_down"]:
                    s = "host_down"
                elif span["is_flapping"] and avoptions["consider"]["flapping"]:
                    s = "flapping"
                else:
                    if what in [ "service", "bi" ]:
                        s = { 0: "ok", 1:"warn", 2:"crit", 3:"unknown" }.get(state, "unmonitored")
                    else:
                        s = { 0: "up", 1:"down", 2:"unreach" }.get(state, "unmonitored")
                    if s == "warn":
                        s = avoptions["state_grouping"]["warn"]
                    elif s == "unknown":
                        s = avoptions["state_grouping"]["unknown"]
                    elif s == "host_down":
                        s = avoptions["state_grouping"]["host_down"]

                total_duration += span["duration"]
                if consider:
                    timeline_rows.append((span, s))
                    considered_duration += span["duration"]

            # Now merge consecutive rows with identical state
            if not avoptions["dont_merge"]:
                merge_timeline(timeline_rows)

            # Melt down short intervals
            if avoptions["short_intervals"]:
                melt_short_intervals(timeline_rows, avoptions["short_intervals"], avoptions["dont_merge"])

            # Condense into availability
            states = {}
            statistics = {}
            for span, s in timeline_rows:
                states.setdefault(s, 0)
                duration = span["duration"]
                states[s] += duration
                if need_statistics:
                    entry = statistics.get(s)
                    if entry:
                        entry[0] += 1
                        entry[1] = min(entry[1], duration)
                        entry[2] = max(entry[2], duration)
                    else:
                        statistics[s] = [ 1, duration, duration ] # count, min, max

            if not show_timeline:
                timeline_rows = None

            availability.append([site_host[0], site_host[1], service, display_name, states,
                                considered_duration, total_duration, statistics, timeline_rows, group_ids])

    # Prepare number format function
    range, range_title = avoptions["range"]
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
        render_timeline(timeline_rows, from_time, until_time, total_duration,
                        timeline, range_title, render_number, what, timewarpcode, avoptions, style="standalone")
    else:
        render_availability_table(availability, from_time, until_time, range_title, what, avoptions, render_number)

    render_annotations(annotations, from_time, until_time, by_host, what, avoptions, omit_service = timeline)


# style is either inline (just the timeline bar) or "standalone" (the complete page)
def render_timeline(timeline_rows, from_time, until_time, considered_duration,
                    timeline, range_title, render_number, what, timewarpcode, avoptions, style):
    if not timeline_rows:
        html.write('<div class=info>%s</div>' % _("No information available"))
        return

    # Timeformat: show date only if the displayed time range spans over
    # more than one day.
    format = "%H:%M:%S"
    if time.localtime(from_time)[:3] != time.localtime(until_time-1)[:3]:
        format = "%Y-%m-%d " + format
    def render_date(ts):
        return time.strftime(format, time.localtime(ts))

    if type(timeline) == tuple:
        tl_site, tl_host, tl_service = timeline
        if tl_service:
            availability_columns = service_availability_columns
        else:
            availability_columns = host_availability_columns
    else:
        availability_columns = bi_availability_columns

    # Render graphical representation
    # Make sure that each cell is visible, if possible
    min_percentage = min(100.0 / len(timeline_rows), style == "inline" and 0.1 or 0.5)
    rest_percentage = 100 - len(timeline_rows) * min_percentage
    html.write('<div class="timelinerange %s">' % style)
    if style == "standalone":
        html.write('<div class=from>%s</div><div class=until>%s</div></div>' % (
            render_date(from_time), render_date(until_time)))

    html.write('<table class="timeline %s">' % style)
    html.write('<tr class=timeline>')
    for row_nr, (row, state_id) in enumerate(timeline_rows):
        for sid, css, sname, help in availability_columns:
            if sid == state_id:
                title = _("From %s until %s (%s) %s") % (
                    render_date(row["from"]), render_date(row["until"]),
                    render_number(row["duration"], considered_duration),
                    help and help or sname)
                if row["log_output"]:
                    title += " - " + row["log_output"]
                width = min_percentage + rest_percentage * row["duration"] / considered_duration
                html.write('<td onmouseover="timeline_hover(%d, 1);" onmouseout="timeline_hover(%d, 0);" '
                           'style="width: %.1f%%" title="%s" class="%s"></td>' % (
                           row_nr, row_nr, width, html.attrencode(title), css))
    html.write('</tr></table>')

    if style == "inline":
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
        for sid, css, sname, help in availability_columns:
            if sid == state_id:
                table.cell(_("State"), sname, css=css + " state narrow")
                break
        else:
            table.cell(_("State"), "(%s/%s)" % (sid,sname))
        table.cell(_("Additional information"), row["log_output"])

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
        title = "%s %d" % (month_names[broken[1]-1], broken[0])

    dst = broken[8]
    if old_dst == 1 and dst == 0:
        epoch += 3600
    elif old_dst == 0 and dst == 1:
        epoch -= 3600
    return epoch, title





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

def melt_short_intervals(entries, duration, dont_merge):
    n = 1
    need_merge = False
    while n < len(entries) - 1:
        if entries[n][0]["duration"] <= duration and \
            entries[n-1][1] == entries[n+1][1]:
            entries[n] = (entries[n][0], entries[n-1][1])
            need_merge = True
        n += 1

    # Due to melting, we need to merge again
    if need_merge and not dont_merge:
        merge_timeline(entries)
        melt_short_intervals(entries, duration, dont_merge)

def history_url_of(site, host, service, from_time, until_time):
    history_url_vars = [
        ("site", site),
        ("host", host),
        ("logtime_from_range", "unix"),  # absolute timestamp
        ("logtime_until_range", "unix"), # absolute timestamp
        ("logtime_from", str(int(from_time))),
        ("logtime_until", str(int(until_time)))]
    if service:
        history_url_vars += [
            ("service", service),
            ("view_name", "svcevents"),
        ]
    else:
        history_url_vars += [
            ("view_name", "hostevents"),
        ]

    return "view.py?" + html.urlencode_vars(history_url_vars)

statistics_headers = {
    "min" : _("Shortest"),
    "max" : _("Longest"),
    "avg" : _("Average"),
    "cnt" : _("Count"),
}

def render_availability_table(availability, from_time, until_time, range_title, what, avoptions, render_number):
    if not availability:
        html.message(_("No matching hosts/services."))
        return # No objects

    grouping = avoptions["grouping"]

    if not grouping:
        render_availability_group(range_title, range_title, None, availability, from_time, until_time, what, avoptions, render_number)

    else:
        # Grouping is one of host/hostgroup/servicegroup
        # 1. Get complete list of all groups
        all_group_ids = get_av_groups(availability, grouping)

        # 2. Compute Names for the groups and sort according to these names
        if grouping != "host":
            group_titles = dict(all_groups(grouping[:-7]))

        titled_groups = []
        for group_id in all_group_ids:
            if grouping == "host":
                titled_groups.append((group_id[1], group_id)) # omit the site name
            else:
                if group_id == ():
                    title = _("Not contained in any group")
                else:
                    title = group_titles.get(group_id, group_id)
                titled_groups.append((title, group_id)) ## ACHTUNG
        titled_groups.sort(cmp = lambda a,b: cmp(a[1], b[1]))

        # 3. Loop over all groups and render them
        for title, group_id in titled_groups:
            render_availability_group(title, range_title, group_id, availability, from_time, until_time, what, avoptions, render_number)

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


def get_av_groups(availability, grouping):
    all_group_ids = set([])
    for site, host, service, display_name, states, considered_duration, total_duration, statistics, timeline_rows, group_ids in availability:
        all_group_ids.update(group_ids)
        if len(group_ids) == 0:
            all_group_ids.add(()) # null-tuple denotes ungrouped objects
    return all_group_ids


# When grouping is enabled, this function is called once for each group
def render_availability_group(group_title, range_title, group_id, availability, from_time, until_time, what, avoptions, render_number):

    # Filter out groups that we want to show this time
    group_availability = []
    for entry  in availability:
        group_ids = entry[-1]
        if group_id == () and group_ids:
            continue # This is not an angrouped object
        elif group_id and group_id not in group_ids:
            continue # Not this group
        group_availability.append(entry)

    # Some columns might be unneeded due to state treatment options
    sg = avoptions["state_grouping"]
    state_groups = [ sg["warn"], sg["unknown"], sg["host_down"] ]

    show_timeline = avoptions["show_timeline"]
    labelling = avoptions["labelling"]
    av_levels = avoptions["av_levels"]

    # Helper function, needed in row and in summary line
    def cell_active(sid):
        if sid not in [ "up", "ok" ] and avoptions["av_mode"]:
            return False
        if sid == "outof_notification_period" and avoptions["notification_period"] != "honor":
            return False
        elif sid == "outof_service_period": # Never show this as a column
            return False
        elif sid == "in_downtime" and avoptions["downtimes"]["include"] != "honor":
            return False
        elif sid == "unmonitored" and not avoptions["consider"]["unmonitored"]:
            return False
        elif sid == "flapping" and not avoptions["consider"]["flapping"]:
            return False
        elif sid in [ "warn", "unknown", "host_down" ] and sid not in state_groups:
            return False
        else:
            return True

    # Render the stuff
    availability.sort()
    show_summary = what != "bi" and avoptions.get("summary")
    summary = {}
    summary_counts = {}
    table.begin("av_items", group_title, css="availability",
        searchable = False, limit = None)
    for site, host, service, display_name, states, considered_duration, total_duration, statistics, timeline_rows, group_ids in group_availability:
        table.row()

        if what != "bi":
            timeline_url = html.makeuri([
                   ("timeline", "yes"),
                   ("timeline_site", site),
                   ("timeline_host", host),
                   ("timeline_service", service)])

            if not "omit_buttons" in labelling:
                table.cell("", css="buttons")
                history_url = history_url_of(site, host, service, from_time, until_time)
                html.icon_button(history_url, _("Event History"), "history")
                html.icon_button(timeline_url, _("Timeline"), "timeline")
        else:
            timeline_url = html.makeuri([("timeline", "1")])

        host_url = "view.py?" + html.urlencode_vars([("view_name", "hoststatus"), ("site", site), ("host", host)])
        if what == "bi":
            bi_url = "view.py?" + html.urlencode_vars([("view_name", "aggr_single"), ("aggr_name", service)])
            table.cell(_("Aggregate"), '<a href="%s">%s</a>' % (bi_url, service))
            availability_columns = bi_availability_columns
        else:
            if not "omit_host" in labelling:
                table.cell(_("Host"), '<a href="%s">%s</a>' % (host_url, host))
            if what == "service":
                service_url = "view.py?" + html.urlencode_vars([("view_name", "service"), ("site", site), ("host", host), ("service", service)])
                if "use_display_name" in labelling:
                    service_name = display_name
                else:
                    service_name = service
                table.cell(_("Service"), '<a href="%s">%s</a>' % (service_url, service_name))
                availability_columns = service_availability_columns
            else:
                availability_columns = host_availability_columns

        if show_timeline:
            table.cell(_("Timeline"), css="timeline")
            html.write('<a href="%s">' % timeline_url)
            render_timeline(timeline_rows, from_time, until_time, total_duration, (site, host, service), range_title, render_number, what, "", avoptions, style="inline")
            html.write('</a>')

        for sid, css, sname, help in availability_columns:
            if not cell_active(sid):
                continue
            if avoptions["av_mode"]:
                sname = _("Avail.")

            number = states.get(sid, 0)
            if not number:
                css = "unused"
            elif show_summary:
                summary.setdefault(sid, 0.0)
                if avoptions["timeformat"].startswith("percentage"):
                    if considered_duration > 0:
                        summary[sid] += float(number) / considered_duration
                else:
                    summary[sid] += number

            # Apply visual availability levels (render OK in yellow/red, if too low)
            if number and av_levels and sid in [ "ok", "up" ]:
                css = "state%d" % check_av_levels(number, av_levels, considered_duration)
            table.cell(sname, render_number(number, considered_duration), css="narrow number " + css, help=help)

            # Statistics?
            x_cnt, x_min, x_max = statistics.get(sid, (None, None, None))
            os_aggrs, os_states = avoptions.get("outage_statistics", ([],[]))
            if sid in os_states:
                for aggr in os_aggrs:
                    title = statistics_headers[aggr]
                    if x_cnt != None:
                        if aggr == "avg":
                            r = render_number(number / x_cnt, considered_duration)
                        elif aggr == "min":
                            r = render_number(x_min, considered_duration)
                        elif aggr == "max":
                            r = render_number(x_max, considered_duration)
                        else:
                            r = str(x_cnt)
                            summary_counts.setdefault(sid, 0)
                            summary_counts[sid] += x_cnt
                        table.cell(title, r, css="number stats " + css)
                    else:
                        table.cell(title, "")



    if show_summary:
        table.row(css="summary")
        if not "omit_buttons" in labelling:
            table.cell("")
        if not "omit_host" in labelling:
            table.cell("", _("Summary"))
        if what == "service":
            table.cell("", "")

        if show_timeline:
            table.cell("")

        for sid, css, sname, help in availability_columns:
            if not cell_active(sid):
                continue
            number = summary.get(sid, 0)
            if show_summary == "average" or avoptions["timeformat"].startswith("percentage"):
                number /= len(group_availability)
                if avoptions["timeformat"].startswith("percentage"):
                    number *= considered_duration
            if not number:
                css = "unused"

            if number and av_levels and sid in [ "ok", "up" ]:
                css = "state%d" % check_av_levels(number, av_levels, considered_duration)
            table.cell(sname, render_number(number, considered_duration), css="number " + css, help=help)
            os_aggrs, os_states = avoptions.get("outage_statistics", ([],[]))
            if sid in os_states:
                for aggr in os_aggrs:
                    title = statistics_headers[aggr]
                    if aggr == "cnt":
                        count = summary_counts.get(sid, 0)
                        if show_summary == "average":
                            count = float(count) / len(group_availability)
                            text = "%.2f" % count
                        else:
                            text = str(count)
                        table.cell(sname, text, css="number stats " + css, help=help)
                    else:
                        table.cell(title, "")

    table.end()

def check_av_levels(number, av_levels, considered_duration):
    if considered_duration == 0:
        return 0

    perc = 100 * float(number) / float(considered_duration)
    warn, crit = av_levels
    if perc < crit:
        return 2
    elif perc < warn:
        return 1
    else:
        return 0



# Render availability of an BI aggregate. This is currently
# no view and does not support display options
def render_bi_availability(tree):
    reqhosts = tree["reqhosts"]
    timeline = html.var("timeline")
    title = _("Availability of ") + tree["title"]
    html.body_start(title, stylesheets=["pages","views","status", "bi"], javascripts=['bi'])
    html.top_heading(title)
    html.begin_context_buttons()
    togglebutton("avoptions", False, "painteroptions", _("Configure details of the report"))
    html.context_button(_("Status View"), "view.py?" +
            html.urlencode_vars([("view_name", "aggr_single"),
              ("aggr_name", tree["title"])]), "showbi")
    if timeline:
        html.context_button(_("Availability"), html.makeuri([("timeline", "")]), "availability")
    else:
        html.context_button(_("Timeline"), html.makeuri([("timeline", "1")]), "timeline")
    html.end_context_buttons()

    avoptions = render_availability_options()
    if not html.has_user_errors():
        try:
            timewarp = int(html.var("timewarp"))
        except:
            timewarp = None
        rows, tree_state = get_bi_timeline(tree, avoptions, timewarp)
        if timewarp:
            state, assumed_state, node, subtrees = tree_state
            eff_state = state
            if assumed_state != None:
                eff_state = assumed_state
            row = {
                    "aggr_tree"            : tree,
                    "aggr_treestate"       : tree_state,
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
            html.icon_button(html.makeuri([("timewarp", "")]), _("Close Timewarp"), "close")
            timewarpcode = html.drain()
            html.unplug()
            timewarpcode += '%s %s</h3>' % (_("Timewarp to "), time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timewarp))) + \
                           '<table class="data table timewarp"><tr class="data odd0"><td class="%s">' % tdclass + \
                           htmlcode + \
                           '</td></tr></table>'
        else:
            timewarpcode = ""
        do_render_availability(rows, "bi", avoptions, timeline, timewarpcode)

    html.bottom_footer()
    html.body_end()

def get_bi_timeline(tree, avoptions, timewarp):
    range, range_title = avoptions["range"]
    # Get state history of all hosts and services contained in the tree.
    # In order to simplify the query, we always fetch the information for
    # all hosts of the aggregates.
    only_sites = set([])
    hosts = []
    for site, host in tree["reqhosts"]:
        only_sites.add(site)
        hosts.append(host)

    columns = [ "host_name", "service_description", "from", "log_output", "state" ]
    html.live.set_only_sites(list(only_sites))
    html.live.set_prepend_site(True)
    html.live.set_limit() # removes limit
    query = "GET statehist\n" + \
            "Columns: " + " ".join(columns) + "\n" +\
            "Filter: time >= %d\nFilter: time <= %d\n" % range

    for host in hosts:
        query += "Filter: host_name = %s\n" % host
    query += "Or: %d\n" % len(hosts)
    data = html.live.query(query)
    html.live.set_prepend_site(False)
    html.live.set_only_sites(None)
    columns = ["site"] + columns
    rows = [ dict(zip(columns, row)) for row in data ]

    # Now comes the tricky part: recompute the state of the aggregate
    # for each step in the state history and construct a timeline from
    # it. As a first step we need the start state for each of the
    # hosts/services. They will always be the first consecute rows
    # in the statehist table

    # First partition the rows into sequences with equal start time
    phases = {}
    for row in rows:
        from_time = row["from"]
        phases.setdefault(from_time, []).append(row)

    # Convert phases to sorted list
    sorted_times = phases.keys()
    sorted_times.sort()
    phases_list = []
    for from_time in sorted_times:
        phases_list.append((from_time, phases[from_time]))

    states = {}
    def update_states(phase_entries):
        for row in phase_entries:
            service = row["service_description"]
            key = row["site"], row["host_name"], service
            states[key] = row["state"], row["log_output"]


    update_states(phases_list[0][1])
    # states does now reflect the host/services states at the beginning
    # of the query range.
    tree_state = compute_tree_state(tree, states)
    tree_time = range[0]
    if timewarp == int(tree_time):
        timewarp_state = tree_state
    else:
        timewarp_state = None

    timeline = []
    def append_to_timeline(from_time, until_time, tree_state):
        timeline.append({"state" : tree_state[0]['state'],
                         "log_output" : tree_state[0]['output'],
                         "from" : from_time,
                         "until" : until_time,
                         "site" : "",
                         "host_name" : "",
                         "service_description" : tree['title'],
                         "in_notification_period" : 1,
                         "in_service_period" : 1,
                         "in_downtime" : 0,
                         "in_host_downtime" : 0,
                         "host_down" : 0,
                         "is_flapping" : 0,
                         "duration" : until_time - from_time,
        })


    for from_time, phase in phases_list[1:]:
        update_states(phase)
        next_tree_state = compute_tree_state(tree, states)
        duration = from_time - tree_time
        append_to_timeline(tree_time, from_time, tree_state)
        tree_state = next_tree_state
        tree_time = from_time
        if timewarp == tree_time:
            timewarp_state = tree_state

    # Add one last entry - for the state until the end of the interval
    append_to_timeline(tree_time, range[1], tree_state)

    return timeline, timewarp_state

def compute_tree_state(tree, status):
    # Convert our status format into that needed by BI
    services_by_host = {}
    hosts = {}
    for site_host_service, state_output in status.items():
        site_host = site_host_service[:2]
        service = site_host_service[2]
        if service:
            services_by_host.setdefault(site_host, []).append((
                service, state_output[0], 1, state_output[1]))
        else:
            hosts[site_host] = state_output

    status_info = {}
    for site_host, state_output in hosts.items():
        status_info[site_host] = [
            state_output[0],
            state_output[1],
            services_by_host[site_host]
        ]


    # Finally we can execute the tree
    bi.load_assumptions()
    tree_state = bi.execute_tree(tree, status_info)
    return tree_state

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


def render_annotations(annotations, from_time, until_time, by_host, what, avoptions, omit_service):
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


