#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from collections.abc import Callable

import cmk.ccc.version as cmk_version
import cmk.utils.paths
from cmk.gui.exceptions import MKUserError
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.utils.urls import makeuri_contextless
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
)

from .type_defs import (
    AVObjectType,
    AVOptions,
    AVOptionValueSpecs,
    AVOutageStatistics,
    AVTimeFormats,
    AVTimeformatSpec,
    AVTimeStamp,
)


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

    if cmk_version.edition(cmk.utils.paths.omd_root) is not cmk_version.Edition.COMMUNITY:
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
                title=_("Format timestamps as"),
                choices=[
                    ("yyyy-mm-dd hh:mm:ss", _("YYYY-MM-DD HH:MM:SS")),
                    ("epoch", _("Unix timestamp (epoch)")),
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
                title=_("Service state grouping"),
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
                title=_("Host state grouping"),
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
    if isinstance(timeformat, list | tuple):
        if timeformat[0] == "both":
            this_timeformat = [
                (timeformat[1], render_number_function(timeformat[1])),
                (timeformat[2], render_number_function(timeformat[2])),
            ]
        elif timeformat[0] == "perc":
            this_timeformat = [(timeformat[1], render_number_function(timeformat[1]))]
        elif timeformat[0] == "time":
            this_timeformat = [(timeformat[2], render_number_function(timeformat[2]))]
    elif timeformat.startswith("percentage_") or timeformat in [
        "seconds",
        "minutes",
        "hours",
        "hhmmss",
    ]:
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
