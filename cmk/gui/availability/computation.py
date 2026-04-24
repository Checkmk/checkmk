#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from livestatus import (
    lqencode,
    OnlySites,
    Query,
    QuerySpecification,
)

from cmk.ccc.cpu_tracking import CPUTracker
from cmk.gui.data_source import query_livestatus
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.num_split import key_num_split
from cmk.gui.type_defs import (
    FilterHeader,
    HTTPVariables,
    ViewProcessTracking,
    VisualContext,
)
from cmk.gui.utils.urls import urlencode_vars
from cmk.gui.view_utils import cmp_service_name_equiv
from cmk.gui.watolib.groups_io import all_groups

from .annotations import (
    load_annotations,
)
from .annotations import (
    reclassify_config_by_annotation as reclassify_config_by_annotation,
)
from .annotations import (
    reclassify_history_by_annotation as reclassify_history_by_annotation,
)
from .annotations import (
    reclassify_history_by_annotations as reclassify_history_by_annotations,
)
from .annotations import (
    reclassify_times_by_annotation as reclassify_times_by_annotation,
)
from .annotations import (
    ReclassifyConfig as ReclassifyConfig,
)
from .options import get_outage_statistic_options
from .type_defs import (
    AVAnnotationKey,
    AVData,
    AVEntry,
    AVGroupIds,
    AVGroupKey,
    AVGroups,
    AVHostOrServiceObjectSpec,
    AVLevels,
    AVObjectSpec,
    AVObjectType,
    AVOptions,
    AVRawData,
    AVRawServices,
    AVSpan,
    AVTimelineRows,
    AVTimelineStates,
    AVTimelineStatistics,
    AVTimeRange,
    HostOrServiceGroupName,
)


# Get raw availability data for host/service via livestatus. The result is a
# list of spans. Each span is a dictionary that describes one span of time where
# a specific host or service has one specific state.
# For BI availability use get_bi_availability_rawdata from the bi module,
# or the top-level get_availability_rawdata from cmk.gui.availability which
# dispatches automatically.
def get_host_service_availability_rawdata(
    what: AVObjectType,
    context: VisualContext,
    filterheaders: FilterHeader,
    only_sites: OnlySites,
    av_object: AVObjectSpec,
    include_output: bool,
    include_long_output: bool,
    avoptions: AVOptions,
    view_process_tracking: ViewProcessTracking | None = None,
) -> tuple[AVRawData, bool]:
    # 'view_process_tracking=None': this function is also called from the grafana module
    # which has not the task to track the processed rows/cpu time but the views module does
    # track these steps.
    time_range: AVTimeRange = avoptions["range"][0]

    av_filter = "Filter: time >= %d\nFilter: time < %d\n" % time_range
    if av_object:
        tl_site, tl_host, tl_service = av_object
        av_filter += f"Filter: host_name = {lqencode(str(tl_host))}\nFilter: service_description = {lqencode(tl_service)}\n"
        assert tl_site is not None
        only_sites = [tl_site]
    elif what == "service":
        av_filter += "Filter: service_description !=\n"
    else:
        av_filter += "Filter: service_description =\n"

    # Add Columns needed for object identification
    columns = ["host_name", "service_description"]

    # Columns for availability
    columns += [
        "duration",
        "from",
        "until",
        "state",
        "host_down",
        "in_downtime",
        "in_host_downtime",
        "in_notification_period",
        "in_service_period",
        "is_flapping",
    ]
    if include_output:
        columns.append("log_output")
    if include_long_output:
        columns.append("long_log_output")
        columns.append("service_check_command")
        columns.append("service_custom_variables")
    if "use_display_name" in avoptions["labelling"]:
        columns.append("service_display_name")
    if "show_alias" in avoptions["labelling"]:
        columns.append("host_alias")

    # If we group by host/service group then make sure that that information is available
    if avoptions["grouping"] not in [None, "host"]:
        columns.append(avoptions["grouping"])

    headers = av_filter
    headers += "Timelimit: %d\n" % avoptions["timelimit"]
    headers += filterheaders
    logrow_limit = avoptions["logrow_limit"]

    with CPUTracker(logger.debug) as fetch_rows_tracker:
        data = query_livestatus(
            Query(
                QuerySpecification(
                    table="statehist",
                    columns=columns,
                    headers=headers,
                )
            ),
            only_sites=only_sites,
            limit=logrow_limit or None,
            auth_domain="read",
        )

    columns = ["site"] + columns
    spans: list[AVSpan] = [dict(zip(columns, span)) for span in data]
    amount_filtered_rows = len(spans)

    # When a group filter is set, only care about these groups in the group fields
    with CPUTracker(logger.debug) as filter_rows_tracker:
        if avoptions["grouping"] not in [None, "host"]:
            filter_groups_of_entries(context, avoptions, spans)

    # Now we find out if the log row limit was exceeded or
    # if the log's length is the limit by accident.
    # If this limit was exceeded then we cut off the last element
    # because it might be incomplete.
    exceeded_log_row_limit: bool = False
    if logrow_limit and len(data) > logrow_limit:
        exceeded_log_row_limit = True
        spans = spans[:-1]

    if view_process_tracking:
        view_process_tracking.amount_unfiltered_rows = len(data)
        view_process_tracking.amount_filtered_rows = amount_filtered_rows
        view_process_tracking.amount_rows_after_limit = len(spans)
        view_process_tracking.duration_fetch_rows = fetch_rows_tracker.duration
        view_process_tracking.duration_filter_rows = filter_rows_tracker.duration

    return spans_by_object(spans), exceeded_log_row_limit


