#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable
from typing import Any, Literal, NotRequired, TypedDict

from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.gui.type_defs import Row
from cmk.gui.utils.html import HTML
from cmk.gui.valuespec import TimerangeValue, ValueSpec
from cmk.gui.view_utils import CSSClass
from cmk.utils.servicename import ServiceName

AVMode = Literal["availability", "timeline"]
AVObjectType = Literal["host", "service", "bi"]
AVOptionValueSpecs = list[tuple[str, Literal["double", "single"], bool, ValueSpec[Any]]]
AVBIObjectSpec = tuple[None, None, str]
AVHostOrServiceObjectSpec = tuple[SiteId, HostName, ServiceName]
AVObjectSpec = None | AVBIObjectSpec | AVHostOrServiceObjectSpec
AVOutageStatisticsAggregations = list[Literal["min", "max", "avg", "cnt"]]
# The stored option offers only service states; for host availability the
# computation additionally appends the equivalent host states ("up", "down",
# "unreach"), so they are part of the value set as well.
AVOutageStatisticsState = Literal[
    "ok",
    "warn",
    "crit",
    "unknown",
    "flapping",
    "host_down",
    "in_downtime",
    "outof_notification_period",
    "up",
    "down",
    "unreach",
]
AVOutageStatisticsStates = list[AVOutageStatisticsState]
AVOutageStatistics = tuple[AVOutageStatisticsAggregations, AVOutageStatisticsStates]

# The functional TypedDict form is required here because "from" and "until" are Python keywords
# and cannot be used as identifiers in the class-body syntax.
AVSpan = TypedDict(
    "AVSpan",
    {
        "site": SiteId,
        "host_name": HostName,
        "service_description": ServiceName,
        "from": int,
        "until": int,
        "duration": int,
        "state": int | None,
        "host_down": int,
        "in_downtime": int,
        "in_host_downtime": int,
        "in_notification_period": int,
        "in_service_period": int,
        "is_flapping": int,
        "log_output": NotRequired[str],
        "long_log_output": NotRequired[str],
        "service_check_command": NotRequired[str],
        "service_custom_variables": NotRequired[dict[str, str]],
        "service_display_name": NotRequired[str],
        "host_alias": NotRequired[str],
        "host_state": NotRequired[int | None],
        "service_groups": NotRequired[list[str]],
        "host_groups": NotRequired[list[str]],
        # Fields added by SLA computation (_sla_computation)
        "original_state": NotRequired[int | None],
        "avail_state": NotRequired[str],
        # Fields added by SLA display (_sla_display)
        "css_period_class": NotRequired[str],
        "css_error_class": NotRequired[str],
        "duration_perc": NotRequired[str],
    },
)

SiteHost = tuple[SiteId, HostName]
AVRawServices = dict[ServiceName, list[AVSpan]]
AVRawData = dict[SiteHost, AVRawServices]
AVTimelineSpan = tuple[int | None, str, float, str]  # row_nr, title, width, css class
AVObjectCells = list[tuple[str, str]]
AVRowCells = list[tuple[HTML | str, CSSClass]]
HostOrServiceGroupName = str
AVGroupKey = SiteHost | HostOrServiceGroupName | None
AVGroupIds = list[SiteHost] | set[HostOrServiceGroupName] | None
AVTimeStamp = float
AVTimeRange = tuple[AVTimeStamp, AVTimeStamp]
AVTimeFormats = list[tuple[str, Callable[[AVTimeStamp, int], str]]]
AVRangeSpec = tuple[AVTimeRange, str]
AVTimeformatSpecLegacy = Literal[
    "percentage_0",
    "percentage_1",
    "percentage_2",
    "percentage_3",
    "seconds",
    "minutes",
    "hours",
    "hhmmss",
]
# The percentage and time slots are None when the selected mode ("perc" / "time")
# does not use them; only the slot relevant to the mode carries a format.
AVTimeformatSpec = (
    AVTimeformatSpecLegacy
    | tuple[
        Literal["both", "perc", "time"],
        Literal["percentage_0", "percentage_1", "percentage_2", "percentage_3"] | None,
        Literal["seconds", "minutes", "hours", "hhmmss"] | None,
    ]
)
AVTimelineLabelling = Literal[
    "omit_headers",
    "omit_host",
    "show_alias",
    "use_display_name",
    "omit_buttons",
    "omit_timeline_plugin_output",
    "timeline_long_output",
    "display_timeline_legend",
    "omit_av_levels",
]
AVIconSpec = tuple[str, str, str]

AVTimelineStateName = str
AVTimelineRow = tuple[AVSpan, AVTimelineStateName]
AVTimelineRows = list[AVTimelineRow]
AVTimelineStates = dict[AVTimelineStateName, int]
AVTimelineStatistics = dict[AVTimelineStateName, tuple[int, int, int]]
AVTimelineStyle = Literal["standalone", "inline"]


