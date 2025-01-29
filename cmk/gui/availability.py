#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import functools
import itertools
import os
import time
from collections.abc import Callable, Generator, Iterator, Sequence
from typing import Any, Literal, NamedTuple

from livestatus import (
    LivestatusRow,
    lq_logic,
    lqencode,
    MKLivestatusPayloadTooLargeError,
    OnlySites,
    Query,
    QuerySpecification,
    SiteId,
)

import cmk.ccc.version as cmk_version
from cmk.ccc import store

import cmk.utils.paths
from cmk.utils import dateutils
from cmk.utils.cpu_tracking import CPUTracker
from cmk.utils.hostaddress import HostName
from cmk.utils.servicename import ServiceName

from cmk.gui import sites
from cmk.gui.bi import BIManager
from cmk.gui.data_source import query_livestatus
from cmk.gui.exceptions import MKUserError
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.logged_in import user
from cmk.gui.num_split import key_num_split
from cmk.gui.type_defs import (
    FilterHeader,
    HTTPVariables,
    Row,
    Rows,
    ViewProcessTracking,
    VisualContext,
)
from cmk.gui.utils import cmp_service_name_equiv
from cmk.gui.utils.html import HTML
from cmk.gui.utils.urls import makeuri, makeuri_contextless, urlencode_vars
from cmk.gui.utils.user_errors import user_errors
from cmk.gui.valuespec import (
    Age,
    Checkbox,
    Dictionary,
    DropdownChoice,
    Integer,
    ListChoice,
    Optional,
    Percentage,
    Timerange,
    Tuple,
    ValueSpec,
)
from cmk.gui.view_utils import CSSClass

from cmk.bi.lib import (
    BIHostSpec,
    BIHostStatusInfoRow,
    BIServiceWithFullState,
    BIStatusInfo,
    NodeComputeResult,
    NodeResultBundle,
)
from cmk.bi.trees import BICompiledAggregation, BICompiledRule, CompiledAggrTree

AVMode = str  # TODO: Improve this type
AVObjectType = Literal["host", "service", "bi"]
AVOptions = dict[str, Any]  # TODO: Improve this type
AVOptionValueSpecs = list[tuple[str, Literal["double", "single"], bool, ValueSpec]]
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
AVEntry = Any
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

ColumnSpec = tuple[str, str, str, str | None]

#   .--Declarations--------------------------------------------------------.
#   |       ____            _                 _   _                        |
#   |      |  _ \  ___  ___| | __ _ _ __ __ _| |_(_) ___  _ __  ___        |
#   |      | | | |/ _ \/ __| |/ _` | '__/ _` | __| |/ _ \| '_ \/ __|       |
#   |      | |_| |  __/ (__| | (_| | | | (_| | |_| | (_) | | | \__ \       |
#   |      |____/ \___|\___|_|\__,_|_|  \__,_|\__|_|\___/|_| |_|___/       |
#   |                                                                      |
#   '----------------------------------------------------------------------'