def filter_groups_of_entries(
    context: VisualContext, avoptions: AVOptions, spans: list[AVSpan]
) -> None:
    group_by = avoptions["grouping"]

    only_groups = set()
    # TODO: This is a dirty hack. The logic of the filters needs to be moved to the filters.
    # They need to be able to filter the list of all groups.
    # TODO: Negated filters are not handled here. :(
    if group_by == "service_groups":
        servicegroups = context.get("servicegroups", {})
        optservicegroup = context.get("optservicegroup", {})
        if not any(iter(servicegroups.values())) and not any(iter(optservicegroup.values())):
            return

        # Extract from context:
        # 'servicegroups': {'servicegroups': 'cpu|disk', 'neg_servicegroups': 'off'},
        # 'optservicegroup': {'optservice_group': '', 'neg_optservice_group': 'off'},
        sg_filter = context.get("servicegroups", {})
        assert isinstance(sg_filter, dict)
        negated = sg_filter.get("neg_servicegroups") == "on"
        if negated:
            return

        only_groups.update([e for e in sg_filter.get("servicegroups", "").split("|") if e])

        opt_sg_filter = context.get("optservicegroup", {})
        assert isinstance(opt_sg_filter, dict)
        negated = opt_sg_filter.get("neg_optservice_group") == "on"
        if negated:
            return

        group_name = opt_sg_filter.get("optservice_group")
        if group_name and not negated:
            only_groups.add(group_name)

    elif group_by == "host_groups":
        if "hostgroups" not in context and "opthostgroup" not in context:
            return

        hg_filter = context.get("hostgroups", {})
        assert isinstance(hg_filter, dict)
        negated = hg_filter.get("neg_hostgroups") == "on"
        if negated:
            return

        only_groups.update([e for e in hg_filter.get("hostgroups", "").split("|") if e])

        opt_hg_filter = context.get("opthostgroup", {})
        assert isinstance(opt_hg_filter, dict)
        negated = opt_hg_filter.get("neg_opthost_group") == "on"
        if negated:
            return

        group_name = opt_hg_filter.get("opthost_group")
        if group_name and not negated:
            only_groups.add(group_name)

    else:
        raise NotImplementedError()

    for span in spans:
        filtered_groups = list(set(span[group_by]).intersection(only_groups))
        span[group_by] = filtered_groups


# Sort the raw spans into a tree of dicts, so that we
# have easy access to the timeline of each object
def spans_by_object(spans: list[AVSpan]) -> AVRawData:
    # Sort by site/host and service, while keeping native order
    av_rawdata: AVRawData = {}
    for span in spans:
        site_host = span["site"], span["host_name"]
        service = span["service_description"]
        av_rawdata.setdefault(site_host, {})
        av_rawdata[site_host].setdefault(service, []).append(span)

    return av_rawdata


