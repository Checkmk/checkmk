#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
import os

from typing import Callable, Set, Dict, Any, Union, List, NamedTuple, Tuple as _Tuple, Optional as _Optional

from livestatus import SiteId, LivestatusOutputFormat

import cmk.utils.version as cmk_version
import cmk.utils.defines as defines
import cmk.utils.paths
import cmk.utils.store as store
from cmk.utils.type_defs import HostName, ServiceName
from cmk.utils.prediction import lq_logic
from cmk.utils.bi.bi_lib import NodeComputeResult, NodeResultBundle

import cmk.gui.utils as utils
import cmk.gui.sites as sites
from cmk.gui.view_utils import CSSClass
from cmk.gui.type_defs import Rows, Row
from cmk.gui.valuespec import (
    Integer,
    Age,
    Checkbox,
    DropdownChoice,
    Dictionary,
    Percentage,
    Tuple,
    ListChoice,
    Optional,
    Timerange,
)
from cmk.gui.i18n import _
from cmk.gui.globals import html, request
from cmk.gui.utils.urls import makeuri, makeuri_contextless
from cmk.gui.utils.html import HTML
from cmk.gui.log import logger

AVMode = str  # TODO: Improve this type
AVObjectType = str  # TODO: Improve this type
AVOptions = Dict[str, Any]  # TODO: Improve this type
AVOptionValueSpecs = List  # TODO: Be more specific here
AVObjectSpec = Union[None, _Tuple[None, None, str], _Tuple[str, str, str]]
AVSpan = Dict[str, Any]  # TODO: Improve this type
SiteHost = _Tuple[SiteId, HostName]
AVRawServices = Dict[ServiceName, List[AVSpan]]
AVRawData = Dict[SiteHost, AVRawServices]
AVEntry = Any
AVData = List[AVEntry]
AVTimelineSpan = _Tuple[_Optional[int], str, float, CSSClass]
AVObjectCells = List[_Tuple[str, str]]
AVRowCells = List[_Tuple[Union[HTML, str], CSSClass]]
AVGroups = List[_Tuple[_Optional[str], AVData]]
HostOrServiceGroupName = str
AVGroupKey = Union[SiteHost, HostOrServiceGroupName, None]
AVGroupIds = Union[None, List[SiteHost], Set[HostOrServiceGroupName]]
AVTimeStamp = float
AVTimeRange = _Tuple[AVTimeStamp, AVTimeStamp]
AVTimeFormats = List[_Tuple[str, Callable[[AVTimeStamp, int], str]]]
AVRangeSpec = _Tuple[AVTimeRange, str]

AVTimelineStateName = str
AVTimelineRows = List[_Tuple[AVSpan, AVTimelineStateName]]
AVTimelineStates = Dict[AVTimelineStateName, int]
AVTimelineStatistics = Dict[AVTimelineStateName, _Tuple[int, int, int]]
AVTimelineStyle = str

from cmk.utils.bi.bi_data_fetcher import (
    BIServiceWithFullState,
    BIHostStatusInfoRow,
    BIStatusInfo,
    BIHostSpec,
)

from cmk.gui.bi import BIManager

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
AVAnnotationKey = _Tuple[SiteId, HostName, _Optional[ServiceName]]
AVAnnotationEntry = Dict[str, Any]
AVAnnotations = Dict[AVAnnotationKey, List[AVAnnotationEntry]]

AVLayoutTimeline = Dict[str, Any]  # TODO: Improve this type
AVLayoutTimelineRow = Dict[str, Any]  # TODO: Improve this type
AVLayoutTable = Dict[str, Any]  # TODO: Improve this type
AVLayoutTableRow = Dict[str, Any]  # TODO: Improve this type

AVBIPhaseData = Dict[_Tuple[HostName, ServiceName], Row]
AVBIPhases = List[_Tuple[int, AVBIPhaseData]]
AVBITimelineState = _Tuple[int, str, bool, bool]  # state, output, in_downtime, in_service_period
AVBITimelineStates = Dict[_Tuple[SiteId, HostName, ServiceName], AVBITimelineState]

#   .--Declarations--------------------------------------------------------.
#   |       ____            _                 _   _                        |
#   |      |  _ \  ___  ___| | __ _ _ __ __ _| |_(_) ___  _ __  ___        |
#   |      | | | |/ _ \/ __| |/ _` | '__/ _` | __| |/ _ \| '_ \/ __|       |
#   |      | |_| |  __/ (__| | (_| | | | (_| | |_| | (_) | | | \__ \       |
#   |      |____/ \___|\___|_|\__,_|_|  \__,_|\__|_|\___/|_| |_|___/       |
#   |                                                                      |
#   '----------------------------------------------------------------------'


class AvailabilityColumns:
    def __init__(self):
        super(AvailabilityColumns, self).__init__()
        self.host = self._host_availability_columns()
        self.service = self._service_availability_columns()
        self.bi = self._bi_availability_columns()

    def __getitem__(self, key):
        return getattr(self, key)

    def _host_availability_columns(self):
        return [
            ("up", "state0", _("UP"), None),
            ("down", "state2", _("DOWN"), None),
            ("unreach", "state3", _("UNREACH"), None),
            ("flapping", "flapping", _("Flapping"), None),
            ("in_downtime", "downtime", _("Downtime"), _("The host was in a scheduled downtime")),
            ("outof_notification_period", "", _("OO/Notif"), _("Out of Notification Period")),
            ("outof_service_period", "ooservice", _("OO/Service"), _("Out of Service Period")),
            ("unmonitored", "unmonitored", _("N/A"),
             _("During this time period no monitoring data is available")),
        ]

    def _service_availability_columns(self):
        return [
            ("ok", "state0", _("OK"), None),
            ("warn", "state1", _("WARN"), None),
            ("crit", "state2", _("CRIT"), None),
            ("unknown", "state3", _("UNKNOWN"), None),
            ("flapping", "flapping", _("Flapping"), None),
            ("host_down", "hostdown", _("H.Down"), _("The host was down")),
            ("in_downtime", "downtime", _("Downtime"),
             _("The host or service was in a scheduled downtime")),
            ("outof_notification_period", "", _("OO/Notif"), _("Out of Notification Period")),
            ("outof_service_period", "ooservice", _("OO/Service"), _("Out of Service Period")),
            ("unmonitored", "unmonitored", _("N/A"),
             _("During this time period no monitoring data is available")),
        ]

    def _bi_availability_columns(self):
        return [
            ("ok", "state0", _("OK"), None),
            ("warn", "state1", _("WARN"), None),
            ("crit", "state2", _("CRIT"), None),
            ("unknown", "state3", _("UNKNOWN"), None),
            ("in_downtime", "downtime", _("Downtime"),
             _("The aggregate was in a scheduled downtime")),
            ("unmonitored", "unmonitored", _("N/A"),
             _("During this time period no monitoring data is available")),
        ]