class AvailabilityColumns:
    def __init__(self) -> None:
        super().__init__()
        self.host = self._host_availability_columns()
        self.service = self._service_availability_columns()
        self.bi = self._bi_availability_columns()

    def __getitem__(self, key: str) -> list[ColumnSpec]:
        return getattr(self, key)

    def _host_availability_columns(self) -> list[ColumnSpec]:
        return [
            ("up", "state0", _("UP"), None),
            ("down", "state2", _("DOWN"), None),
            ("unreach", "state3", _("UNREACH"), None),
            ("flapping", "flapping", _("Flapping"), None),
            ("in_downtime", "downtime", _("Downtime"), _("The host was in a scheduled downtime")),
            ("outof_notification_period", "", _("OO/Notif"), _("Out of Notification Period")),
            ("outof_service_period", "ooservice", _("OO/Service"), _("Out of Service Period")),
            (
                "unmonitored",
                "unmonitored",
                _("N/A"),
                _("During this time period no monitoring data is available"),
            ),
        ]

    def _service_availability_columns(self) -> list[ColumnSpec]:
        return [
            ("ok", "state0", _("OK"), None),
            ("warn", "state1", _("WARN"), None),
            ("crit", "state2", _("CRIT"), None),
            ("unknown", "state3", _("UNKNOWN"), None),
            ("flapping", "flapping", _("Flapping"), None),
            ("host_down", "hostdown", _("H.Down"), _("The host was down")),
            (
                "in_downtime",
                "downtime",
                _("Downtime"),
                _("The host or service was in a scheduled downtime"),
            ),
            ("outof_notification_period", "", _("OO/Notif"), _("Out of Notification Period")),
            ("outof_service_period", "ooservice", _("OO/Service"), _("Out of Service Period")),
            (
                "unmonitored",
                "unmonitored",
                _("N/A"),
                _("During this time period no monitoring data is available"),
            ),
        ]

    def _bi_availability_columns(self) -> list[ColumnSpec]:
        return [
            ("ok", "state0", _("OK"), None),
            ("warn", "state1", _("WARN"), None),
            ("crit", "state2", _("CRIT"), None),
            ("unknown", "state3", _("UNKNOWN"), None),
            (
                "in_downtime",
                "downtime",
                _("Downtime"),
                _("The aggregate was in a scheduled downtime"),
            ),
            (
                "unmonitored",
                "unmonitored",
                _("N/A"),
                _("During this time period no monitoring data is available"),
            ),
        ]


# .
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

# Options for availability computation and rendering. These are four-tuple
# with the columns:
# 1. variable name
# 2. show in single or double height box
# 3. use this in reporting
# 4. the valuespec