# Compute an availability table. what is one of "bi", "host", "service".
def compute_availability(
    what: AVObjectType,
    av_rawdata: AVRawData,
    avoptions: AVOptions,
) -> AVData:
    reclassified_rawdata = reclassify_by_annotations(what, av_rawdata)

    # Now compute availability table. We have the following possible states:
    # 1. "unmonitored"
    # 2. monitored -->
    #    2.1 "outof_service_period"
    #    2.2 in service period -->
    #        2.2.1 "outof_notification_period"
    #        2.2.2 in notification period -->
    #             2.2.2.1 "in_downtime" (also in_host_downtime)
    #             2.2.2.2 not in downtime -->
    #                   2.2.2.2.1 "host_down"
    #                   2.2.2.2.2 host not down -->
    #                        2.2.2.2.2.1 "ok"
    #                        2.2.2.2.2.2 "warn"
    #                        2.2.2.2.2.3 "crit"
    #                        2.2.2.2.2.4 "unknown"
    availability_table: AVData = []
    os_aggrs, os_states = get_outage_statistic_options(avoptions)
    need_statistics = os_aggrs and os_states
    grouping = avoptions["grouping"]

    # Note: in case of timeline, we have data from exacly one host/service
    for site_host, site_host_entry in reclassified_rawdata.items():
        for service, service_entry in site_host_entry.items():
            if grouping == "host":
                group_ids: AVGroupIds = [site_host]
            elif grouping in ["host_groups", "service_groups"]:
                group_ids = set()
            else:
                group_ids = None

            # First compute timeline
            timeline_rows: AVTimelineRows = []
            total_duration = 0
            considered_duration = 0
            display_name: str = service
            host_alias: str = site_host[1]
            for span in service_entry:
                # Information about host/service groups are in the actual entries
                if grouping in ["host_groups", "service_groups"] and what != "bi":
                    assert isinstance(group_ids, set)
                    group_ids.update(span[grouping])  # List of host/service groups

                display_name = span.get("service_display_name", service)
                state = span["state"]
                host_alias = span.get("host_alias", site_host[1])
                consider = True
                s: str

                if avoptions["service_period"] != "ignore" and (
                    (span["in_service_period"] and avoptions["service_period"] != "honor")
                    or (not span["in_service_period"] and avoptions["service_period"] == "honor")
                ):
                    s = "outof_service_period"
                    consider = False
                elif state == -1:
                    s = "unmonitored"
                    if not avoptions["consider"]["unmonitored"]:
                        consider = False
                elif state is None:
                    # state is None means that this element was not known at this given time
                    # So there is no reason for creating a fake pending state
                    consider = False
                elif (
                    span["in_notification_period"] == 0
                    and avoptions["notification_period"] == "exclude"
                ):
                    consider = False

                elif (
                    span["in_notification_period"] == 0
                    and avoptions["notification_period"] == "honor"
                ):
                    s = "outof_notification_period"

                elif (
                    (span["in_downtime"] or span["in_host_downtime"])
                    and not (avoptions["downtimes"]["exclude_ok"] and state == 0)
                    and not avoptions["downtimes"]["include"] == "ignore"
                ):
                    if avoptions["downtimes"]["include"] == "exclude":
                        consider = False
                    else:
                        s = "in_downtime"
                elif what != "host" and span["host_down"] and avoptions["consider"]["host_down"]:
                    # Reclassification due to state grouping
                    s = avoptions["state_grouping"].get("host_down", "host_down")

                elif span["is_flapping"] and avoptions["consider"]["flapping"]:
                    s = "flapping"
                else:
                    if what in ["service", "bi"]:
                        s = {0: "ok", 1: "warn", 2: "crit", 3: "unknown"}.get(state, "unmonitored")
                    else:
                        s = {0: "up", 1: "down", 2: "unreach"}.get(state, "unmonitored")

                    # Reclassification due to state grouping
                    if s in avoptions["state_grouping"]:
                        s = avoptions["state_grouping"][s]

                    elif s in avoptions["host_state_grouping"]:
                        s = avoptions["host_state_grouping"][s]

                total_duration += span["duration"]
                if consider:
                    timeline_rows.append((span, s))
                    considered_duration += span["duration"]

            # Now merge consecutive rows with identical state
            if not avoptions["dont_merge"]:
                merge_timeline(timeline_rows)

            # Melt down short intervals
            if avoptions["short_intervals"]:
                melt_short_intervals(
                    timeline_rows, avoptions["short_intervals"], avoptions["dont_merge"]
                )

            # Condense into availability
            states: AVTimelineStates = {}
            statistics: AVTimelineStatistics = {}
            for span, s in timeline_rows:
                states.setdefault(s, 0)
                duration = span["duration"]
                states[s] += duration
                if need_statistics:
                    entry = statistics.get(s)
                    if entry:
                        statistics[s] = (
                            entry[0] + 1,
                            min(entry[1], duration),
                            max(entry[2], duration),
                        )
                    else:
                        statistics[s] = (1, duration, duration)  # count, min, max

            availability_entry: AVEntry = {
                "site": site_host[0],
                "host": site_host[1],
                "alias": host_alias,
                "service": service,
                "display_name": display_name,
                "states": states,
                "considered_duration": considered_duration,
                "total_duration": total_duration,
                "statistics": statistics,
                "groups": group_ids,
                "timeline": timeline_rows,
            }

            availability_table.append(availability_entry)

    # Apply filters
    filtered_table: AVData = []
    for row in sorted(availability_table, key=key_av_entry):
        if pass_availability_filter(row, avoptions):
            filtered_table.append(row)
    return filtered_table


