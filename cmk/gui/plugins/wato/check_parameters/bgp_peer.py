#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersNetworking,
)
from cmk.gui.valuespec import Dictionary, MonitoringState


def _parameter_valuespec_bgp_peer():
    return Dictionary(
        elements=[
            (
                "admin_state_mapping",
                Dictionary(
                    title=_("Admin States"),
                    elements=[
                        ("halted", MonitoringState(title="halted")),
                        ("running", MonitoringState(title="running")),
                    ],
                    optional_keys=[],
                ),
            ),
            (
                "peer_state_mapping",
                Dictionary(
                    title=_("Peer States"),
                    elements=[
                        ("idle", MonitoringState(title="idle")),
                        ("active", MonitoringState(title="active")),
                        ("opensent", MonitoringState(title="opensent")),
                        ("openconfirm", MonitoringState(title="openconfirm")),
                        ("established", MonitoringState(title="established")),
                    ],
                    optional_keys=[],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="bgp_peer",
        group=RulespecGroupCheckParametersNetworking,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_bgp_peer,
        title=lambda: _("BGP Peer State Mapping"),
    )
)