def get_av_display_options(what: AVObjectType) -> AVOptionValueSpecs:
    if what == "bi":
        grouping_choices = [
            (None, _("Do not group")),
            ("host", _("By aggregation group")),
        ]
    else:
        grouping_choices = [
            (None, _("Do not group")),
            ("host", _("By host")),
            ("host_groups", _("By host group")),
            ("service_groups", _("By service group")),
        ]

    if cmk_version.edition(cmk.utils.paths.omd_root) is not cmk_version.Edition.CRE:
        ruleset_search_url = makeuri_contextless(
            request,
            [
                ("filled_in", "search"),
                ("search", "long_output"),
                ("mode", "rule_search"),
            ],
            filename="wato.py",
        )
        long_output_labelling = [
            (
                "timeline_long_output",
                _('Display long output in timeline (<a href="%s">Enable in Setup</a>)')
                % ruleset_search_url,
            )
        ]
    else:
        long_output_labelling = []

    return [
        # Time range selection
        ("rangespec", "double", False, vs_rangespec()),
        # Labelling and Texts
        (
            "labelling",
            "double",
            True,
            ListChoice(
                title=_("Labelling options"),
                choices=[
                    ("omit_headers", _("Do not display column headers")),
                    ("omit_host", _("Do not display the host name")),
                    ("show_alias", _("Display the host alias")),
                    ("use_display_name", _("Use alternative display name for services")),
                    ("omit_buttons", _("Do not display icons for history and timeline")),
                    ("omit_timeline_plugin_output", _("Do not display plug-in output in timeline")),
                ]
                + long_output_labelling
                + [
                    ("display_timeline_legend", _("Display legend for timeline")),
                    ("omit_av_levels", _("Do not display legend for availability levels")),
                ],
            ),
        ),
        # Visual levels for the availability
        (
            "av_levels",
            "double",
            True,
            Optional(
                valuespec=Tuple(
                    elements=[
                        Percentage(
                            title=_("Warning below"),
                            default_value=99,
                            size=7,
                        ),
                        Percentage(
                            title=_("Critical below"),
                            default_value=95,
                            size=7,
                        ),
                    ]
                ),
                title=_("Visual levels for the availability"),
                label=_("Visual levels for the availability (OK percentage)"),
            ),
        ),
        # Show colummns for min, max, avg duration and count
        (
            "outage_statistics",
            "double",
            True,
            Tuple(
                title=_("Outage statistics"),
                orientation="horizontal",
                elements=[
                    ListChoice(
                        title=_("Aggregations"),
                        choices=[
                            ("min", _("min. duration")),
                            ("max", _("max. duration")),
                            ("avg", _("avg. duration")),
                            ("cnt", _("count")),
                        ],
                    ),
                    ListChoice(
                        title=_("For these states:"),
                        columns=2,
                        choices=[
                            ("ok", _("OK/Up")),
                            ("warn", _("Warn")),
                            ("crit", _("Crit/Down")),
                            ("unknown", _("Unknown/Unreach")),
                            ("flapping", _("Flapping")),
                            ("host_down", _("Host down")),
                            ("in_downtime", _("Downtime")),
                            ("outof_notification_period", _("OO/Notif")),
                        ],
                    ),
                ],
            ),
        ),
        (
            "timeformat",
            "double",
            True,
            Tuple(
                title=_("Format time ranges"),
                elements=[
                    DropdownChoice(
                        choices=[
                            ("both", _("Percent and time")),
                            ("perc", _("Only percent")),
                            ("time", _("Only time")),
                        ],
                        default_value="perc",
                    ),
                    DropdownChoice(
                        choices=[
                            ("percentage_0", _("Percentage - XX %")),
                            ("percentage_1", _("Percentage - XX.X %")),
                            ("percentage_2", _("Percentage - XX.XX %")),
                            ("percentage_3", _("Percentage - XX.XXX %")),
                        ],
                        default_value="percentage_2",
                    ),
                    DropdownChoice(
                        choices=[
                            ("seconds", _("Seconds")),
                            ("minutes", _("Minutes")),
                            ("hours", _("Hours")),
                            ("hhmmss", _("HH:MM:SS")),
                        ],
                    ),
                ],
            ),
        ),
        # Omit all non-OK columns
        (
            "av_mode",
            "single",
            True,
            Checkbox(
                title=_("Availability"),
                label=_("Just show the availability (i.e. OK/UP)"),
            ),
        ),
        # Group by host, host group or service group?
        (
            "grouping",
            "single",
            True,
            DropdownChoice(
                title=_("Grouping"),
                choices=grouping_choices,
                default_value=None,
            ),
        ),
        # Format of numbers
        (
            "dateformat",
            "single",
            True,
            DropdownChoice(
                title=_("Format time stamps as"),
                choices=[
                    ("yyyy-mm-dd hh:mm:ss", _("YYYY-MM-DD HH:MM:SS")),
                    ("epoch", _("Unix Timestamp (Epoch)")),
                ],
                default_value="yyyy-mm-dd hh:mm:ss",
            ),
        ),
        # Summary line
        (
            "summary",
            "single",
            True,
            DropdownChoice(
                title=_("Summary line"),
                choices=[
                    (None, _("Do not show a summary line")),
                    (
                        "sum",
                        # xgettext: no-python-format
                        _("Display total sum (for % the average)"),
                    ),
                    ("average", _("Display average")),
                ],
                default_value="sum",
            ),
        ),
        # Timeline
        (
            "show_timeline",
            "single",
            True,
            Checkbox(
                title=_("Timeline"),
                label=_("Show timeline of each object directly in table"),
            ),
        ),
    ]


def vs_rangespec() -> Timerange:
    return Timerange(
        title=_("Time range"),
        default_value="d0",
    )


