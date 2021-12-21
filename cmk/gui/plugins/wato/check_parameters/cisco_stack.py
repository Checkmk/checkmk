#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersNetworking,
)
from cmk.gui.valuespec import Dictionary, MonitoringState, TextInput


def _parameter_valuespec_cisco_stack() -> Dictionary:
    return Dictionary(
        elements=[
            (
                "waiting",
                MonitoringState(
                    title="waiting",
                    default_value=0,
                    help=_("Waiting for other switches to come online"),
                ),
            ),
            (
                "progressing",
                MonitoringState(
                    title="progressing",
                    default_value=0,
                    help=_("Master election or mismatch checks in progress"),
                ),
            ),
            ("added", MonitoringState(title="added", default_value=0, help=_("Added to stack"))),
            ("ready", MonitoringState(title="ready", default_value=0, help=_("Ready"))),
            (
                "sdmMismatch",
                MonitoringState(
                    title="sdmMismatch", default_value=1, help=_("SDM template mismatch")
                ),
            ),
            (
                "verMismatch",
                MonitoringState(
                    title="verMismatch", default_value=1, help=_("OS version mismatch")
                ),
            ),
            (
                "featureMismatch",
                MonitoringState(
                    title="featureMismatch", default_value=1, help=_("Configured feature mismatch")
                ),
            ),
            (
                "newMasterInit",
                MonitoringState(
                    title="newMasterInit",
                    default_value=0,
                    help=_("Waiting for new master initialization"),
                ),
            ),
            (
                "provisioned",
                MonitoringState(
                    title="provisioned",
                    default_value=0,
                    help=_("Not an active member of the stack"),
                ),
            ),
            (
                "invalid",
                MonitoringState(
                    title="invalid", default_value=2, help=_("State machine in invalid state")
                ),
            ),
            (
                "removed",
                MonitoringState(title="removed", default_value=2, help=_("Removed from stack")),
            ),
        ],
        optional_keys=[],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="cisco_stack",
        group=RulespecGroupCheckParametersNetworking,
        item_spec=lambda: TextInput(
            title=_("Switch number"),
        ),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_cisco_stack,
        title=lambda: _("Cisco Stack Switch Status"),
    )
)
