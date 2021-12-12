#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Dictionary, MonitoringState

FRONTEND_STATES = [("OPEN", 0), ("STOP", 2)]
SERVER_STATES = [("UP", 0), ("DOWN", 2), ("NOLB", 2), ("MAINT", 2), ("DRAIN", 2), ("no check", 2)]


def _parameter_valuespec_haproxy_frontend() -> Dictionary:
    return Dictionary(
        title=_("Translation of HAProxy state to monitoring state"),
        help=_(
            "Define a direct translation of the possible states of the HAProxy frontend "
            "to monitoring states, i.e. to the result of the check. This overwrites the default "
            "mapping used by the check."
        ),
        elements=[
            (
                fe_state,
                MonitoringState(
                    title=_("Monitoring state if HAProxy frontend is %s") % fe_state,
                    default_value=default,
                ),
            )
            for fe_state, default in FRONTEND_STATES
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="haproxy_frontend",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_haproxy_frontend,
        title=lambda: _("HAproxy Frontend State"),
    )
)


def _parameter_valuespec_haproxy_server() -> Dictionary:
    return Dictionary(
        title=_("Translation of HAProxy state to monitoring state"),
        help=_(
            "Define a direct translation of the possible states of the HAProxy server "
            "to monitoring states, i.e. to the result of the check. This overwrites the default "
            "mapping used by the check."
        ),
        elements=[
            (
                server_state,
                MonitoringState(
                    title=_("Monitoring state if HAProxy server is %s") % server_state,
                    default_value=default,
                ),
            )
            for server_state, default in SERVER_STATES
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="haproxy_server",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_haproxy_server,
        title=lambda: _("HAproxy Server State"),
    )
)
