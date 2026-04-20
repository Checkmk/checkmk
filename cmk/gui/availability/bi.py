#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from collections.abc import Generator, Sequence
from typing import Any

from livestatus import (
    LivestatusRow,
    lq_logic,
    MKLivestatusPayloadTooLargeError,
    OnlySites,
    Query,
    QuerySpecification,
)

from cmk.bi.lib import (
    BIHostSpec,
    BIHostStatusInfoRow,
    BIServiceWithFullState,
    BIState,
    BIStatusInfo,
    NodeComputeResult,
    NodeResultBundle,
)
from cmk.bi.trees import BICompiledAggregation, BICompiledRule, CompiledAggrTree
from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import omd_site
from cmk.gui.bi.bi_manager import BIManager
from cmk.gui.data_source import query_livestatus
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.type_defs import (
    FilterHeader,
    Row,
    Rows,
)
from cmk.utils.servicename import ServiceName

from .annotations import load_annotations, reclassify_history_by_annotations
from .computation import spans_by_object
from .type_defs import (
    AVBIPhaseData,
    AVBIPhases,
    AVBITimelineState,
    AVBITimelineStates,
    AVObjectSpec,
    AVOptions,
    AVRawData,
    AVSpan,
    AVTimeRange,
    AVTimeStamp,
)

BIAggregationGroupTitle = str
BIAggregationTitle = str
BITreeState = Any
BITimelineEntry = Any


DEFAULT_MAX_TIME_RANGE = 31 * 24 * 60 * 60  # One month


# Not a real class, more a struct
class TimelineContainer:
    def __init__(self, aggr_row: Row) -> None:
        self._aggr_row = aggr_row

        # PUBLIC accessible data
        self.aggr_compiled_aggregation: BICompiledAggregation = self._aggr_row[
            "aggr_compiled_aggregation"
        ]
        self.aggr_compiled_branch: BICompiledRule = self._aggr_row["aggr_compiled_branch"]
        self.aggr_tree: CompiledAggrTree = self._aggr_row["aggr_tree"]
        self.aggr_group: BIAggregationGroupTitle = self._aggr_row["aggr_group"]

        # Data fetched from livestatus query
        self.host_service_info: set[tuple[HostName, ServiceName]] = set()

        # Computed data
        self.timeline: list[BITimelineEntry] = []
        self.states: AVBITimelineStates = {}

        # Can be optional after computation
        self.node_compute_result: NodeComputeResult | None = None
        self.timewarp_state: BITreeState | None = None
        # Can not be optional after computation
        self.tree_time: AVTimeStamp | None = None


def get_bi_availability(
    avoptions: AVOptions, aggr_rows: Rows, timewarp: AVTimeStamp | None
) -> tuple[list[TimelineContainer], AVRawData, bool]:
    logrow_limit = avoptions["logrow_limit"]
    if logrow_limit == 0:
        livestatus_limit = None
    else:
        livestatus_limit = (len(aggr_rows) * logrow_limit) + 1

    timeline_containers, fetched_rows = get_timeline_containers(
        aggr_rows, avoptions, timewarp, livestatus_limit
    )

    has_reached_logrow_limit = bool(livestatus_limit and fetched_rows > livestatus_limit)

    spans: list[AVSpan] = []
    for timeline_container in timeline_containers:
        spans.extend(timeline_container.timeline)

    av_rawdata = spans_by_object(spans)

    return timeline_containers, av_rawdata, has_reached_logrow_limit


def get_bi_availability_rawdata(
    filterheaders: FilterHeader,
    only_sites: OnlySites,
    av_object: AVObjectSpec,
    include_output: bool,
    avoptions: AVOptions,
) -> tuple[AVRawData, bool]:
    raise Exception("Not implemented yet. Sorry.")


def get_timeline_containers(
    aggr_rows: Rows,
    avoptions: AVOptions,
    timewarp: AVTimeStamp | None,
    livestatus_limit: int | None,
) -> tuple[list[TimelineContainer], int]:
    time_range: AVTimeRange = avoptions["range"][0]
    phases_list, timeline_containers, fetched_rows = get_bi_leaf_history(
        aggr_rows, time_range, livestatus_limit
    )
    return (
        compute_bi_timelines(timeline_containers, time_range, timewarp, phases_list),
        fetched_rows,
    )