def get_av_computation_options() -> AVOptionValueSpecs:
    return [
        # How to deal with downtimes
        (
            "downtimes",
            "double",
            True,
            Dictionary(
                title=_("Scheduled downtimes"),
                columns=2,
                elements=[
                    (
                        "include",
                        DropdownChoice(
                            title=_("Handling"),
                            choices=[
                                ("honor", _("Honor scheduled downtimes")),
                                ("ignore", _("Ignore scheduled downtimes")),
                                ("exclude", _("Exclude scheduled downtimes")),
                            ],
                            default_value="honor",
                        ),
                    ),
                    (
                        "exclude_ok",
                        Checkbox(
                            title=_("Phases"), label=_("Treat phases of UP/OK as non-downtime")
                        ),
                    ),
                ],
                optional_keys=False,
            ),
        ),
        # How to deal with downtimes, etc.
        (
            "consider",
            "double",
            True,
            Dictionary(
                title=_("Status classification"),
                columns=2,
                elements=[
                    (
                        "flapping",
                        Checkbox(
                            title=_("Consider periods of flapping states"), default_value=True
                        ),
                    ),
                    (
                        "host_down",
                        Checkbox(
                            title=_("Consider times where the host is down"), default_value=True
                        ),
                    ),
                    (
                        "unmonitored",
                        Checkbox(title=_("Include unmonitored time"), default_value=True),
                    ),
                ],
                optional_keys=False,
            ),
        ),
        (
            "state_grouping",
            "double",
            True,
            Dictionary(
                title=_("Service status grouping"),
                columns=2,
                elements=[
                    (
                        "warn",
                        DropdownChoice(
                            title=_("Treat warning as"),
                            choices=[
                                ("ok", _("OK")),
                                ("warn", _("WARN")),
                                ("crit", _("CRIT")),
                                ("unknown", _("UNKNOWN")),
                            ],
                            default_value="warn",
                        ),
                    ),
                    (
                        "unknown",
                        DropdownChoice(
                            title=_("Treat unknown/unreachable as"),
                            choices=[
                                ("ok", _("OK")),
                                ("warn", _("WARN")),
                                ("crit", _("CRIT")),
                                ("unknown", _("UNKNOWN")),
                            ],
                            default_value="unknown",
                        ),
                    ),
                    (
                        "host_down",
                        DropdownChoice(
                            title=_("Treat host down as"),
                            choices=[
                                ("ok", _("OK")),
                                ("warn", _("WARN")),
                                ("crit", _("CRIT")),
                                ("unknown", _("UNKNOWN")),
                                ("host_down", _("Host Down")),
                            ],
                            default_value="host_down",
                        ),
                    ),
                ],
                optional_keys=False,
            ),
        ),
        # Filter rows according to actual availability
        (
            "av_filter_outages",
            "double",
            True,
            Dictionary(
                title=_("Only show objects with outages"),
                columns=2,
                elements=[
                    (
                        "warn",
                        Percentage(
                            title=_("Show only rows with WARN of at least"), default_value=0.0
                        ),
                    ),
                    (
                        "crit",
                        Percentage(
                            title=_("Show only rows with CRIT of at least"), default_value=0.0
                        ),
                    ),
                    (
                        "non-ok",
                        Percentage(
                            title=_("Show only rows with non-OK of at least"), default_value=0.0
                        ),
                    ),
                ],
                optional_keys=False,
            ),
        ),
        # Optionally group some states together
        (
            "host_state_grouping",
            "single",
            True,
            Dictionary(
                title=_("Host status grouping"),
                columns=2,
                elements=[
                    (
                        "unreach",
                        DropdownChoice(
                            # TOOD: aligned
                            title=_("Treat unreachable as"),
                            choices=[
                                ("up", _("UP")),
                                ("down", _("DOWN")),
                                ("unreach", _("UNREACH")),
                            ],
                            default_value="unreach",
                        ),
                    ),
                ],
                optional_keys=False,
            ),
        ),
        # How to deal with the service periods
        (
            "service_period",
            "single",
            True,
            DropdownChoice(
                title=_("Service time"),
                choices=[
                    ("honor", _("Base report only on service times")),
                    ("ignore", _("Include both service and non-service times")),
                    ("exclude", _("Base report only on non-service times")),
                ],
                default_value="honor",
            ),
        ),
        # How to deal with times out of the notification period
        (
            "notification_period",
            "single",
            True,
            DropdownChoice(
                title=_("Notification period"),
                choices=[
                    ("honor", _("Distinguish times in and out of notification period")),
                    ("exclude", _("Exclude times out of notification period")),
                    ("ignore", _("Ignore notification period")),
                ],
                default_value="ignore",
            ),
        ),
        # Short time intervals
        (
            "short_intervals",
            "single",
            True,
            Integer(
                title=_("Short time intervals"),
                label=_("Ignore intervals shorter or equal"),
                minvalue=0,
                unit=_("sec"),
                default_value=0,
            ),
        ),
        # Merging
        (
            "dont_merge",
            "single",
            True,
            Checkbox(
                title=_("Phase merging"),
                label=_("Do not merge consecutive phases with equal state"),
            ),
        ),
        (
            "timelimit",
            "single",
            False,
            Age(
                title=_("Query time limit"),
                help=_(
                    "Limit the execution time of the query, in order to avoid a hanging system."
                ),
                default_value=30,
            ),
        ),
        (
            "logrow_limit",
            "single",
            True,
            Integer(
                title=_("Limit processed data"),
                help=_(
                    "The availability is computed by processing entries from a data table "
                    "of historic events and state phases. In order to avoid a hanging system "
                    "in cases where your time range and filtering would accept a vast amount "
                    "of data entries, the number of processed entries is limited. You can raise "
                    "this limit here if you really need to process a huge amount of data. Set this "
                    "to zero in order to disable the limit."
                ),
                label=_("Process at most"),
                unit=_("status entries"),
                minvalue=0,
                default_value=5000,
                size=6,
            ),
        ),
    ]