#.
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


def get_av_display_options(what) -> AVOptionValueSpecs:
    if what == "bi":
        grouping_choices = [
            (None, _("Do not group")),
            ("host", _("By Aggregation Group")),
        ]
    else:
        grouping_choices = [
            (None, _("Do not group")),
            ("host", _("By Host")),
            ("host_groups", _("By Host group")),
            ("service_groups", _("By Service group")),
        ]

    if not cmk_version.is_raw_edition():
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
            (u"timeline_long_output",
             _("Display long output in timeline (<a href=\"%s\">Enable via WATO</a>)") %
             ruleset_search_url)
        ]
    else:
        long_output_labelling = []

    return [
        # Time range selection
        ("rangespec", "double", False, vs_rangespec()),

        # Labelling and Texts
        ("labelling", "double", True,
         ListChoice(
             title=_("Labelling Options"),
             choices=[
                 (u"omit_headers", _("Do not display column headers")),
                 (u"omit_host", _("Do not display the host name")),
                 (u"show_alias", _("Display the host alias")),
                 (u"use_display_name", _("Use alternative display name for services")),
                 (u"omit_buttons", _("Do not display icons for history and timeline")),
                 (u"omit_timeline_plugin_output", _("Do not display plugin output in timeline")),
             ] + long_output_labelling + [
                 (u"display_timeline_legend", _("Display legend for timeline")),
                 (u"omit_av_levels", _("Do not display legend for availability levels")),
             ])),

        # Visual levels for the availability
        ("av_levels", "double", True,
         Optional(
             Tuple(elements=[
                 Percentage(
                     title=_("Warning below"), default_value=99, display_format="%.3f", size=7),
                 Percentage(
                     title=_("Critical below"), default_value=95, display_format="%.3f", size=7),
             ]),
             title=_("Visual levels for the availability (OK percentage)"),
         )),

        # Show colummns for min, max, avg duration and count
        ("outage_statistics", "double", True,
         Tuple(title=_("Outage statistics"),
               orientation="horizontal",
               elements=[
                   ListChoice(title=_("Aggregations"),
                              choices=[
                                  ("min", _("min. duration")),
                                  ("max", _("max. duration")),
                                  ("avg", _("avg. duration")),
                                  ("cnt", _("count")),
                              ]),
                   ListChoice(title=_("For these states:"),
                              columns=2,
                              choices=[
                                  ("ok", _("OK/Up")),
                                  ("warn", _("Warn")),
                                  ("crit", _("Crit/Down")),
                                  ("unknown", _("Unknown/Unreach")),
                                  ("flapping", _("Flapping")),
                                  ("host_down", _("Host Down")),
                                  ("in_downtime", _("Downtime")),
                                  ("outof_notification_period", _("OO/Notif")),
                              ])
               ])),
        ("timeformat", "double", True,
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
                 DropdownChoice(choices=[
                     ("percentage_0", _("Percentage - XX %")),
                     ("percentage_1", _("Percentage - XX.X %")),
                     ("percentage_2", _("Percentage - XX.XX %")),
                     ("percentage_3", _("Percentage - XX.XXX %")),
                 ],
                                default_value="percentage_2"),
                 DropdownChoice(choices=[
                     ("seconds", _("Seconds")),
                     ("minutes", _("Minutes")),
                     ("hours", _("Hours")),
                     ("hhmmss", _("HH:MM:SS")),
                 ],
                                default_value=None),
             ],
         )),

        # Omit all non-OK columns
        ("av_mode", "single", True,
         Checkbox(
             title=_("Availability"),
             label=_("Just show the availability (i.e. OK/UP)"),
         )),

        # Group by Host, Hostgroup or Servicegroup?
        ("grouping", "single", True,
         DropdownChoice(
             title=_("Grouping"),
             choices=grouping_choices,
             default_value=None,
         )),

        # Format of numbers
        ("dateformat", "single", True,
         DropdownChoice(
             title=_("Format time stamps as"),
             choices=[
                 ("yyyy-mm-dd hh:mm:ss", _("YYYY-MM-DD HH:MM:SS")),
                 ("epoch", _("Unix Timestamp (Epoch)")),
             ],
             default_value="yyyy-mm-dd hh:mm:ss",
         )),

        # Summary line
        ("summary", "single", True,
         DropdownChoice(
             title=_("Summary line"),
             choices=[
                 (None, _("Do not show a summary line")),
                 ("sum", _("Display total sum (for % the average)")),
                 ("average", _("Display average")),
             ],
             default_value="sum",
         )),

        # Timeline
        ("show_timeline", "single", True,
         Checkbox(
             title=_("Timeline"),
             label=_("Show timeline of each object directly in table"),
         )),
    ]


def vs_rangespec():
    return Timerange(
        title=_("Time Range"),
        default_value='d0',
    )