def split_time_range(
    start: AVTimeStamp, end: AVTimeStamp, interval: AVTimeStamp
) -> Generator[AVTimeRange]:
    """
    Split a time range into smaller ranges of a given interval.

    Examples:
    >>> _start, _end = 42, 1337
    >>> list(split_time_range(_start, _end, -((_end - _start) // -2)))
    [(42, 690), (690, 1337)]
    >>> list(split_time_range(_start, _end, (_end - _start) // 2))
    [(42, 689), (689, 1336), (1336, 1337)]
    >>> list(split_time_range(_start, _end, 250))
    [(42, 292), (292, 542), (542, 792), (792, 1042), (1042, 1292), (1292, 1337)]
    """
    if interval <= 0:
        raise ValueError("Interval must be positive")
    while start < end:
        yield start, min(start + interval, end)
        start += interval


def get_bi_leaf_history(
    aggr_rows: Rows,
    time_range: AVTimeRange,
    livestatus_limit: int | None,
    max_time_range: int = DEFAULT_MAX_TIME_RANGE,
) -> tuple[AVBIPhases, list[TimelineContainer], int]:
    """Get state history of all hosts and services contained in the tree.
    In order to simplify the query, we always fetch the information for all hosts of the aggregates.
    """
    only_sites = set()
    hosts = set()
    for row in aggr_rows:
        for site, host in row["aggr_compiled_branch"].get_required_hosts():
            only_sites.add(site)
            hosts.add(host)

    columns = [
        "host_name",
        "service_description",
        "from",
        "until",
        "log_output",
        "state",
        "in_downtime",
        "in_service_period",
    ]

    # Create a specific filter. We really only want the services and hosts
    # of the aggregation in question. That prevents status changes
    # irrelevant services from introducing new phases.
    by_host: dict[HostName, set[ServiceName]] = {}
    timeline_containers: list[TimelineContainer] = []
    for row in aggr_rows:
        timeline_container = TimelineContainer(row)

        for _site, host, service in timeline_container.aggr_compiled_branch.required_elements():
            this_service = service or ""
            by_host.setdefault(host, {""}).add(this_service)
            timeline_container.host_service_info.add((host, this_service))
            timeline_container.host_service_info.add((host, ""))

        timeline_containers.append(timeline_container)

    headers = ""
    for host, services in by_host.items():
        headers += "Filter: host_name = %s\n" % host
        headers += lq_logic("Filter: service_description = ", list(services), "Or")
        headers += "And: 2\n"
    if len(hosts) != 1:
        headers += "Or: %d\n" % len(hosts)

    data: list[LivestatusRow] = []

    split_time_ranges = split_time_range(time_range[0], time_range[1], max_time_range)
    for current_time_range in split_time_ranges:
        get_bi_split_history_data(
            data, current_time_range, columns, only_sites, headers, livestatus_limit
        )

    if not data:
        return [], [], 0

    columns = ["site"] + columns
    rows = [dict(zip(columns, row)) for row in data]

    # Reclassify base data due to annotations
    rows = reclassify_bi_rows(rows)
    merged_rows_by_id = get_bi_merged_rows_by_id(rows)

    # Now comes the tricky part: recompute the state of the aggregate
    # for each step in the state history and construct a timeline from
    # it. As a first step we need the start state for each of the
    # hosts/services. They will always be the first consecute rows
    # in the statehist table

    # First partition the rows into sequences with equal start time
    phases: dict[int, dict[tuple[HostName, ServiceName], Row]] = {}
    for id_, merged_rows in merged_rows_by_id.items():
        for row in merged_rows:
            phases.setdefault(row["from"], {})[id_] = row

    # Convert phases to sorted list
    sorted_times = sorted(phases.keys())
    phases_list: AVBIPhases = []

    for from_time in sorted_times:
        phases_list.append((from_time, phases[from_time]))
    return phases_list, timeline_containers, sum(len(rows) for rows in merged_rows_by_id.values())


def get_bi_merged_rows_by_id(rows: list[Row]) -> dict[tuple[HostName, ServiceName], list[Row]]:
    by_id: dict[tuple[HostName, ServiceName], list[Row]] = {}
    for row in rows:
        id_ = (row["host_name"], row["service_description"])
        by_id.setdefault(id_, [])
        by_id[id_].append(row)

    for id_, service_rows in by_id.items():
        by_id[id_] = sorted(service_rows, key=lambda x: x["from"])

    merged_rows_by_id: dict[tuple[HostName, ServiceName], list[Row]] = {id_: [] for id_ in by_id}
    for id_, service_rows in by_id.items():
        for service_row in service_rows:
            if not merged_rows_by_id[id_]:
                merged_rows_by_id[id_].append(service_row)
            elif (
                merged_rows_by_id[id_][-1]["state"] != service_row["state"]
                or merged_rows_by_id[id_][-1]["in_downtime"] != service_row["in_downtime"]
                or merged_rows_by_id[id_][-1]["in_service_period"]
                != service_row["in_service_period"]
                or merged_rows_by_id[id_][-1]["log_output"] != service_row["log_output"]
            ):
                merged_rows_by_id[id_].append(service_row)
            else:
                merged_rows_by_id[id_][-1]["until"] = service_row["until"]
    return merged_rows_by_id