# Creates a function for rendering time values according to
# the avoptions of the report.
def render_number_function(timeformat: str) -> Callable[[AVTimeStamp, int], str]:
    if timeformat.startswith("percentage_"):

        def render_number(n: AVTimeStamp, d: int) -> str:
            if not d:
                return _("n/a")
            return ("%." + timeformat[11:] + "f%%") % (float(n) / float(d) * 100.0)

    elif timeformat == "seconds":

        def render_number(n: AVTimeStamp, d: int) -> str:
            return "%d s" % n

    elif timeformat == "minutes":

        def render_number(n: AVTimeStamp, d: int) -> str:
            return "%d min" % (n / 60)

    elif timeformat == "hours":

        def render_number(n: AVTimeStamp, d: int) -> str:
            return "%d h" % (n / 3600)

    else:

        def render_number(n: AVTimeStamp, d: int) -> str:
            minn, sec = divmod(n, 60)
            hours, minn = divmod(minn, 60)
            return "%02d:%02d:%02d" % (hours, minn, sec)

    return render_number


def prepare_avo_timeformats(timeformat: AVTimeformatSpec) -> AVTimeFormats:
    """Processes the information provided in the Format time ranges section

    Args:
        timeformat:
            list containing the options of the three dropdown menus in the 'Format time ranges' section

    Returns:
        list containing the value rendering options

    """
    this_timeformat = [("percentage_2", render_number_function("percentage_2"))]
    if isinstance(timeformat, (list, tuple)):
        if timeformat[0] == "both":
            this_timeformat = [
                (timeformat[1], render_number_function(timeformat[1])),
                (timeformat[2], render_number_function(timeformat[2])),
            ]
        elif timeformat[0] == "perc":
            this_timeformat = [(timeformat[1], render_number_function(timeformat[1]))]
        elif timeformat[0] == "time":
            this_timeformat = [(timeformat[2], render_number_function(timeformat[2]))]
    elif isinstance(timeformat, str) and (
        timeformat.startswith("percentage_")
        or timeformat in ["seconds", "minutes", "hours", "hhmmss"]
    ):
        # Old style
        this_timeformat = [(timeformat, render_number_function(timeformat))]
    return this_timeformat


def get_default_avoptions(range_spec: tuple[float, float] | None = None) -> AVOptions:
    if range_spec is None:
        range_spec = time.time() - 86400, time.time()
    return {
        "range": (range_spec, ""),
        "rangespec": "d0",
        "labelling": [],
        "av_levels": None,
        "av_filter_outages": {"warn": 0.0, "crit": 0.0, "non-ok": 0.0},
        "outage_statistics": ([], []),
        "av_mode": False,
        "service_period": "honor",
        "notification_period": "ignore",
        "grouping": None,
        "dateformat": "yyyy-mm-dd hh:mm:ss",
        "timeformat": ("perc", "percentage_2", None),
        "short_intervals": 0,
        "dont_merge": False,
        "summary": "sum",
        "show_timeline": False,
        "timelimit": 30,
        "logrow_limit": 5000,
        "downtimes": {
            "include": "honor",
            "exclude_ok": False,
        },
        "consider": {
            "flapping": True,
            "host_down": True,
            "unmonitored": True,
        },
        "host_state_grouping": {
            "unreach": "unreach",
        },
        "state_grouping": {
            "warn": "warn",
            "unknown": "unknown",
            "host_down": "host_down",
        },
    }


