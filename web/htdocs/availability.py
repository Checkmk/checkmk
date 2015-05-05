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

import bi, views

#   .--Computation---------------------------------------------------------.
#   |      ____                            _        _   _                  |
#   |     / ___|___  _ __ ___  _ __  _   _| |_ __ _| |_(_) ___  _ __       |
#   |    | |   / _ \| '_ ` _ \| '_ \| | | | __/ _` | __| |/ _ \| '_ \      |
#   |    | |__| (_) | | | | | | |_) | |_| | || (_| | |_| | (_) | | | |     |
#   |     \____\___/|_| |_| |_| .__/ \__,_|\__\__,_|\__|_|\___/|_| |_|     |
#   |                         |_|                                          |
#   +----------------------------------------------------------------------+
#   |  Computation of availability data into abstract data structures.     |
#   |  These are being used for rendering in HTML and also for the re-     |
#   |  porting module. Could also be a source for exporting data into      |
#   |  files like CSV or spread sheets.                                    |
#   |                                                                      |
#   |  This code might be moved to another file.                           |
#   '----------------------------------------------------------------------'

# Get raw availability data via livestatus. The result is a list
# of spans. Each span is a dictionary that describes one span of time where
# a specific host or service has one specific state.
# what is either "host" or "service"
def get_availability_rawdata(what, filterheaders, time_range, only_sites, single_object, include_output, avoptions):
    av_filter = "Filter: time >= %d\nFilter: time < %d\n" % time_range
    if single_object:
        tl_site, tl_host, tl_service = single_object
        av_filter += "Filter: host_name = %s\nFilter: service_description = %s\n" % (
                tl_host, tl_service)
        only_sites = [ tl_site ]
    elif what == "service":
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

    query += "Columns: %s\n" % " ".join(columns)
    query += filterheaders

    html.live.set_prepend_site(True)
    html.live.set_only_sites(only_sites)
    data = html.live.query(query)
    html.live.set_only_sites(None)
    html.live.set_prepend_site(False)
    columns = ["site"] + columns
    spans = [ dict(zip(columns, span)) for span in data ]

    # Sort by site/host and service, while keeping native order
    av_rawdata = {}
    for span in spans:
        site_host = span["site"], span["host_name"]
        service = span["service_description"]
        av_rawdata.setdefault(site_host, {})
        av_rawdata[site_host].setdefault(service, []).append(span)

    return av_rawdata



# Compute an availability table. what is one of "bi", "host", "service".
def compute_availability(what, av_rawdata, avoptions):

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
    grouping = avoptions["grouping"]
    timeline_rows = [] # Need this as a global variable if just one service is affected
    total_duration = 0
    considered_duration = 0

    # Note: in case of timeline, we have data from exacly one host/service
    for site_host, site_host_entry in av_rawdata.iteritems():
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

            availability_entry = {
                "site"                : site_host[0],
                "host"                : site_host[1],
                "service"             : service,
                "display_name"        : display_name,
                "states"              : states,
                "considered_duration" : considered_duration,
                "total_duration"      : total_duration,
                "statistics"          : statistics,
                "groups"              : group_ids,
                "timeline"            : timeline_rows,
            }


            availability.append(availability_entry)

    return availability


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


#   .--BI------------------------------------------------------------------.
#   |                              ____ ___                                |
#   |                             | __ )_ _|                               |
#   |                             |  _ \| |                                |
#   |                             | |_) | |                                |
#   |                             |____/___|                               |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Availability computation in BI aggregates. Here we generate the     |
#   |  same availability raw data. We fill the field "host" with the BI    |
#   |  group and the field "service" with the BI aggregate's name.         |
#   '----------------------------------------------------------------------'

def compute_bi_availability(avoptions, aggr_rows):
    av_rawdata = {}
    for aggr_row in aggr_rows:
        by_host = av_rawdata.setdefault((None, aggr_row["aggr_group"]), {})
        entry = by_host.setdefault(aggr_row["aggr_name"], [])
        these_rows, tree_state = get_bi_timeline(aggr_row["aggr_tree"], aggr_row["aggr_group"], avoptions, False)
        entry += these_rows

    # TODO: Das hier klappt sicher nicht!
    return views.do_render_availability("bi", av_rawdata, avoptions, timeline=False, timewarpcode=None, fetch=True)


def get_bi_timeline(tree, aggr_group, avoptions, timewarp):
    range, range_title = avoptions["range"]
    # Get state history of all hosts and services contained in the tree.
    # In order to simplify the query, we always fetch the information for
    # all hosts of the aggregates.
    only_sites = set([])
    hosts = []
    for site, host in tree["reqhosts"]:
        only_sites.add(site)
        hosts.append(host)

    columns = [ "host_name", "service_description", "from", "log_output", "state", "in_downtime" ]
    html.live.set_only_sites(list(only_sites))
    html.live.set_prepend_site(True)
    html.live.set_limit() # removes limit
    query = "GET statehist\n" + \
            "Columns: " + " ".join(columns) + "\n" +\
            "Filter: time >= %d\nFilter: time < %d\n" % range

    # Create a specific filter. We really only want the services and hosts
    # of the aggregation in question. That prevents status changes
    # irrelevant services from introducing new phases.
    by_host = {}
    for site, host, service in bi.find_all_leaves(tree):
        by_host.setdefault(host, set([])).add(service)

    for host, services in by_host.items():
        query += "Filter: host_name = %s\n" % host
        query += "Filter: service_description = \n"
        for service in services:
            query += "Filter: service_description = %s\n" % service
        query += "Or: %d\nAnd: 2\n" % (len(services) + 1)
    if len(hosts) != 1:
        query += "Or: %d\n" % len(hosts)

    data = html.live.query(query)
    if not data:
        return [], None
        # raise MKGeneralException(_("No historical data available for this aggregation. Query was: <pre>%s</pre>") % query)

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
            service     = row["service_description"]
            key         = row["site"], row["host_name"], service
            states[key] = row["state"], row["log_output"], row["in_downtime"]


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
        timeline.append({
            "state"                  : tree_state[0]['state'],
            "log_output"             : tree_state[0]['output'],
            "from"                   : from_time,
            "until"                  : until_time,
            "site"                   : "",
            "host_name"              : aggr_group,
            "service_description"    : tree['title'],
            "in_notification_period" : 1,
            "in_service_period"      : 1,
            "in_downtime"            : tree_state[0]['in_downtime'],
            "in_host_downtime"       : 0,
            "host_down"              : 0,
            "is_flapping"            : 0,
            "duration"               : until_time - from_time,
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
                service,         # service description
                state_output[0], # state
                1,               # has_been_checked
                state_output[1], # output
                state_output[0], # hard state (we use the soft state here)
                1,               # attempt
                1,               # max_attempts (not relevant)
                state_output[2], # in_downtime
                False,           # acknowledged
                ))
        else:
            hosts[site_host] = state_output

    status_info = {}
    for site_host, state_output in hosts.items():
        status_info[site_host] = [
            state_output[0],
            state_output[0], # host hard state
            state_output[1],
            state_output[2], # in_downtime
            False, # acknowledged
            services_by_host.get(site_host,[])
        ]


    # Finally we can execute the tree
    bi.load_assumptions()
    tree_state = bi.execute_tree(tree, status_info)
    return tree_state