# Note: Reclassifications of host/service periods do currently *not* have
# any impact on BI aggregations.
def reclassify_by_annotations(what: AVObjectType, av_rawdata: AVRawData) -> AVRawData:
    annotations = load_annotations()
    if not annotations:
        return av_rawdata

    reclassified_rawdata: AVRawData = {}
    for (site, host_name), history_entries in av_rawdata.items():
        new_entries: AVRawServices = {}
        reclassified_rawdata[(site, host_name)] = new_entries
        for service_description, history in history_entries.items():
            cycles: list[AVAnnotationKey] = []
            cycles.append((site, host_name, service_description or None))
            if what == "service":
                cycles.insert(0, (site, host_name, None))

            for anno_key in cycles:
                if anno_key in annotations:
                    new_entries[service_description] = reclassify_history_by_annotations(
                        history, annotations[anno_key]
                    )
                    history = new_entries[service_description]
                else:
                    new_entries[service_description] = history

    return reclassified_rawdata


def pass_availability_filter(row: AVEntry, avoptions: AVOptions) -> bool:
    if row["considered_duration"] == 0:
        return True

    for key, level in avoptions["av_filter_outages"].items():
        if level == 0.0:
            continue
        if key == "warn":
            ref_value = row["states"].get("warn", 0)
        elif key == "crit":
            ref_value = row["states"].get("crit", row["states"].get("down", 0))
        elif key == "non-ok":
            ref_value = 0
            for state_key, value in row["states"].items():
                if state_key not in ["ok", "up", "unmonitored"]:
                    ref_value += value
        else:
            continue  # undefined key. Should never happen
        percentage = 100.0 * ref_value / row["considered_duration"]
        if percentage < level:
            return False

    return True


# Compute a list of availability tables - one for each group.
# Each entry is a pair of group_name and availability_table.
# It is sorted by the group names
def compute_availability_groups(
    what: AVObjectType,
    av_data: AVData,
    avoptions: AVOptions,
) -> AVGroups:
    grouping = avoptions["grouping"]
    if not grouping:
        return [(None, av_data)]

    availability_tables: AVGroups = []

    # Grouping is one of host/hostgroup/servicegroup

    # 1. Get complete list of all groups
    all_group_ids = get_av_groups(av_data, avoptions)

    # 2. Compute names for the groups and sort according to these names
    group_titles: dict[str, str] = {}
    if grouping != "host":
        group_titles = dict(all_groups(grouping[:-7]))

    titled_groups: list[tuple[str, AVGroupKey]] = []
    for group_id in all_group_ids:
        if grouping == "host":
            assert isinstance(group_id, tuple)
            titled_groups.append((group_id[1], group_id))  # omit the site name
        else:
            if group_id is None:
                title = _("Not contained in any group")
            else:
                assert isinstance(group_id, HostOrServiceGroupName)
                title = group_titles.get(group_id, group_id)
            titled_groups.append((title, group_id))  # ACHTUNG

    # 3. Loop over all groups and render them
    for title, group_id in sorted(titled_groups, key=lambda x: x[1] or ""):
        group_table = []
        for entry in av_data:
            row_group_ids: AVGroupIds = entry["groups"]
            if group_id is None and row_group_ids:
                continue  # This is not an ungrouped object
            if group_id and row_group_ids and group_id not in row_group_ids:
                continue  # Not this group
            if group_id and not row_group_ids:
                continue  # This is an ungrouped object
            group_table.append(entry)
        availability_tables.append((title, group_table))

    return availability_tables


