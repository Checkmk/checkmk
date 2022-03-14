#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Dictionary, Integer, MonitoringState, TextInput, Tuple


def _parameter_valuespec_graylog_nodes():
    return Dictionary(
        elements=[
            (
                "lb_alive",
                MonitoringState(
                    title=_("State when load balancer state is alive"), default_value=0
                ),
            ),
            (
                "lb_throttled",
                MonitoringState(
                    title=_("State when load balancer state is throttled"), default_value=2
                ),
            ),
            (
                "lb_dead",
                MonitoringState(title=_("State when load balancer state is dead"), default_value=2),
            ),
            (
                "lc_running",
                MonitoringState(title=_("State when lifecycle state is running"), default_value=0),
            ),
            (
                "lc_starting",
                MonitoringState(title=_("State when lifecycle state is starting"), default_value=1),
            ),
            (
                "lc_halting",
                MonitoringState(title=_("State when lifecycle state is halting"), default_value=1),
            ),
            (
                "lc_paused",
                MonitoringState(title=_("State when lifecycle state is paused"), default_value=1),
            ),
            (
                "lc_uninitialized",
                MonitoringState(
                    title=_("State when lifecycle state is uninitialized"), default_value=1
                ),
            ),
            (
                "lc_failed",
                MonitoringState(title=_("State when lifecycle state is failed"), default_value=2),
            ),
            (
                "lc_throttled",
                MonitoringState(
                    title=_("State when lifecycle state is throttled"), default_value=2
                ),
            ),
            (
                "lc_override_lb_alive",
                MonitoringState(
                    title=_("State when lifecycle state is override_lb_alive"), default_value=0
                ),
            ),
            (
                "lc_override_lb_dead",
                MonitoringState(
                    title=_("State when lifecycle state is override_lb_dead"), default_value=1
                ),
            ),
            (
                "lc_override_lb_throttled",
                MonitoringState(
                    title=_("State when lifecycle state is override_lb_throttled"), default_value=1
                ),
            ),
            (
                "ps_true",
                MonitoringState(title=_("State when index is processing"), default_value=0),
            ),
            (
                "ps_false",
                MonitoringState(title=_("State when index is not processing"), default_value=2),
            ),
            (
                "input_state",
                MonitoringState(
                    title=_("State when input is not in state running"), default_value=1
                ),
            ),
            (
                "input_count_lower",
                Tuple(
                    title=_("Total number of inputs lower level"),
                    elements=[
                        Integer(title=_("Warning if less then"), unit="inputs"),
                        Integer(title=_("Critical if less then"), unit="inputs"),
                    ],
                ),
            ),
            (
                "input_count_upper",
                Tuple(
                    title=_("Total number of inputs upper level"),
                    elements=[
                        Integer(title=_("Warning at"), unit="inputs"),
                        Integer(title=_("Critical at"), unit="inputs"),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="graylog_nodes",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextInput(title=_("Node name")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_graylog_nodes,
        title=lambda: _("Graylog nodes"),
    )
)
