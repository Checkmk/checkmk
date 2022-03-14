#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    Levels,
    rulespec_registry,
    RulespecGroupCheckParametersOperatingSystem,
)
from cmk.gui.valuespec import Age, Dictionary, DropdownChoice, Integer, Percentage, Transform, Tuple


def cpu_util_elements():
    return [
        (
            "core_util_time_total",
            Tuple(
                title=_("Levels over an extended time period on total CPU utilization"),
                elements=[
                    Percentage(title=_("High utilization at "), default_value=100.0),
                    Age(title=_("Warning after "), default_value=5 * 60),
                    Age(title=_("Critical after "), default_value=15 * 60),
                ],
                help=_(
                    "With this configuration, Checkmk will alert if the actual (not averaged) total CPU is "
                    "exceeding a utilization threshold over an extended period of time. "
                    "ATTENTION: This configuration cannot be used for check <i>lparstat_aix.cpu_util</i>!"
                ),
            ),
        ),
        (
            "core_util_time",
            Tuple(
                title=_("Levels over an extended time period on a single core CPU utilization"),
                elements=[
                    Percentage(title=_("High utilization at "), default_value=100.0),
                    Age(title=_("Warning after "), default_value=5 * 60),
                    Age(title=_("Critical after "), default_value=15 * 60),
                ],
                help=_(
                    "A single thread fully utilizing a single core (potentially due to a bug) "
                    "may go unnoticed when only monitoring the total utilization of the CPU. "
                    "With this configuration, Checkmk will alert if a single core is "
                    "exceeding a utilization threshold over an extended period of time."
                    "This is currently only supported on linux and windows agents "
                    "as well as devices monitored through the host-resource mib"
                ),
            ),
        ),
        (
            "average",
            Integer(
                title=_("Averaging for total CPU utilization"),
                help=_(
                    "When this option is activated then the CPU utilization is being "
                    "averaged <b>before</b> the levels on total CPU utilization are being applied."
                ),
                unit=_("minutes"),
                minvalue=1,
                default_value=15,
                label=_("Compute average over last "),
            ),
        ),
        (
            "average_single",
            Dictionary(
                title=_("Averaging for single cores"),
                help=_(
                    "Compute averaged single-core CPU utilizations. Note that this option only has "
                    "an effect if at least one of the sub-options 'Apply single-core levels' or "
                    "'Graphs for averaged single-core utilizations' is enabled."
                ),
                elements=[
                    (
                        "time_average",
                        Integer(
                            title=_("Time frame"),
                            unit=_("minutes"),
                            minvalue=1,
                            default_value=15,
                            label=_("Compute average over last "),
                        ),
                    ),
                    (
                        "apply_levels",
                        DropdownChoice(
                            title=_("Apply single-core levels defined in 'Levels on single cores'"),
                            help=_(
                                "Apply the levels for single cores to the averaged instead of the "
                                "instantaneous utilizations."
                            ),
                            choices=[
                                (True, _("Enable")),
                                (False, _("Disable")),
                            ],
                            default_value=False,
                        ),
                    ),
                    (
                        "show_graph",
                        DropdownChoice(
                            title=_("Graphs for averaged single-core utilizations"),
                            help=_(
                                "Create a separate graph showing the averaged single-core CPU "
                                "utilizations."
                            ),
                            choices=[
                                (True, _("Enable")),
                                (False, _("Disable")),
                            ],
                            default_value=False,
                        ),
                    ),
                ],
                optional_keys=False,
            ),
        ),
        (
            "util",
            Levels(
                title=_("Levels on total CPU utilization"),
                unit="%",
                default_levels=(90, 95),
                default_difference=(5, 8),
                default_value=None,
                help=_(
                    "The CPU utilization sums up the percentages of CPU time that is used "
                    "for user processes, kernel routines (system), disk wait (sometimes also "
                    "called IO wait) or nothing (idle). The levels are always applied "
                    "on the average utilization since the last check - which is usually one minute."
                ),
            ),
        ),
        (
            "levels_single",
            Tuple(
                title=_("Levels on single cores"),
                elements=[
                    Percentage(title=_("Warning at"), default_value=90.0),
                    Percentage(title=_("Critical at"), default_value=95.0),
                ],
                help=_("Here you can set levels on the CPU utilization on single cores"),
            ),
        ),
        (
            "core_util_graph",
            DropdownChoice(
                title=_("Graphs for individual cores"),
                help=_(
                    "This adds another graph to the performance CPU utilization "
                    "details page, showing utilization of individual cores. "
                    "Please note that this graph may be impractical on "
                    "device with very many cores. "
                    "This is currently only supported on linux and windows agents "
                    "as well as devices monitored through the host-resource mib"
                ),
                choices=[
                    (True, _("Enable")),
                    (False, _("Disable")),
                ],
                default_value=True,
            ),
        ),
    ]