def get_av_computation_options() -> AVOptionValueSpecs:
    return [
        # How to deal with downtimes
        ("downtimes", "double", True,
         Dictionary(
             title=_("Scheduled Downtimes"),
             columns=2,
             elements=[
                 ("include",
                  DropdownChoice(
                      title=_("Handling"),
                      choices=[
                          ("honor", _("Honor scheduled downtimes")),
                          ("ignore", _("Ignore scheduled downtimes")),
                          ("exclude", _("Exclude scheduled downtimes")),
                      ],
                      default_value="honor",
                  )),
                 ("exclude_ok",
                  Checkbox(title=_("Phases"), label=_("Treat phases of UP/OK as non-downtime"))),
             ],
             optional_keys=False,
         )),

        # How to deal with downtimes, etc.
        ("consider", "double", True,
         Dictionary(
             title=_("Status Classification"),
             columns=2,
             elements=[
                 ("flapping",
                  Checkbox(title=_("Consider periods of flapping states"), default_value=True)),
                 ("host_down",
                  Checkbox(title=_("Consider times where the host is down"), default_value=True)),
                 ("unmonitored", Checkbox(title=_("Include unmonitored time"), default_value=True)),
             ],
             optional_keys=False,
         )),
        ("state_grouping", "double", True,
         Dictionary(
             title=_("Service Status Grouping"),
             columns=2,
             elements=[
                 ("warn",
                  DropdownChoice(
                      title=_("Treat Warning as"),
                      choices=[
                          ("ok", _("OK")),
                          ("warn", _("WARN")),
                          ("crit", _("CRIT")),
                          ("unknown", _("UNKNOWN")),
                      ],
                      default_value="warn",
                  )),
                 ("unknown",
                  DropdownChoice(
                      title=_("Treat Unknown/Unreachable as"),
                      choices=[
                          ("ok", _("OK")),
                          ("warn", _("WARN")),
                          ("crit", _("CRIT")),
                          ("unknown", _("UNKNOWN")),
                      ],
                      default_value="unknown",
                  )),
                 ("host_down",
                  DropdownChoice(
                      title=_("Treat Host Down as"),
                      choices=[
                          ("ok", _("OK")),
                          ("warn", _("WARN")),
                          ("crit", _("CRIT")),
                          ("unknown", _("UNKNOWN")),
                          ("host_down", _("Host Down")),
                      ],
                      default_value="host_down",
                  )),
             ],
             optional_keys=False,
         )),

        # Filter rows according to actual availability
        ("av_filter_outages", "double", True,
         Dictionary(
             title=_("Only show objects with outages"),
             columns=2,
             elements=[
                 ("warn",
                  Percentage(title=_("Show only rows with WARN of at least"), default_value=0.0)),
                 ("crit",
                  Percentage(title=_("Show only rows with CRIT of at least"), default_value=0.0)),
                 ("non-ok",
                  Percentage(title=_("Show only rows with non-OK of at least"), default_value=0.0)),
             ],
             optional_keys=False,
         )),

        # Optionally group some states together
        (
            "host_state_grouping",
            "single",
            True,
            Dictionary(
                title=_("Host Status Grouping"),
                columns=2,
                elements=[
                    (
                        "unreach",
                        DropdownChoice(
                            # TOOD: aligned
                            title=_("Treat Unreachable as"),
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
            )),

        # How to deal with the service periods
        ("service_period", "single", True,
         DropdownChoice(
             title=_("Service Time"),
             choices=[
                 ("honor", _("Base report only on service times")),
                 ("ignore", _("Include both service and non-service times")),
                 ("exclude", _("Base report only on non-service times")),
             ],
             default_value="honor",
         )),

        # How to deal with times out of the notification period
        ("notification_period", "single", True,
         DropdownChoice(
             title=_("Notification Period"),
             choices=[
                 ("honor", _("Distinguish times in and out of notification period")),
                 ("exclude", _("Exclude times out of notification period")),
                 ("ignore", _("Ignore notification period")),
             ],
             default_value="ignore",
         )),

        # Short time intervals
        ("short_intervals", "single", True,
         Integer(
             title=_("Short Time Intervals"),
             label=_("Ignore intervals shorter or equal"),
             minvalue=0,
             unit=_("sec"),
             default_value=0,
         )),

        # Merging
        ("dont_merge", "single", True,
         Checkbox(
             title=_("Phase Merging"),
             label=_("Do not merge consecutive phases with equal state"),
         )),
        ("timelimit", "single", False,
         Age(
             title=_("Query Time Limit"),
             help=_("Limit the execution time of the query, in order to "
                    "avoid a hanging system."),
             default_value=30,
         )),
        ("logrow_limit", "single", True,
         Integer(
             title=_("Limit processed data"),
             help=_("The availability is computed by processing entries from a data table "
                    "of historic events and state phases. In order to avoid a hanging system "
                    "in cases where your time range and filtering would accept a vast amount "
                    "of data entries, the number of processed entries is limited. You can raise "
                    "this limit here if you really need to process a huge amount of data. Set this "
                    "to zero in order to disable the limit."),
             label=_("Process at most"),
             unit=_("status entries"),
             minvalue=0,
             default_value=5000,
             size=6,
         )),
    ]


# Creates a function for rendering time values according to
# the avoptions of the report.
def render_number_function(timeformat: str) -> Callable[[AVTimeStamp, int], str]:
    if timeformat.startswith("percentage_"):

        def render_number(n, d):
            if not d:
                return _("n/a")
            return ("%." + timeformat[11:] + "f%%") % (float(n) / float(d) * 100.0)
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

    return render_number


def prepare_avo_timeformats(timeformat: str) -> AVTimeFormats:
    this_timeformat = [("percentage_2", render_number_function("percentage_2"))]
    if isinstance(timeformat, (list, tuple)):
        if timeformat[0] == "both":
            this_timeformat = [(x, render_number_function(x)) for x in timeformat[1:]]
        elif timeformat[0] == "perc":
            this_timeformat = [(timeformat[1], render_number_function(timeformat[1]))]
        elif timeformat[0] == "time":
            this_timeformat = [(timeformat[2], render_number_function(timeformat[2]))]
    elif timeformat.startswith("percentage_") or \
         timeformat in [ "seconds", "minutes", "hours", "hhmmss" ]:
        # Old style
        this_timeformat = [(timeformat, render_number_function(timeformat))]
    return this_timeformat


def get_default_avoptions() -> AVOptions:
    return {
        "range": ((time.time() - 86400, time.time()), ""),
        "rangespec": "d0",
        "labelling": [],
        "av_levels": None,
        "av_filter_outages": {
            "warn": 0.0,
            "crit": 0.0,
            "non-ok": 0.0
        },
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


def get_outage_statistic_options(avoptions):
    # Outage options are stored with keys matching service states (like "ok" and "crit").
    # For hosts we use the same checkbox but mean "up" and "down". We simply add these states
    # to the list of selected states.
    aggrs, states = avoptions.get("outage_statistics", ([], []))
    fixed_states = states[:]
    for service_state, host_state in [("ok", "up"), ("crit", "down"), ("unknown", "unreach")]:
        if service_state in fixed_states:
            fixed_states.append(host_state)
    return aggrs, fixed_states


#.
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
def get_availability_rawdata(what, context, filterheaders, only_sites, av_object, include_output,
                             include_long_output, avoptions):
    if what == "bi":
        return get_bi_availability_rawdata(filterheaders, only_sites, av_object, include_output,
                                           avoptions)

    time_range: AVTimeRange = avoptions["range"][0]

    av_filter = "Filter: time >= %d\nFilter: time < %d\n" % time_range
    if av_object:
        tl_site, tl_host, tl_service = av_object
        av_filter += "Filter: host_name = %s\nFilter: service_description = %s\n" % (tl_host,
                                                                                     tl_service)
        only_sites = [tl_site]
    elif what == "service":
        av_filter += "Filter: service_description !=\n"
    else:
        av_filter += "Filter: service_description =\n"

    query = "GET statehist\n" + av_filter
    query += "Timelimit: %d\n" % avoptions["timelimit"]

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
    if "use_display_name" in avoptions["labelling"]:
        columns.append("service_display_name")
    if "show_alias" in avoptions["labelling"]:
        columns.append("host_alias")

    # If we group by host/service group then make sure that that information is available
    if avoptions["grouping"] not in [None, "host"]:
        columns.append(avoptions["grouping"])

    query += "Columns: %s\n" % " ".join(columns)
    query += filterheaders
    logrow_limit = avoptions["logrow_limit"]

    with sites.only_sites(only_sites), sites.prepend_site(), sites.set_limit(logrow_limit or None):
        data = sites.live().query(query)
    columns = ["site"] + columns
    spans: List[AVSpan] = [dict(zip(columns, span)) for span in data]

    # When a group filter is set, only care about these groups in the group fields
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

    return spans_by_object(spans), exceeded_log_row_limit


def filter_groups_of_entries(context, avoptions, spans):
    group_by = avoptions["grouping"]

    only_groups = set()
    # TODO: This is a dirty hack. The logic of the filters needs to be moved to the filters.
    # They need to be able to filter the list of all groups.
    # TODO: Negated filters are not handled here. :(
    if group_by == "service_groups":
        if "servicegroups" not in context and "optservicegroup" not in context:
            return

        # Extract from context:
        # 'servicegroups': {'servicegroups': 'cpu|disk', 'neg_servicegroups': 'off'},
        # 'optservicegroup': {'optservice_group': '', 'neg_optservice_group': 'off'},
        negated = context.get("servicegroups", {}).get("neg_servicegroups") == "on"
        if negated:
            return

        only_groups.update(
            [e for e in context.get("servicegroups", {}).get("servicegroups", "").split("|") if e])

        negated = context.get("optservicegroup", {}).get("neg_optservice_group") == "on"
        if negated:
            return

        group_name = context.get("optservicegroup", {}).get("optservice_group")
        if group_name and not negated:
            only_groups.add(group_name)

    elif group_by == "host_groups":
        if "hostgroups" not in context and "opthostgroup" not in context:
            return

        negated = context.get("hostgroups", {}).get("neg_hostgroups") == "on"
        if negated:
            return

        only_groups.update(
            [e for e in context.get("hostgroups", {}).get("hostgroups", "").split("|") if e])

        negated = context.get("opthostgroup", {}).get("neg_opthost_group") == "on"
        if negated:
            return

        group_name = context.get("opthostgroup", {}).get("opthost_group")
        if group_name and not negated:
            only_groups.add(group_name)

    else:
        raise NotImplementedError()

    for span in spans:
        filtered_groups = list(set(span[group_by]).intersection(only_groups))
        span[group_by] = filtered_groups


# Sort the raw spans into a tree of dicts, so that we
# have easy access to the timeline of each object
def spans_by_object(spans: List[AVSpan]) -> AVRawData:
    # Sort by site/host and service, while keeping native order
    av_rawdata: AVRawData = {}
    for span in spans:
        site_host = span["site"], span["host_name"]
        service = span["service_description"]
        av_rawdata.setdefault(site_host, {})
        av_rawdata[site_host].setdefault(service, []).append(span)

    return av_rawdata


# Compute an availability table. what is one of "bi", "host", "service".
def compute_availability(what: AVObjectType, av_rawdata: AVRawData, avoptions: AVOptions) -> AVData:
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
                    (span["in_service_period"] and avoptions["service_period"] != "honor") or
                    (not span["in_service_period"] and avoptions["service_period"] == "honor")):
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
                elif span["in_notification_period"] == 0 and avoptions[
                        "notification_period"] == "exclude":
                    consider = False

                elif span["in_notification_period"] == 0 and avoptions[
                        "notification_period"] == "honor":
                    s = "outof_notification_period"

                elif (span["in_downtime"] or span["in_host_downtime"]
                     ) and not (avoptions["downtimes"]["exclude_ok"] and
                                state == 0) and not avoptions["downtimes"]["include"] == "ignore":
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
                melt_short_intervals(timeline_rows, avoptions["short_intervals"],
                                     avoptions["dont_merge"])

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
                        statistics[s] = (entry[0] + 1, min(entry[1],
                                                           duration), max(entry[2], duration))
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
    filtered_table = []  # Type: AVData
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
            cycles: List[AVAnnotationKey] = []
            cycles.append((site, host_name, service_description or None))
            if what == "service":
                cycles.insert(0, (site, host_name, None))

            for anno_key in cycles:
                if anno_key in annotations:
                    new_entries[service_description] = \
                          reclassify_history_by_annotations(history, annotations[anno_key])
                    history = new_entries[service_description]
                else:
                    new_entries[service_description] = history

    return reclassified_rawdata


ReclassifyConfig = NamedTuple("ReclassifyConfig", [
    ("downtime", _Optional[Any]),
    ("host_state", _Optional[Any]),
    ("service_state", _Optional[Any]),
])


def reclassify_history_by_annotations(history: List[AVSpan],
                                      annotation_entries: List[AVAnnotationEntry]) -> List[AVSpan]:
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


def reclassify_history_by_annotation(history: List[AVSpan], annotation: AVAnnotationEntry,
                                     new_config: ReclassifyConfig) -> List[AVSpan]:
    new_history: List[AVSpan] = []
    for history_entry in history:
        new_history += reclassify_times_by_annotation(history_entry, annotation, new_config)

    return new_history


def reclassify_times_by_annotation(history_entry, annotation, new_config):
    new_history = []
    if annotation["from"] < history_entry["until"] and annotation["until"] > history_entry["from"]:
        for is_in, p_from, p_until in [
            (False, history_entry["from"], max(history_entry["from"], annotation["from"])),
            (True, max(history_entry["from"],
                       annotation["from"]), min(history_entry["until"], annotation["until"])),
            (False, min(history_entry["until"], annotation["until"]), history_entry["until"]),
        ]:
            if p_from < p_until:
                new_entry = history_entry.copy()
                new_entry["from"] = p_from
                new_entry["until"] = p_until
                new_entry["duration"] = p_until - p_from
                if is_in:
                    reclassify_config_by_annotation(history_entry, annotation, new_entry,
                                                    new_config)

                new_history.append(new_entry)
    else:
        new_history.append(history_entry)

    return new_history


def reclassify_config_by_annotation(history_entry, annotation, new_entry, new_config):
    if new_config.downtime:
        new_entry["in_downtime"] = 1 if annotation['downtime'] else 0
        # If the annotation removes a downtime from the services, but
        # the actual reason for the service being in downtime is a host
        # downtime, then we must cancel the host downtime (also), or else
        # that would override the unset service downtime.
        if history_entry.get("in_host_downtime") \
            and annotation["downtime"] is False:
            new_entry["in_host_downtime"] = 0
    if new_config.host_state is not None:
        new_host_state = annotation.get('host_state', history_entry.get("host_state"))
        new_entry["state"] = new_host_state
        new_entry["host_down"] = 1 if new_host_state else 0
    if new_config.service_state is not None:
        new_entry["state"] = annotation.get('service_state', history_entry.get("state"))

    return new_entry


def pass_availability_filter(row, avoptions):
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
def compute_availability_groups(what: AVObjectType, av_data: AVData,
                                avoptions: AVOptions) -> AVGroups:
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

    titled_groups: List[_Tuple[str, AVGroupKey]] = []
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


def object_title(what, av_entry):
    if what == "host":
        return av_entry["host"]
    # service and BI
    return av_entry["host"] + " / " + av_entry["service"]


# Merge consecutive rows with same state
def merge_timeline(entries):
    n = 1
    while n < len(entries):
        if (entries[n][1] == entries[n - 1][1] and
                entries[n][0]["from"] == entries[n - 1][0]["until"]):
            entries[n - 1][0]["duration"] += entries[n][0]["duration"]
            entries[n - 1][0]["until"] = entries[n][0]["until"]
            del entries[n]
        else:
            n += 1


def melt_short_intervals(entries, duration, dont_merge):
    n = 1
    need_merge = False
    while n < len(entries) - 1:
        if entries[n][0]["duration"] <= duration and \
            (entries[n-1][0]["until"] == entries[n][0]["from"] or entries[n][0]["until"] == entries[n+1][0]["from"]) and \
            entries[n-1][1] == entries[n+1][1]:
            entries[n] = (entries[n][0], entries[n - 1][1])
            need_merge = True
        n += 1

    # Due to melting, we need to merge again
    if need_merge and not dont_merge:
        merge_timeline(entries)
        melt_short_intervals(entries, duration, dont_merge)


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


def update_annotations(site_host_svc: AVAnnotationKey, annotation: AVAnnotationEntry,
                       replace_existing: _Optional[AVAnnotationEntry]) -> None:
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


def find_annotation(annotations: AVAnnotations, site_host_svc: AVAnnotationKey,
                    host_state: _Optional[str], service_state: _Optional[str],
                    fromtime: AVTimeStamp, untiltime: AVTimeStamp) -> _Optional[AVAnnotationEntry]:
    entries = annotations.get(site_host_svc)
    if not entries:
        return None
    for annotation in entries:
        if annotation["from"] == fromtime and annotation["until"] == untiltime:
            return annotation
    return None


def delete_annotation(annotations: AVAnnotations, site_host_svc: AVAnnotationKey,
                      host_state: _Optional[str], service_state: _Optional[str],
                      fromtime: AVTimeStamp, untiltime: AVTimeStamp) -> None:
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


#.
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
#    "title" : "Hostgroup foobar",
#    "headers" : [ "OK, "CRIT", "Downtime" ],
#    "rows" : [ ... ],
#    "summary" : [ ("84.50%", "crit"), ("15.50%", "crit"), ("0.00%", "p"),  ("0.00%", "p") ],
# }
# row ist ein dict: {
#    "cells" : [ ("84.50%", "crit"), ("15.50%", "crit"), ("0.00%", "p"),  ("0.00%", "p") ],
#    "urls" : { "timeline": "view.py..." },
#    "object" : ( "Host123", "Foobar" ),
# }
def layout_availability_table(what: AVObjectType, group_title: _Optional[str],
                              availability_table: AVData, avoptions: AVOptions) -> AVLayoutTable:
    time_range: AVTimeRange = avoptions["range"][0]
    from_time, until_time = time_range
    total_duration = until_time - from_time
    timeformats = prepare_avo_timeformats(avoptions["timeformat"])
    show_timeline = avoptions["show_timeline"]
    labelling = avoptions["labelling"]
    av_levels = avoptions["av_levels"]
    show_summary = avoptions.get("summary")
    summary: Dict[str, float] = {}
    summary_counts: Dict[str, int] = {}
    unmonitored_objects = 0
    av_table: AVLayoutTable = {
        "title": group_title,
        "rows": [],
    }

    availability_columns = AvailabilityColumns()
    statistics_headers = {
        "min": _("Shortest"),
        "max": _("Longest"),
        "avg": _("Average"),
        "cnt": _("Count"),
    }

    # Titles for the columns that specify the object
    titles = []
    if what == "bi":
        titles.append(_("Aggregate"))
    else:
        # in service availability we can only omit the host. In the
        # host availability this is only possible if the alias is
        # being displayed, Otherwise the table wouldn't make sense
        # and the pdf renderer would crash
        if "omit_host" not in labelling or\
                (what == "host" and "show_alias" not in labelling):
            titles.append(_("Host"))
        if "show_alias" in labelling:
            titles.append(_("Alias"))

        if what != "host":
            titles.append(_("Service"))

    av_table["object_titles"] = titles

    # Headers for availability cells
    av_table["cell_titles"] = []
    os_aggrs, os_states = get_outage_statistic_options(avoptions)
    for timeformat, render_number in timeformats:
        for sid, css, sname, help_txt in availability_columns[what]:
            ssid = "%s-%s" % (sid, timeformat)
            if not cell_active(sid, avoptions):
                continue
            if avoptions["av_mode"]:
                sname = _("Avail.")

            av_table["cell_titles"].append((sname, help_txt))

            if sid in os_states:
                for aggr in os_aggrs:
                    title = statistics_headers[aggr]
                    av_table["cell_titles"].append((title, None))

    # Actual rows
    for entry in availability_table:
        site = entry["site"]
        host = entry["host"]
        service = entry["service"]

        row: AVLayoutTableRow = {}
        av_table["rows"].append(row)

        # Iconbuttons with URLs
        urls = []
        if "omit_buttons" not in labelling:
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
                    ("history", _("Event History"), history_url_of((site, host, service),
                                                                   time_range)))
        row["urls"] = urls
        row["object"] = get_object_cells(what, entry, labelling)

        # Inline timeline
        if show_timeline:
            row["timeline"] = layout_timeline(what,
                                              entry["timeline"],
                                              entry["considered_duration"],
                                              avoptions,
                                              style="inline")

        # Actuall cells with availability data
        cells: AVRowCells = []
        row["cells"] = cells

        for timeformat, render_number in timeformats:
            for sid, css, sname, help_txt in availability_columns[what]:
                ssid = "%s-%s" % (sid, timeformat)
                if not cell_active(sid, avoptions):
                    continue

                number = entry["states"].get(sid, 0)
                if not number:
                    css = "unused"

                elif show_summary:
                    summary.setdefault(ssid, 0.0)
                    if timeformat.startswith("percentage"):
                        if entry["considered_duration"] > 0:
                            summary[ssid] += float(number) / entry["considered_duration"]
                    else:
                        summary[ssid] += number

                # Apply visual availability levels (render OK in yellow/red, if too low)
                if number and av_levels and sid in ["ok", "up"]:
                    css = "state%d" % check_av_levels(number, av_levels,
                                                      entry["considered_duration"])

                css = css + " state narrow number"
                cells.append((render_number(number, entry["considered_duration"]), css))

                # Statistics?
                x_cnt, x_min, x_max = entry["statistics"].get(sid, (None, None, None))
                os_aggrs, os_states = get_outage_statistic_options(avoptions)
                if sid in os_states:
                    for aggr in os_aggrs:
                        if x_cnt is not None:
                            if aggr == "avg":
                                r = render_number(
                                    int(number / x_cnt),
                                    entry["considered_duration"])  # fixed: true-division
                            elif aggr == "min":
                                r = render_number(x_min, entry["considered_duration"])
                            elif aggr == "max":
                                r = render_number(x_max, entry["considered_duration"])
                            else:
                                r = str(x_cnt)
                                summary_counts.setdefault(ssid, 0)
                                summary_counts[ssid] += x_cnt
                            cells.append((r, css))
                        else:
                            cells.append((u"", ""))

            # If timeline == [] and states == {} then this objects has complete unmonitored state
            if entry["timeline"] == [] and entry["states"] == {}:
                unmonitored_objects += 1

    # Summary line. It has the same format as each entry in cells
    # We ignore unmonitored objects
    len_availability_table = len(availability_table) - unmonitored_objects
    if show_summary and len_availability_table > 0:
        summary_cells: AVRowCells = []

        for timeformat, render_number in timeformats:
            for sid, css, sname, help_txt in availability_columns[what]:
                ssid = "%s-%s" % (sid, timeformat)
                if not cell_active(sid, avoptions):
                    continue

                number = summary.get(ssid, 0)
                if show_summary == "average" or timeformat.startswith("percentage"):
                    number /= len_availability_table
                    if timeformat.startswith("percentage"):
                        number *= total_duration

                if not number:
                    css = "unused"

                if number and av_levels and sid in ["ok", "up"]:
                    css = "state%d" % check_av_levels(number, av_levels, total_duration)

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


def get_object_cells(what: AVObjectType, av_entry: AVEntry, labelling: List[str]) -> AVObjectCells:
    host = av_entry["host"]
    service = av_entry["service"]

    objectcells: AVObjectCells = []
    if what == "bi":
        bi_url = "view.py?" + html.urlencode_vars([("view_name", "aggr_single"),
                                                   ("aggr_group", host), ("aggr_name", service)])
        objectcells.append((service, bi_url))
        return objectcells

    host_url = "view.py?" + html.urlencode_vars([("view_name", "hoststatus"),
                                                 ("site", av_entry["site"]), ("host", host)])
    if "omit_host" not in labelling or\
            (what == "host" and "show_alias" not in labelling):
        objectcells.append((host, host_url))

    if "show_alias" in labelling:
        objectcells.append((av_entry["alias"], host_url))

    if what == "service":
        if "use_display_name" in labelling:
            service_name = av_entry["display_name"]
        else:
            service_name = service
        service_url = "view.py?" + html.urlencode_vars([("view_name", "service"),
                                                        ("site", av_entry["site"]), ("host", host),
                                                        ("service", service)])
        objectcells.append((service_name, service_url))

    return objectcells


# Compute layout of timeline independent of the output device (HTML, PDF, whatever)...
# style is either "inline" or "standalone"
# Output format:
# {
#    "spans" : [ spans... ],
#    "legend" : [ legendentries... ],
# }
def layout_timeline(what: AVObjectType, timeline_rows: AVTimelineRows, considered_duration: int,
                    avoptions: AVOptions, style: AVTimelineStyle) -> AVLayoutTimeline:
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
    spans: List[AVTimelineSpan] = []
    table: List[AVLayoutTimelineRow] = []
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

    def chaos_period(chaos_begin: AVTimeStamp, chaos_end: AVTimeStamp, chaos_count: int,
                     chaos_width: int) -> AVTimelineSpan:
        title = _("%d chaotic state changes from %s until %s (%s)") % (
            chaos_count, render_date(chaos_begin), render_date(chaos_end),
            apply_render_number_functions(chaos_end - chaos_begin, considered_duration))
        return (None, title, chaos_width, "chaos")

    current_time = from_time
    for row_nr, (row, state_id) in enumerate(timeline_rows):
        this_from_time = row["from"]
        this_until_time = row["until"]
        if this_from_time > current_time:  # GAP
            spans.append((
                None,
                "",
                100.0 * (this_from_time - current_time) / total_duration,
                "unmonitored",
            ))
        current_time = this_until_time

        from_text = render_date(this_from_time)
        until_text = render_date(this_until_time)
        duration_text = apply_render_number_functions(row["duration"], considered_duration)

        for sid, css, sname, help_txt in availability_columns[what]:
            if sid != state_id:
                continue

            title = _("From %s until %s (%s) %s") % (from_text, until_text, duration_text,
                                                     help_txt and help_txt or sname)
            if "log_output" in row and row["log_output"]:
                title += " - " + row["log_output"]
            width = rest_percentage * row["duration"] / total_duration  # fixed: true-division

            # Information for table of detailed events
            if style == "standalone":
                table.append({
                    "state": state_id,
                    "css": css,
                    "state_name": sname,
                    "from": row["from"],
                    "until": row["until"],
                    "from_text": from_text,
                    "until_text": until_text,
                    "duration_text": duration_text,
                })
                if "log_output" in row and row["log_output"]:
                    table[-1]["log_output"] = row["log_output"]
                if "long_log_output" in row and row["long_log_output"]:
                    table[-1]["long_log_output"] = row["long_log_output"]

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

    if chaos_count > 1 and chaos_begin and chaos_end:
        spans.append(chaos_period(chaos_begin, chaos_end, chaos_count, chaos_width))

    if style == "inline":
        timeline_layout["time_choords"] = layout_timeline_choords(time_range)

    return timeline_layout


def layout_timeline_choords(time_range):
    from_time, until_time = time_range
    duration = until_time - from_time

    # Now comes the difficult part: decide automatically, whether to use
    # hours, days, weeks or months. Days and weeks needs to take local time
    # into account. Months are irregular.
    hours = duration / 3600.0
    if hours < 12:
        scale = "hours"
        render = _render_hour
    elif hours < 24:
        scale = "2hours"
        render = _render_2hours
    elif hours < 48:
        scale = "6hours"
        render = _render_6hours
    elif hours < 24 * 14:
        scale = "days"
        render = _render_days
    elif hours < 24 * 60:
        scale = "weeks"
        render = _render_weeks
    else:
        scale = "months"
        render = _render_months

    broken = list(time.localtime(from_time))
    while True:
        # TODO: this modifies `broken` in place. Stopit.
        next_choord = find_next_choord(broken, scale)
        if next_choord >= until_time:
            break
        position = (next_choord - from_time) / float(duration)  # ranges from 0.0 to 1.0
        yield position, render(_structify(broken))


# TODO: refactor the above and get rid of this!
def _structify(broken: List[int]) -> time.struct_time:
    return time.struct_time(
        (int(broken[0]), int(broken[1]), int(broken[2]), int(broken[3]), int(broken[4]),
         int(broken[5]), int(broken[6]), int(broken[7]), int(broken[8])))


def _render_hour(tst: time.struct_time) -> str:
    return time.strftime("%H:%M", tst)


def _render_2hours(tst: time.struct_time) -> str:
    return defines.weekday_name(tst.tm_wday) + time.strftime(" %H:%M", tst)


def _render_6hours(tst: time.struct_time) -> str:
    return defines.weekday_name(tst.tm_wday) + time.strftime(" %H:%M", tst)


def _render_days(tst: time.struct_time) -> str:
    return defines.weekday_name(tst.tm_wday) + time.strftime(", %d.%m. 00:00", tst)


def _render_weeks(tst: time.struct_time) -> str:
    return defines.weekday_name(tst.tm_wday) + time.strftime(", %d.%m.", tst)


def _render_months(tst: time.struct_time) -> str:
    return "%s %d" % (defines.month_name(tst.tm_mon - 1), tst.tm_year)


def find_next_choord(broken: List[int], scale):
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
    broken[4:6] = [0, 0]  # always set min/sec to 00:00
    old_dst = broken[8]

    if scale == "hours":
        epoch = time.mktime(_structify(broken))
        epoch += 3600
        broken[:] = list(time.localtime(epoch))

    elif scale == "2hours":
        broken[3] = int(broken[3] / 2) * 2
        epoch = time.mktime(_structify(broken))
        epoch += 2 * 3600
        broken[:] = list(time.localtime(epoch))

    elif scale == "6hours":
        broken[3] = int(broken[3] / 6) * 6
        epoch = time.mktime(_structify(broken))
        epoch += 6 * 3600
        broken[:] = list(time.localtime(epoch))

    elif scale == "days":
        broken[3] = 0
        epoch = time.mktime(_structify(broken))
        epoch += 24 * 3600
        broken[:] = list(time.localtime(epoch))

    elif scale == "weeks":
        broken[3] = 0
        at_00 = int(time.mktime(_structify(broken)))
        at_monday = at_00 - 86400 * broken[6]
        epoch = at_monday + 7 * 86400
        broken[:] = list(time.localtime(epoch))

    else:  # scale == "months":
        broken[3] = 0
        broken[2] = 0
        broken[1] += 1
        if broken[1] > 12:
            broken[1] = 1
            broken[0] += 1
        epoch = time.mktime(_structify(broken))

    dst = broken[8]
    if old_dst == 1 and dst == 0:
        epoch += 3600
    elif old_dst == 0 and dst == 1:
        epoch -= 3600

    return epoch


#.
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
BIAggregationTree = Dict[str, Any]
BIAggregationTitle = str
BITreeState = Any


def get_bi_availability_rawdata(filterheaders, only_sites, av_object, include_output, avoptions):
    raise Exception("Not implemented yet. Sorry.")


def get_timeline_containers(
        aggr_rows: Rows, avoptions: AVOptions, timewarp: _Optional[AVTimeStamp],
        livestatus_limit: _Optional[int]) -> '_Tuple[List[TimelineContainer], int]':
    time_range: AVTimeRange = avoptions["range"][0]
    phases_list, timeline_containers, fetched_rows = get_bi_leaf_history(
        aggr_rows, time_range, livestatus_limit)
    return compute_bi_timelines(timeline_containers, time_range, timewarp,
                                phases_list), fetched_rows


# Not a real class, more a struct
class TimelineContainer:
    def __init__(self, aggr_row):
        self._aggr_row = aggr_row

        # PUBLIC accessible data
        self.aggr_compiled_aggregation = self._aggr_row["aggr_compiled_aggregation"]
        self.aggr_compiled_branch = self._aggr_row["aggr_compiled_branch"]
        self.aggr_tree: BIAggregationTree = self._aggr_row["aggr_tree"]
        self.aggr_group: BIAggregationGroupTitle = self._aggr_row["aggr_group"]

        # Data fetched from livestatus query
        self.host_service_info: Set[_Tuple[HostName, ServiceName]] = set()

        # Computed data
        self.timeline = []
        self.states: AVBITimelineStates = {}
        self.node_compute_result: _Optional[NodeComputeResult] = None
        self.timewarp_state: _Optional[BITreeState] = None
        self.tree_time: _Optional[AVTimeStamp] = None


def get_bi_leaf_history(
        aggr_rows: Rows, time_range: AVTimeRange,
        livestatus_limit: _Optional[int]) -> _Tuple[AVBIPhases, List[TimelineContainer], int]:
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

    query = "GET statehist\n" + \
            "Columns: " + " ".join(columns) + "\n" +\
            "Filter: time >= %d\nFilter: time < %d\n" % time_range

    # Create a specific filter. We really only want the services and hosts
    # of the aggregation in question. That prevents status changes
    # irrelevant services from introducing new phases.
    by_host: Dict[HostName, Set[ServiceName]] = {}
    timeline_containers: List[TimelineContainer] = []
    for row in aggr_rows:
        timeline_container = TimelineContainer(row)

        for site, host, service in timeline_container.aggr_compiled_branch.required_elements():
            this_service = service or ""
            by_host.setdefault(host, set()).add(this_service)
            timeline_container.host_service_info.add((host, this_service))
            timeline_container.host_service_info.add((host, ""))

        timeline_containers.append(timeline_container)

    for host, services in by_host.items():
        query += "Filter: host_name = %s\n" % host
        query += lq_logic("Filter: service_description = ", list(services), "Or")
        query += "And: 2\n"
    if len(hosts) != 1:
        query += "Or: %d\n" % len(hosts)

    with sites.output_format(LivestatusOutputFormat.JSON), sites.only_sites(
            list(only_sites)), sites.prepend_site(), sites.set_limit(livestatus_limit):
        data = sites.live().query(query)

    if not data:
        return [], [], 0

    columns = ["site"] + columns
    rows = [dict(zip(columns, row)) for row in data]

    # Reclassify base data due to annotations
    rows = reclassify_bi_rows(rows)

    # Now comes the tricky part: recompute the state of the aggregate
    # for each step in the state history and construct a timeline from
    # it. As a first step we need the start state for each of the
    # hosts/services. They will always be the first consecute rows
    # in the statehist table

    # First partition the rows into sequences with equal start time
    phases: Dict[int, Dict[_Tuple[HostName, ServiceName], Row]] = {}
    for row in rows:
        phases.setdefault(row["from"], {})[(row["host_name"], row["service_description"])] = row

    # Convert phases to sorted list
    sorted_times = sorted(phases.keys())
    phases_list: AVBIPhases = []

    for from_time in sorted_times:
        phases_list.append((from_time, phases[from_time]))

    return phases_list, timeline_containers, len(rows)


def compute_bi_timelines(timeline_containers: List[TimelineContainer], time_range: AVTimeRange,
                         timewarp: _Optional[AVTimeStamp],
                         phases_list: AVBIPhases) -> List[TimelineContainer]:
    if not timeline_containers:
        return timeline_containers

    def update_states(states: AVBITimelineStates, use_entries: Set[_Tuple[HostName, ServiceName]],
                      phase_entries: AVBIPhaseData) -> None:
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
        len(phases_list), len(timeline_containers))
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
                timeline_container.timeline.append(
                    create_bi_timeline_entry(timeline_container.aggr_tree,
                                             timeline_container.aggr_group,
                                             timeline_container.tree_time, from_time,
                                             timeline_container.node_compute_result))

            timeline_container.node_compute_result = next_node_compute_result
            timeline_container.tree_time = from_time
            if timewarp == timeline_container.tree_time:
                timeline_container.timewarp_state = _get_timewarp_state(
                    result_bundle, timeline_container)

    # Create a final timeline entry to the end of the query interval
    for timeline_container in list(timeline_containers):
        if timeline_container.node_compute_result is None:
            # This can only happen if the livestatus row limit was reached
            # The data is incomplete or entirely missing
            timeline_containers.remove(timeline_container)
            continue

        timeline_container.timeline.append(
            create_bi_timeline_entry(timeline_container.aggr_tree, timeline_container.aggr_group,
                                     timeline_container.tree_time, time_range[1],
                                     timeline_container.node_compute_result))

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
        node_compute_result_bundle)["aggr_treestate"]