def get_outage_statistic_options(avoptions: AVOptions) -> AVOutageStatistics:
    # Outage options are stored with keys matching service states (like "ok" and "crit").
    # For hosts we use the same checkbox but mean "up" and "down". We simply add these states
    # to the list of selected states.
    aggrs, states = avoptions.get("outage_statistics", ([], []))
    fixed_states = states[:]
    for service_state, host_state in [("ok", "up"), ("crit", "down"), ("unknown", "unreach")]:
        if service_state in fixed_states:
            fixed_states.append(host_state)
    return aggrs, fixed_states


def get_availability_options_from_request(what: AVObjectType) -> AVOptions:
    avoptions = get_default_avoptions()

    # Users of older versions might not have all keys set. The following
    # trick will merge their options with our default options.
    avoptions.update(user.load_file("avoptions", {}))

    form_name = request.get_ascii_input("filled_in")
    if form_name == "avoptions_display":
        avoption_entries = get_av_display_options(what)
    elif form_name == "avoptions_computation":
        avoption_entries = get_av_computation_options()
    else:
        avoption_entries = []

    if request.var("avoptions") == "set":
        for name, _height, _show_in_reporting, vs in avoption_entries:
            try:
                avoptions[name] = vs.from_html_vars("avo_" + name)
                vs.validate_value(avoptions[name], "avo_" + name)
            except MKUserError as e:
                user_errors.add(e)

    range_vs = vs_rangespec()
    try:
        range_, range_title = range_vs.compute_range(avoptions["rangespec"])
        avoptions["range"] = range_, range_title
    except MKUserError as e:
        user_errors.add(e)

    if request.var("_unset_logrow_limit") == "1":
        avoptions["logrow_limit"] = 0

    return avoptions