def _cpu_util_unix_elements():
    return [
        (
            "iowait",
            Tuple(
                title=_("Levels on IO wait (UNIX only)"),
                elements=[
                    Percentage(title=_("Warning at a disk wait of"), default_value=5.0),
                    Percentage(title=_("Critical at a disk wait of"), default_value=10.0),
                ],
                help=_(
                    "The disk wait is the total percentage of time all CPUs have nothing else to do but waiting "
                    "for data coming from or going to disk. If you have a significant disk wait "
                    "the the bottleneck of your server is IO. Please note that depending on the "
                    "applications being run this might or might not be totally normal."
                ),
            ),
        ),
        (
            "steal",
            Tuple(
                title=_("Levels on steal CPU utilization (UNIX only)"),
                elements=[
                    Percentage(title=_("Warning at a steal time of"), default_value=30.0),
                    Percentage(title=_("Critical at a steal time of"), default_value=50.0),
                ],
                help=_("Here you can set levels on the steal CPU utilization."),
            ),
        ),
    ]


def _cpu_util_common_elements():
    return Dictionary(
        help=_(
            "This rule configures levels for the CPU utilization (not load) for "
            "Linux/UNIX and Windows, as well as devices "
            "implementing the Host Resources MIB. The utilization "
            "percentage is computed with respect to the total number of CPUs. "
            "Note that not all parameters you can configure here are applicable "
            "to all checks."
        ),
        elements=cpu_util_elements() + _cpu_util_unix_elements(),
    )


def transform_legacy_cpu_utilization_os(params):
    if "levels" in params:
        params["util"] = params.pop("levels")
    return params


def _parameter_valuespec_cpu_utilization_os():
    return Transform(
        valuespec=_cpu_util_common_elements(),
        forth=transform_legacy_cpu_utilization_os,
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="cpu_utilization_os",
        group=RulespecGroupCheckParametersOperatingSystem,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_cpu_utilization_os,
        title=lambda: _("CPU utilization for simple devices"),
    )
)


def transform_cpu_iowait(params):
    if isinstance(params, tuple):
        return {"iowait": params}
    return params


def _parameter_valuespec_cpu_iowait():
    return Transform(
        valuespec=_cpu_util_common_elements(),
        forth=transform_cpu_iowait,
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="cpu_iowait",
        group=RulespecGroupCheckParametersOperatingSystem,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_cpu_iowait,
        title=lambda: _("CPU utilization on Linux/UNIX"),
    )
)


def _transform_cpu_utilization(params):
    if params is None:
        return {}
    if isinstance(params, tuple):
        return {"util": params}
    return params


def _parameter_valuespec_cpu_utilization():
    return Transform(
        valuespec=Dictionary(
            elements=[
                (
                    "util",
                    Tuple(
                        elements=[
                            Percentage(title=_("Warning at a utilization of")),
                            Percentage(title=_("Critical at a utilization of")),
                        ],
                        title=_("Alert on excessive CPU utilization"),
                        help=_(
                            "The CPU utilization sums up the percentages of CPU time that is used "
                            "for user processes and kernel routines over all available cores within "
                            "the last check interval. The possible range is from 0% to 100%"
                        ),
                        default_value=(90.0, 95.0),
                    ),
                ),
            ]
        ),
        forth=_transform_cpu_utilization,
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="cpu_utilization",
        group=RulespecGroupCheckParametersOperatingSystem,
        parameter_valuespec=_parameter_valuespec_cpu_utilization,
        title=lambda: _("CPU utilization for Appliances"),
    )
)