def create_bi_timeline_entry(tree, aggr_group, from_time, until_time, node_compute_result):
    return {
        "state": node_compute_result.state,
        "log_output": node_compute_result.output,
        "from": from_time,
        "until": until_time,
        "site": "",
        "host_name": aggr_group,
        "service_description": tree['title'],
        "in_notification_period": 1,
        "in_service_period": node_compute_result.in_service_period,
        "in_downtime": node_compute_result.downtime_state > 0,
        "in_host_downtime": 0,
        "host_down": 0,
        "is_flapping": 0,
        "duration": until_time - from_time,
    }


def _compute_node_result_bundle(timeline_container, bi_manager: BIManager) -> NodeResultBundle:
    # Convert our status format into that needed by BI
    #
    status = timeline_container.states
    services_by_host: Dict[BIHostSpec, Dict[str, BIServiceWithFullState]] = {}
    hosts: Dict[BIHostSpec, AVBITimelineState] = {}
    for site_host_service, state_output in status.items():
        site_host: BIHostSpec = site_host_service[:2]
        service = site_host_service[2]
        state: _Optional[int] = state_output[0]

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
            NodeComputeResult(-1, 0, False, _("Not yet monitored"), True, {}, {}),
            None,
            [],
            None,
        )

    return results[0]


def _compute_status_info(
        hosts: Dict[BIHostSpec, AVBITimelineState],
        services_by_host: Dict[BIHostSpec, Dict[str, BIServiceWithFullState]]) -> BIStatusInfo:

    status_info: BIStatusInfo = {}

    for site_host, state_output in hosts.items():
        state: _Optional[int] = state_output[0]

        if state == -1:
            state = None  # Means: consider this object as missing

        status_info[site_host] = BIHostStatusInfoRow(
            state,  # state
            True,  # has_been_checked
            state,  # host hard state
            state_output[1],  # plugin output
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


#.
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
def cell_active(sid, avoptions):
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
def check_av_levels(ok_seconds, av_levels, considered_duration):
    if considered_duration == 0:
        return 0

    perc = 100 * float(ok_seconds) / float(considered_duration)
    warn, crit = av_levels
    if perc < crit:
        return 2
    if perc < warn:
        return 1
    return 0


def get_av_groups(availability_table: AVData, avoptions: AVOptions) -> Set[AVGroupKey]:
    all_group_ids: Set[AVGroupKey] = set()
    for entry in availability_table:
        all_group_ids.update(entry["groups"])
        if len(entry["groups"]) == 0:
            all_group_ids.add(None)  # None denotes ungrouped objects
    return all_group_ids


# Sort according to host and service. First after site, then
# host (natural sort), then service
def key_av_entry(a):
    # This local import currently needed
    import cmk.gui.plugins.views as views
    return utils.key_num_split(a["service"]), views.cmp_service_name_equiv(
        a["service"]), utils.key_num_split(a["host"]), utils.key_num_split(a["site"])


def history_url_of(av_object, time_range):
    site, host, service = av_object
    from_time, until_time = time_range

    history_url_vars = [
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

    return "view.py?" + html.urlencode_vars(history_url_vars)