def get_bi_split_history_data(
    data: list[LivestatusRow],
    time_range: AVTimeRange,
    columns: Sequence[str],
    only_sites: set[Any],
    headers: str,
    livestatus_limit: int | None,
) -> None:
    try:
        # Try to fetch complete data
        data.extend(
            query_livestatus(
                Query(
                    QuerySpecification(
                        table="statehist",
                        columns=columns,
                        headers="Filter: time >= %d\nFilter: time < %d\n" % time_range + headers,
                    )
                ),
                only_sites=list(only_sites),
                limit=livestatus_limit,
                auth_domain="read",
            )
        )
    except MKLivestatusPayloadTooLargeError:
        # If the query fails, split the time range into two and try again
        split_time_ranges = split_time_range(
            time_range[0],
            time_range[1],
            # Ceiling division in order not to split into three parts (see docstring example)
            -((time_range[1] - time_range[0]) // -2),
        )
        for current_time_range in split_time_ranges:
            get_bi_split_history_data(
                data, current_time_range, columns, only_sites, headers, livestatus_limit
            )


def compute_bi_timelines(
    timeline_containers: list[TimelineContainer],
    time_range: AVTimeRange,
    timewarp: AVTimeStamp | None,
    phases_list: AVBIPhases,
) -> list[TimelineContainer]:
    if not timeline_containers:
        return timeline_containers

    def update_states(
        states: AVBITimelineStates,
        use_entries: set[tuple[HostName, ServiceName]],
        phase_entries: AVBIPhaseData,
    ) -> None:
        for element in use_entries:
            hostname, svc_desc = element
            values = phase_entries[element]
            key = values["site"], hostname, svc_desc
            states[key] = (
                values["state"],
                values["log_output"],
                values["in_downtime"],
                (values["in_service_period"] != 0),
            )

    bi_manager = BIManager()

    logger.warning(
        "Computing timelines for range %r. %d phases and %d timeline containers",
        tuple(map(lambda x: time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(x)), time_range)),
        len(phases_list),
        len(timeline_containers),
    )
    computed_aggregations = 0
    for from_time, phase_hst_svc in phases_list:
        phase_keys = set(phase_hst_svc.keys())

        for timeline_container in timeline_containers:
            changed_elements = timeline_container.host_service_info.intersection(phase_keys)
            if not changed_elements:
                continue

            update_states(timeline_container.states, changed_elements, phase_hst_svc)
            result_bundle = _compute_node_result_bundle(timeline_container, bi_manager)
            computed_aggregations += 1
            next_node_compute_result = result_bundle.actual_result

            if timeline_container.node_compute_result is not None:
                assert timeline_container.tree_time is not None
                timeline_container.timeline.append(
                    create_bi_timeline_entry(
                        timeline_container.aggr_tree,
                        timeline_container.aggr_group,
                        timeline_container.tree_time,
                        from_time,
                        timeline_container.node_compute_result,
                    )
                )

            timeline_container.node_compute_result = next_node_compute_result
            timeline_container.tree_time = from_time
            if timewarp == timeline_container.tree_time:
                timeline_container.timewarp_state = _get_timewarp_state(
                    result_bundle, timeline_container
                )

    # Create a final timeline entry to the end of the query interval
    for timeline_container in list(timeline_containers):
        if timeline_container.node_compute_result is None:
            # This can only happen if the livestatus row limit was reached
            # The data is incomplete or entirely missing
            timeline_containers.remove(timeline_container)
            continue

        assert timeline_container.tree_time is not None
        timeline_container.timeline.append(
            create_bi_timeline_entry(
                timeline_container.aggr_tree,
                timeline_container.aggr_group,
                timeline_container.tree_time,
                time_range[1],
                timeline_container.node_compute_result,
            )
        )

    logger.warning("Timeline generation finished. Computed %d aggregations", computed_aggregations)
    return timeline_containers