# .
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
# what is either "host" or "service" or "bi".
def get_availability_rawdata(
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
    if what == "bi":
        return get_bi_availability_rawdata(
            filterheaders, only_sites, av_object, include_output, avoptions
        )

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
            for span in service_entry:
                # Information about host/service groups are in the actual entries
                if grouping in ["host_groups", "service_groups"] and what != "bi":
                    assert isinstance(group_ids, set)
                    group_ids.update(span[grouping])  # List of host/service groups

                display_name = span.get("service_display_name", service)
                state = span["state"]
                host_alias = span.get("host_alias", site_host[1])
                consider = True

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


class ReclassifyConfig(NamedTuple):
    downtime: Any | None
    host_state: Any | None
    service_state: Any | None


def reclassify_history_by_annotations(
    history: list[AVSpan], annotation_entries: list[AVAnnotationEntry]
) -> list[AVSpan]:
    new_history = history
    for annotation in annotation_entries:
        downtime = annotation.get("downtime")
        host_state = annotation.get("host_state")
        service_state = annotation.get("service_state")
        if downtime is None and host_state is None and service_state is None:
            continue

        new_config = ReclassifyConfig(
            downtime=downtime,
            host_state=host_state,
            service_state=service_state,
        )

        new_history = reclassify_history_by_annotation(new_history, annotation, new_config)
    return new_history


def reclassify_history_by_annotation(
    history: list[AVSpan],
    annotation: AVAnnotationEntry,
    new_config: ReclassifyConfig,
) -> list[AVSpan]:
    new_history: list[AVSpan] = []
    for history_entry in history:
        new_history += reclassify_times_by_annotation(history_entry, annotation, new_config)

    return new_history


def reclassify_times_by_annotation(
    history_entry: AVSpan,
    annotation: AVAnnotationEntry,
    new_config: ReclassifyConfig,
) -> list[AVSpan]:
    new_history = []
    if annotation["from"] < history_entry["until"] and annotation["until"] > history_entry["from"]:
        for is_in, p_from, p_until in [
            (False, history_entry["from"], max(history_entry["from"], annotation["from"])),
            (
                True,
                max(history_entry["from"], annotation["from"]),
                min(history_entry["until"], annotation["until"]),
            ),
            (False, min(history_entry["until"], annotation["until"]), history_entry["until"]),
        ]:
            if p_from < p_until:
                new_entry = history_entry.copy()
                new_entry["from"] = p_from
                new_entry["until"] = p_until
                new_entry["duration"] = p_until - p_from
                if is_in:
                    reclassify_config_by_annotation(
                        history_entry, annotation, new_entry, new_config
                    )

                new_history.append(new_entry)
    else:
        new_history.append(history_entry)

    return new_history


def reclassify_config_by_annotation(
    history_entry: AVSpan,
    annotation: AVAnnotationEntry,
    new_entry: AVSpan,
    new_config: ReclassifyConfig,
) -> AVSpan:
    if new_config.downtime is not None:
        new_entry["in_downtime"] = 1 if annotation["downtime"] else 0
        # If the annotation removes a downtime from the services, but
        # the actual reason for the service being in downtime is a host
        # downtime, then we must cancel the host downtime (also), or else
        # that would override the unset service downtime.
        if history_entry.get("in_host_downtime") and annotation["downtime"] is False:
            new_entry["in_host_downtime"] = 0
    if new_config.host_state is not None:
        new_host_state = annotation.get("host_state", history_entry.get("host_state"))
        new_entry["state"] = new_host_state
        new_entry["host_down"] = 1 if new_host_state else 0
    if new_config.service_state is not None:
        new_entry["state"] = annotation.get("service_state", history_entry.get("state"))

    return new_entry


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
            ref_value = 0.0
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
    if grouping != "host":
        group_titles = dict(sites.all_groups(grouping[:-7]))

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
        return av_entry["host"]
    # service and BI
    return av_entry["host"] + " / " + av_entry["service"]


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


# .
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
#            "service_state"  : 1,
#            "from"           : 1238288548,
#            "until"          : 1238292845,
#            "text"           : u"Das ist ein Text über mehrere Zeilen, oder was weiß ich",
#            "date"           : 12348854885, # Time of entry
#            "author"         : "mk",
#            "downtime"       : True, # Can also be False or None or missing. None is like missing
#         },
#         # ... further entries
#      ]
# }


def save_annotations(annotations: AVAnnotations) -> None:
    path = cmk.utils.paths.var_dir + "/availability_annotations.mk"
    store.save_object_to_file(path, annotations)


def load_annotations(lock: bool = False) -> AVAnnotations:
    path = cmk.utils.paths.var_dir + "/availability_annotations.mk"
    if not os.path.exists(path):
        # Support legacy old wrong name-clashing path
        path = cmk.utils.paths.var_dir + "/web/statehist_annotations.mk"

    return store.load_object_from_file(path, default={}, lock=lock)


def update_annotations(
    site_host_svc: AVAnnotationKey,
    annotation: AVAnnotationEntry,
    replace_existing: AVAnnotationEntry | None,
) -> None:
    annotations = load_annotations(lock=True)
    entries = annotations.get(site_host_svc, [])
    new_entries = []
    for entry in entries:
        if entry == replace_existing:
            continue  # Skip existing entries with same identity
        new_entries.append(entry)
    new_entries.append(annotation)
    annotations[site_host_svc] = new_entries
    save_annotations(annotations)


def find_annotation(
    annotations: AVAnnotations,
    site_host_svc: AVAnnotationKey,
    host_state: str | None,
    service_state: str | None,
    fromtime: AVTimeStamp,
    untiltime: AVTimeStamp,
) -> AVAnnotationEntry | None:
    entries = annotations.get(site_host_svc)
    if not entries:
        return None
    for annotation in entries:
        if annotation["from"] == fromtime and annotation["until"] == untiltime:
            return annotation
    return None


def delete_annotation(
    annotations: AVAnnotations,
    site_host_svc: AVAnnotationKey,
    host_state: str | None,
    service_state: str | None,
    fromtime: AVTimeStamp,
    untiltime: AVTimeStamp,
) -> None:
    entries = annotations.get(site_host_svc)
    if not entries:
        return

    found = None
    for nr, annotation in enumerate(entries):
        if annotation["from"] == fromtime and annotation["until"] == untiltime:
            found = nr
            break

    if found is not None:
        del entries[found]


def get_relevant_annotations(annotations, by_host, what, avoptions):
    time_range: AVTimeRange = avoptions["range"][0]
    from_time, until_time = time_range

    annos_to_render = []
    annos_rendered: set[int] = set()

    for site_host, avail_entries in by_host.items():
        for service in avail_entries.keys():
            for search_what in ["host", "service"]:
                if what == "host" and search_what == "service":
                    continue  # Service annotations are not relevant for host

                if search_what == "host":
                    site_host_svc = site_host[0], site_host[1], None
                else:
                    site_host_svc = site_host[0], site_host[1], service  # service can be None

                for annotation in annotations.get(site_host_svc, []):
                    if _annotation_affects_time_range(
                        annotation["from"], annotation["until"], from_time, until_time
                    ):
                        if id(annotation) not in annos_rendered:
                            annos_to_render.append((site_host_svc, annotation))
                            annos_rendered.add(id(annotation))

    return annos_to_render


def get_annotation_date_render_function(annotations, avoptions):
    timestamps = list(
        itertools.chain.from_iterable(
            [(a[1]["from"], a[1]["until"]) for a in annotations] + [avoptions["range"][0]]
        )
    )

    multi_day = len({time.localtime(t)[:3] for t in timestamps}) > 1
    if multi_day:
        return cmk.utils.render.date_and_time
    return cmk.utils.render.time_of_day


def _annotation_affects_time_range(annotation_from, annotation_until, from_time, until_time):
    return not (annotation_until < from_time or annotation_from > until_time)


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

    availability_columns = AvailabilityColumns()
    # Titles for the columns that specify the object
    av_table["object_titles"] = object_column_titles(labelling, what)

    # Headers for availability cells
    os_aggrs, os_states = get_outage_statistic_options(avoptions)
    av_table["cell_titles"] = _availability_cell_headers(
        availability_columns, avoptions, os_aggrs, os_states, timeformats, what
    )

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
            for sid, css, _sname, _help_txt in availability_columns[what]:
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
            summary["ok_level"] = sum(
                float(entry["states"].get("ok", 0)) / entry["considered_duration"]
                for entry in availability_table
                if entry["considered_duration"] > 0
            )

    # Summary line. It has the same format as each entry in cells
    # We ignore unmonitored objects
    len_availability_table = len(availability_table) - unmonitored_objects
    if show_summary and len_availability_table > 0:
        summary_cells: AVRowCells = []

        for timeformat, render_number in timeformats:
            for sid, css, _sname, _help_txt in availability_columns[what]:
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
    availability_columns: AvailabilityColumns,
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
        for sid, _css, sname, help_txt in availability_columns[what]:
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
    availability_columns = AvailabilityColumns()

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

        for sid, css, sname, help_txt in availability_columns[what]:
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


# .
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

BIAggregationGroupTitle = str
BIAggregationTitle = str
BITreeState = Any
BITimelineEntry = Any


DEFAULT_MAX_TIME_RANGE = 31 * 24 * 60 * 60  # One month


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


def _get_timewarp_state(node_compute_result_bundle, timeline_container):
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
        "site": "",
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
        site_host = BIHostSpec(site_host_service[0], site_host_service[1])
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
                state,
                True,  # has_been_checked
                state_output[1],  # output
                state,  # hard state (we use the soft state here)
                1,  # attempt
                1,  # max_attempts (not relevant)
                state_output[2],  # in_downtime
                False,  # acknowledged
                state_output[3],  # in_service_period
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
            NodeComputeResult(-1, False, False, _("Not yet monitored"), True, {}, {}),
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
            state,  # state
            True,  # has_been_checked
            state,  # host hard state
            state_output[1],  # plug-in output
            state_output[2],  # in_downtime
            state_output[3],  # in_service_period
            False,  # acknowledged
            services_by_host.get(site_host, {}),
            {},  # remaining keys N/A
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


# .
#   .--Various-------------------------------------------------------------.
#   |                __     __         _                                   |
#   |                \ \   / /_ _ _ __(_) ___  _   _ ___                   |
#   |                 \ \ / / _` | '__| |/ _ \| | | / __|                  |
#   |                  \ V / (_| | |  | | (_) | |_| \__ \                  |
#   |                   \_/ \__,_|_|  |_|\___/ \__,_|___/                  |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Various other functions                                             |
#   '----------------------------------------------------------------------'


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
        all_group_ids.update(entry["groups"])
        if len(entry["groups"]) == 0:
            all_group_ids.add(None)  # None denotes ungrouped objects
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
