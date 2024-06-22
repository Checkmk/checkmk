#!/usr/bin/env python3
# Copyright (C) 2014 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

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
                    title=_("Create separate service for DB time"),
                    totext=_("Extracts DB time performance data into a separate service"),
                ),
            ),
            (
                "memory",
                FixedValue(
                    value=True,
                    title=_("Create separate service for memory information"),
                    totext=_(
                        "Extracts SGA performance data into a separate service and additionally displays PGA performance data"
                    ),
                ),
            ),
            (
                "iostat_bytes",
                FixedValue(
                    value=True,
                    title=_("Create additional service for IO stats bytes"),
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
                    title=_("Create additional service for IO stats requests"),
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
                    title=_("Create additional service for system wait"),
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
                        f"oracle_ios_f_{iofile_id}_{size_code}_{io_code}",
                        f" {iofile_name} {size_text} {io_text}",
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
        help=_("Here you can set levels for the Oracle performance metrics."),
        elements=[
            (
                "dbtime",
                ListOf(
                    valuespec=CascadingDropdown(
                        title=_("Field"),
                        orientation="horizontal",
                        choices=[
                            ("oracle_db_cpu", "DB CPU", levels_tuple(Float, "1/s")),
                            ("oracle_db_time", "DB time", levels_tuple(Float, "1/s")),
                            ("oracle_db_wait_time", "DB non-idle wait", levels_tuple(Float, "1/s")),
                        ],
                    ),
                    title=_("Levels for DB time"),
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
                    title=_("Levels for memory"),
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
                    title=_("Levels for IO stats bytes"),
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
                    title=_("Levels for IO stats requests"),
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
                    title=_("Levels for system wait"),
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
        title=lambda: _("Oracle performance"),
    )
)