class AVEntry(TypedDict):
    site: SiteId
    host: HostName
    alias: str
    service: ServiceName
    display_name: str
    states: AVTimelineStates
    considered_duration: int
    total_duration: int
    statistics: AVTimelineStatistics
    groups: AVGroupIds
    timeline: AVTimelineRows


AVData = list[AVEntry]
AVGroups = list[tuple[str | None, AVData]]


# Example for annotations:
# {
#   ( "mysite", "foohost", "myservice" ) : # service might be None
#       [
#         {
#            "from"       : 1238288548,
#            "until"      : 1238292845,
#            "text"       : u"Das ist ein Text über mehrere Zeilen, oder was weiß ich",
#            "date"       : 12348854885, # Time of entry
#            "author"     : "mk",
#            "downtime"   : True, # Can also be False or None or missing. None is like missing
#         },
#         # ... further entries
#      ]
# }
AVAnnotationKey = tuple[SiteId, HostName, ServiceName | None]
AVAnnotationEntry = dict[str, Any]
AVAnnotations = dict[AVAnnotationKey, list[AVAnnotationEntry]]

# The functional TypedDict form is required here because "from" and "until" are
# Python keywords and cannot be used as identifiers in the class-body syntax.
AVLayoutTimelineRow = TypedDict(
    "AVLayoutTimelineRow",
    {
        "state": AVTimelineStateName,
        "css": str,
        "state_name": str,
        "from": int,
        "until": int,
        "from_text": str,
        "until_text": str,
        "duration_text": str,
        "site": SiteId,
        "log_output": NotRequired[str],
        "long_log_output": NotRequired[str],
    },
)


class AVLayoutTimeline(TypedDict):
    range: AVTimeRange
    spans: list[AVTimelineSpan]
    time_choords: list[tuple[float, str]]
    render_date: Callable[[AVTimeStamp], str]
    table: list[AVLayoutTimelineRow]


class AVLayoutTableRow(TypedDict):
    urls: list[AVIconSpec]
    object: AVObjectCells
    cells: AVRowCells
    timeline: NotRequired[AVLayoutTimeline]


class AVLayoutTable(TypedDict):
    title: str | None
    rows: list[AVLayoutTableRow]
    object_titles: list[str]
    cell_titles: list[tuple[str, str | None]]
    summary: NotRequired[AVRowCells]


AVBIPhaseData = dict[tuple[HostName, ServiceName], Row]
AVBIPhases = list[tuple[int, AVBIPhaseData]]
AVBITimelineState = tuple[int, str, bool, bool]  # state, output, in_downtime, in_service_period
AVBITimelineStates = dict[tuple[SiteId, HostName, ServiceName], AVBITimelineState]
AVLevels = tuple[float, float]


class AVOptionDowntimes(TypedDict):
    include: Literal["honor", "ignore", "exclude"]
    exclude_ok: bool


class AVOptionConsider(TypedDict):
    flapping: bool
    host_down: bool
    unmonitored: bool


class AVOptionStateGrouping(TypedDict):
    warn: Literal["ok", "warn", "crit", "unknown"]
    unknown: Literal["ok", "warn", "crit", "unknown"]
    host_down: Literal["ok", "warn", "crit", "unknown", "host_down"]


class AVOptionHostStateGrouping(TypedDict):
    unreach: Literal["up", "down", "unreach"]


# The functional TypedDict form is required here because "non-ok" is not a valid
# Python identifier and cannot be used as a key in the class-body syntax.
AVOptionFilterOutages = TypedDict(
    "AVOptionFilterOutages",
    {
        "warn": float,
        "crit": float,
        "non-ok": float,
    },
)


class AVOptions(TypedDict):
    range: AVRangeSpec
    rangespec: TimerangeValue
    labelling: list[AVTimelineLabelling]
    av_levels: AVLevels | None
    outage_statistics: AVOutageStatistics
    timeformat: AVTimeformatSpec
    av_mode: bool
    grouping: Literal["host", "host_groups", "service_groups"] | None
    dateformat: Literal["yyyy-mm-dd hh:mm:ss", "epoch"]
    summary: Literal["sum", "average"] | None
    show_timeline: bool
    downtimes: AVOptionDowntimes
    consider: AVOptionConsider
    state_grouping: AVOptionStateGrouping
    av_filter_outages: AVOptionFilterOutages
    host_state_grouping: AVOptionHostStateGrouping
    service_period: Literal["honor", "ignore", "exclude"]
    notification_period: Literal["honor", "exclude", "ignore"]
    short_intervals: int
    dont_merge: bool
    timelimit: int
    logrow_limit: int
    # Only present in the reporting context, where the stored report element
    # configuration selects which parts of the availability output to render.
    elements: NotRequired[list[Literal["timebar", "timeline", "table"]]]


_ColumnSpec = tuple[str, str, str, str | None]

SiteHostSvc = tuple[SiteId, HostName, ServiceName | None]