def _get_timewarp_state(
    node_compute_result_bundle: NodeResultBundle, timeline_container: TimelineContainer
) -> BITreeState:
    if node_compute_result_bundle.instance is None:
        # This timeline container was unable to find any host/services for the aggregation
        # Since this timewarp info is rendered through the legacy bi tree renderer,
        # which requires the legacy data format, we need to fake legacy data
        # state, assumed_state, node, _subtrees = aggr_treestate
        return (
            {
                "state": -1,
                "in_downtime": False,
                "in_service_period": True,
                "output": _("Not yet monitored"),
                "acknowledged": False,
            },
            None,
            {
                "title": _("Unknown aggregation"),
                "reqhosts": [],
            },
            [],  # no subtrees available
        )
    return timeline_container.aggr_compiled_aggregation.convert_result_to_legacy_format(
        node_compute_result_bundle
    )["aggr_treestate"]


def create_bi_timeline_entry(
    tree: CompiledAggrTree,
    aggr_group: BIAggregationGroupTitle,
    from_time: AVTimeStamp,
    until_time: AVTimeStamp,
    node_compute_result: NodeComputeResult,
) -> BITimelineEntry:
    return {
        "state": node_compute_result.state,
        "log_output": node_compute_result.output,
        "from": from_time,
        "until": until_time,
        "site": omd_site(),
        "host_name": aggr_group,
        "service_description": tree["title"],
        "in_notification_period": 1,
        "in_service_period": node_compute_result.in_service_period,
        "in_downtime": node_compute_result.in_downtime,
        "in_host_downtime": 0,
        "host_down": 0,
        "is_flapping": 0,
        "duration": until_time - from_time,
    }


def _compute_node_result_bundle(
    timeline_container: TimelineContainer, bi_manager: BIManager
) -> NodeResultBundle:
    # Convert our status format into that needed by BI
    status = timeline_container.states
    services_by_host: dict[BIHostSpec, dict[str, BIServiceWithFullState]] = {}
    hosts: dict[BIHostSpec, AVBITimelineState] = {}
    for site_host_service, state_output in status.items():
        site_host = BIHostSpec(site_id=site_host_service[0], host_name=site_host_service[1])
        service = site_host_service[2]
        state: int | None = state_output[0]

        # Create an entry for hosts that are not explicitly referenced in the timeline container.
        hosts.setdefault(site_host, (0, "", False, False))
        if service:
            if state == -1:
                # Ignore pending services
                continue
            services_by_host.setdefault(site_host, {})
            services_by_host[site_host][service] = BIServiceWithFullState(
                state=state,
                has_been_checked=True,
                plugin_output=state_output[1],
                hard_state=state,
                current_attempt=1,
                max_check_attempts=1,
                scheduled_downtime_depth=state_output[2],
                acknowledged=False,
                in_service_period=state_output[3],
            )
        else:
            hosts[site_host] = state_output

    bi_manager.status_fetcher.states = _compute_status_info(hosts, services_by_host)
    compiled_aggregation = timeline_container.aggr_compiled_aggregation
    branch = timeline_container.aggr_compiled_branch
    results = compiled_aggregation.compute_branches([branch], bi_manager.status_fetcher)

    if not results:
        # The aggregation did not find any hosts or services. Return "Not yet monitored"
        return NodeResultBundle(
            NodeComputeResult(
                state=BIState.PENDING,
                in_downtime=False,
                acknowledged=False,
                output=_("Not yet monitored"),
                in_service_period=True,
                state_messages={},
                custom_infos={},
            ),
            None,
            [],
            None,
        )

    return results[0]


def _compute_status_info(
    hosts: dict[BIHostSpec, AVBITimelineState],
    services_by_host: dict[BIHostSpec, dict[str, BIServiceWithFullState]],
) -> BIStatusInfo:
    status_info: BIStatusInfo = {}

    for site_host, state_output in hosts.items():
        state: int | None = state_output[0]

        if state == -1:
            state = None  # Means: consider this object as missing

        status_info[site_host] = BIHostStatusInfoRow(
            state=state,
            has_been_checked=True,
            hard_state=state,
            plugin_output=state_output[1],
            scheduled_downtime_depth=state_output[2],
            in_service_period=state_output[3],
            acknowledged=False,
            services_with_fullstate=services_by_host.get(site_host, {}),
            remaining_row_keys={},
        )
    return status_info


def reclassify_bi_rows(rows: Rows) -> Rows:
    annotations = load_annotations()
    if not annotations:
        return rows

    new_rows: Rows = []
    for row in rows:
        site = row["site"]
        host_name = row["host_name"]
        service_description = row["service_description"]
        anno_key = (site, host_name, service_description or None)
        if anno_key in annotations:
            new_rows += reclassify_history_by_annotations([row], annotations[anno_key])
        else:
            new_rows.append(row)
    return new_rows