def object_title(what: AVObjectType, av_entry: AVEntry) -> str:
    if what == "host":
        return str(av_entry["host"])
    # service and BI
    return str(av_entry["host"]) + " / " + str(av_entry["service"])


def merge_timeline(entries: AVTimelineRows) -> None:
    """Merge consecutive rows with same state"""
    n = 1
    while n < len(entries):
        if (
            entries[n][1] == entries[n - 1][1]
            and entries[n][0]["from"] == entries[n - 1][0]["until"]
        ):
            entries[n - 1][0]["duration"] += entries[n][0]["duration"]
            entries[n - 1][0]["until"] = entries[n][0]["until"]
            del entries[n]
        else:
            n += 1


def melt_short_intervals(entries: AVTimelineRows, duration: int, dont_merge: bool) -> None:
    n = 1
    need_merge = False
    while n < len(entries) - 1:
        if (
            entries[n][0]["duration"] <= duration
            and (
                entries[n - 1][0]["until"] == entries[n][0]["from"]
                or entries[n][0]["until"] == entries[n + 1][0]["from"]
            )
            and entries[n - 1][1] == entries[n + 1][1]
        ):
            entries[n] = (entries[n][0], entries[n - 1][1])
            need_merge = True
        n += 1

    # Due to melting, we need to merge again
    if need_merge and not dont_merge:
        merge_timeline(entries)
        melt_short_intervals(entries, duration, dont_merge)


# Helper function, needed in row and in summary line. Determines whether
# a certain cell should be visiable. For example when WARN is mapped
# to CRIT because of state grouping, then the WARN column should not be
# displayed.
def cell_active(sid: str, avoptions: AVOptions) -> bool:
    # Some columns might be unneeded due to state treatment options
    sg = avoptions["state_grouping"]
    hsg = avoptions["host_state_grouping"]

    if sid not in ["up", "ok"] and avoptions["av_mode"]:
        return False
    if sid == "outof_notification_period" and avoptions["notification_period"] != "honor":
        return False
    if sid == "outof_service_period":  # Never show this as a column
        return False
    if sid == "in_downtime" and avoptions["downtimes"]["include"] != "honor":
        return False
    if sid == "unmonitored" and not avoptions["consider"]["unmonitored"]:
        return False
    if sid == "flapping" and not avoptions["consider"]["flapping"]:
        return False
    if sid == "host_down" and not avoptions["consider"]["host_down"]:
        return False
    if sid in sg and sid not in sg.values():
        return False
    if sid in hsg and sid not in hsg.values():
        return False
    return True


# Check if the availability of some object is below the levels
# that are configured in the avoptions.
def check_av_levels(ok_seconds: float, av_levels: AVLevels, considered_duration: float) -> int:
    if considered_duration == 0:
        return 0

    perc = 100 * float(ok_seconds) / float(considered_duration)
    warn, crit = av_levels
    if perc < crit:
        return 2
    if perc < warn:
        return 1
    return 0


def get_av_groups(availability_table: AVData, avoptions: AVOptions) -> set[AVGroupKey]:
    all_group_ids: set[AVGroupKey] = set()
    for entry in availability_table:
        if entry["groups"] is None or len(entry["groups"]) == 0:
            all_group_ids.add(None)  # None denotes ungrouped objects
        else:
            all_group_ids.update(entry["groups"])
    return all_group_ids


# Sort according to host and service. First after site, then
# host (natural sort), then service
def key_av_entry(
    a: AVEntry,
) -> tuple[tuple[int | str, ...], int, tuple[int | str, ...], tuple[int | str, ...]]:
    return (
        key_num_split(a["service"]),
        cmp_service_name_equiv(a["service"]),
        key_num_split(a["host"]),
        key_num_split(a["site"]),
    )


def history_url_of(av_object: AVHostOrServiceObjectSpec, time_range: AVTimeRange) -> str:
    site, host, service = av_object
    from_time, until_time = time_range

    history_url_vars: HTTPVariables = [
        ("site", site),
        ("host", host),
        ("logtime_from_range", "unix"),  # absolute timestamp
        ("logtime_until_range", "unix"),  # absolute timestamp
        ("logtime_from", str(int(from_time))),
        ("logtime_until", str(int(until_time))),
    ]
    if service:
        history_url_vars += [
            ("service", service),
            ("view_name", "svcevents"),
        ]
    else:
        history_url_vars += [
            ("view_name", "hostevents"),
        ]

    return "view.py?" + urlencode_vars(history_url_vars)
