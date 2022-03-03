#!/usr/bin/env python3
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
# This file is part of Checkmk.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

from cmk.utils.oracle_constants import (
    oracle_io_sizes,
    oracle_io_types,
    oracle_iofiles,
    oracle_pga_fields,
    oracle_sga_fields,
    oracle_waitclasses,
)

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    HostRulespec,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
    RulespecGroupCheckParametersDiscovery,
)
from cmk.gui.valuespec import (
    CascadingDropdown,
    Dictionary,
    FixedValue,
    Float,
    Integer,
    ListOf,
    TextInput,
    Tuple,
)


def _valuespec_discovery_oracle_performance():
    return Dictionary(
        title=_("Service discovery: "),
        elements=[
            (
                "dbtime",
                FixedValue(
                    value=True,
                    title=_("Create separate Service for DB-Time"),
                    totext=_("Extracts DB-Time performance data into a separate service"),
                ),
            ),
            (
                "memory",
                FixedValue(
                    value=True,
                    title=_("Create separate Service for memory information"),
                    totext=_(
                        "Extracts SGA performance data into a separate service and additionally displays PGA performance data"
                    ),
                ),
            ),
            (
                "iostat_bytes",
                FixedValue(
                    value=True,
                    title=_("Create additional Service for IO Stats Bytes"),
                    totext=_(
                        "Creates a new service that displays information about disk I/O of database files. "
                        "This service displays the number of bytes read and written to database files."
                    ),
                ),
            ),
            (
                "iostat_ios",
                FixedValue(
                    value=True,
                    title=_("Create additional Service for IO Stats Requests"),
                    totext=_(
                        "Creates a new service that displays information about disk I/O of database files. "
                        "This service displays the number of single block read and write requests that are being made to database files."
                    ),
                ),
            ),
            (
                "waitclasses",
                FixedValue(
                    value=True,
                    title=_("Create additional Service for System Wait"),
                    totext=_(
                        "Display the time an oracle instance spents inside of the different wait classes."
                    ),
                ),
            ),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        name="oracle_performance_discovery",
        group=RulespecGroupCheckParametersDiscovery,
        match_type="dict",
        valuespec=_valuespec_discovery_oracle_performance,
        title=lambda: _("Oracle performance discovery"),
    )
)


def _parameter_valuespec_oracle_performance():
    def levels_tuple(Type, unit):
        return Tuple(
            orientation="float",
            show_titles=False,
            elements=[
                Type(label=_("Warning at"), unit=unit),
                Type(label=_("Critical at"), unit=unit),
            ],
        )

    # memory
    memory_choices: list = []
    for ga in oracle_sga_fields + oracle_pga_fields:
        memory_choices.append(
            (
                ga.metric,
                ga.name,
                levels_tuple(Integer, "bytes"),
            )
        )

    # iostat_bytes + iostat_ios
    iostat_bytes_choices: list = []
    iostat_ios_choices: list = []
    for iofile_name, iofile_id in oracle_iofiles:
        for size_code, size_text in oracle_io_sizes:
            for io_code, io_text, io_unit in oracle_io_types:
                target_array = iostat_bytes_choices if io_unit == "bytes/s" else iostat_ios_choices
                target_array.append(
                    (
                        "oracle_ios_f_%s_%s_%s" % (iofile_id, size_code, io_code),
                        " %s %s %s" % (iofile_name, size_text, io_text),
                        levels_tuple(Integer, io_unit),
                    )
                )

    # waitclasses
    waitclasses_choices: list = [
        (
            "oracle_wait_class_total",
            "Total waited",
            levels_tuple(Float, "1/s"),
        ),
        (
            "oracle_wait_class_total_fg",
            "Total waited (FG)",
            levels_tuple(Float, "1/s"),
        ),
    ]
    for waitclass in oracle_waitclasses:
        waitclasses_choices.append(
            (waitclass.metric, "%s wait class" % waitclass.name, levels_tuple(Float, "1/s"))
        )
        waitclasses_choices.append(
            (waitclass.metric_fg, "%s wait class (FG)" % waitclass.name, levels_tuple(Float, "1/s"))
        )

    return Dictionary(
        help=_("Here you can set levels for the ORACLE Performance metrics."),
        elements=[
            (
                "dbtime",
                ListOf(
                    valuespec=CascadingDropdown(
                        title=_("Field"),
                        orientation="horizontal",
                        choices=[
                            ("oracle_db_cpu", "DB CPU", levels_tuple(Float, "1/s")),
                            ("oracle_db_time", "DB Time", levels_tuple(Float, "1/s")),
                            ("oracle_db_wait_time", "DB Non-Idle Wait", levels_tuple(Float, "1/s")),
                        ],
                    ),
                    title=_("Levels for DB Time"),
                ),
            ),
            (
                "memory",
                ListOf(
                    valuespec=CascadingDropdown(
                        title=_("Field"),
                        orientation="horizontal",
                        choices=memory_choices,
                    ),
                    title=_("Levels for Memory"),
                ),
            ),
            (
                "iostat_bytes",
                ListOf(
                    valuespec=CascadingDropdown(
                        title=_("Field"),
                        orientation="horizontal",
                        choices=iostat_bytes_choices,
                    ),
                    title=_("Levels for IO Stats Bytes"),
                ),
            ),
            (
                "iostat_ios",
                ListOf(
                    valuespec=CascadingDropdown(
                        title=_("Field"),
                        orientation="horizontal",
                        choices=iostat_ios_choices,
                    ),
                    title=_("Levels for IO Stats Requests"),
                ),
            ),
            (
                "waitclasses",
                ListOf(
                    valuespec=CascadingDropdown(
                        title=_("Field"),
                        orientation="horizontal",
                        choices=waitclasses_choices,
                    ),
                    title=_("Levels for System Wait"),
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="oracle_performance",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextInput(title=_("Database SID"), size=12, allow_empty=False),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_oracle_performance,
        title=lambda: _("Oracle Performance"),
    )
)
