#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable
from typing import Any, Literal

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
AVSpan = dict[str, Any]  # TODO: Improve this type
SiteHost = tuple[SiteId, HostName]
AVRawServices = dict[ServiceName, list[AVSpan]]
AVRawData = dict[SiteHost, AVRawServices]
AVEntry = dict[str, Any]
AVData = list[AVEntry]
AVTimelineSpan = tuple[int | None, str, float, CSSClass]
AVObjectCells = list[tuple[str, str]]
AVRowCells = list[tuple[HTML | str, CSSClass]]
AVGroups = list[tuple[str | None, AVData]]
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
