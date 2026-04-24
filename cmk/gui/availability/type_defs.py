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
from cmk.gui.valuespec import ValueSpec
from cmk.gui.view_utils import CSSClass
from cmk.utils.servicename import ServiceName

AVMode = str  # TODO: Improve this type
AVObjectType = Literal["host", "service", "bi"]
AVOptions = dict[str, Any]  # TODO: Improve this type
AVOptionValueSpecs = list[tuple[str, Literal["double", "single"], bool, ValueSpec[Any]]]
AVBIObjectSpec = tuple[None, None, str]
AVHostOrServiceObjectSpec = tuple[SiteId, HostName, ServiceName]
AVObjectSpec = None | AVBIObjectSpec | AVHostOrServiceObjectSpec
AVOutageStatisticsAggregations = list[Literal["min", "max", "avg", "cnt"]]
AVOutageStatisticsStates = list[
    Literal[
        "ok",
        "warn",
        "crit",
        "unknown",
        "flapping",
        "host_down",
        "in_downtime",
        "outof_notification_period",
    ]
]
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
AVTimelineSpan = tuple[int | None, str, float, CSSClass]
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
AVTimeformatSpec = (
    AVTimeformatSpecLegacy
    | tuple[
        Literal["both", "perc", "time"],
        Literal["percentage_0", "percentage_1", "percentage_2", "percentage_3"],
        Literal["seconds", "minutes", "hours", "hhmmss"],
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

AVLayoutTimeline = dict[str, Any]  # TODO: Improve this type
AVLayoutTimelineRow = dict[str, Any]  # TODO: Improve this type
AVLayoutTable = dict[str, Any]  # TODO: Improve this type
AVLayoutTableRow = dict[str, Any]  # TODO: Improve this type

AVBIPhaseData = dict[tuple[HostName, ServiceName], Row]
AVBIPhases = list[tuple[int, AVBIPhaseData]]
AVBITimelineState = tuple[int, str, bool, bool]  # state, output, in_downtime, in_service_period
AVBITimelineStates = dict[tuple[SiteId, HostName, ServiceName], AVBITimelineState]
AVLevels = tuple[float, float]

_ColumnSpec = tuple[str, str, str, str | None]

SiteHostSvc = tuple[SiteId, HostName, ServiceName | None]
