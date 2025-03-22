#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    CheckParameterRulespecWithoutItem,
    Levels,
    rulespec_registry,
    RulespecGroupCheckParametersNetworking,
)
from cmk.gui.valuespec import Dictionary, MonitoringState, TextInput


def _parameter_valuespec_checkpoint_packets() -> Dictionary:
    return Dictionary(
        elements=[
            (
                "accepted",
                Levels(
                    title=_("Maximum Rate of Accepted Packets"),
                    default_value=None,
                    default_levels=(100000, 200000),
                    unit="pkts/sec",
                ),
            ),
            (
                "rejected",
                Levels(
                    title=_("Maximum Rate of Rejected Packets"),
                    default_value=None,
                    default_levels=(100000, 200000),
                    unit="pkts/sec",
                ),
            ),
            (
                "dropped",
                Levels(
                    title=_("Maximum Rate of Dropped Packets"),
                    default_value=None,
                    default_levels=(100000, 200000),
                    unit="pkts/sec",
                ),
            ),
            (
                "logged",
                Levels(
                    title=_("Maximum Rate of Logged Packets"),
                    default_value=None,
                    default_levels=(100000, 200000),
                    unit="pkts/sec",
                ),
            ),
            (
                "espencrypted",
                Levels(
                    title=_("Maximum Rate of ESP Encrypted Packets"),
                    default_value=None,
                    default_levels=(100000, 200000),
                    unit="pkts/sec",
                ),
            ),
            (
                "espdecrypted",
                Levels(
                    title=_("Maximum Rate of ESP Decrypted Packets"),
                    default_value=None,
                    default_levels=(100000, 200000),
                    unit="pkts/sec",
                ),
            ),
        ]
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="checkpoint_packets",
        group=RulespecGroupCheckParametersNetworking,
        parameter_valuespec=_parameter_valuespec_checkpoint_packets,
        title=lambda: _("Check Point Firewall Packet Rates"),
    )
)


def _parameter_valuespec_checkpoint_tunnels() -> Dictionary:
    return Dictionary(
        elements=[
            (
                "Active",
                MonitoringState(
                    title=_("State when VPN status is Active"),
                    default_value=0,
                ),
            ),
            (
                "Destroy",
                MonitoringState(
                    title=_("State when VPN status is Destroy"),
                    default_value=1,
                ),
            ),
            (
                "Idle",
                MonitoringState(
                    title=_("State when VPN status is Idle"),
                    default_value=0,
                ),
            ),
            (
                "Phase1",
                MonitoringState(
                    title=_("State when VPN status is Phase1"),
                    default_value=2,
                ),
            ),
            (
                "Down",
                MonitoringState(
                    title=_("State when VPN status is Down"),
                    default_value=2,
                ),
            ),
            (
                "Init",
                MonitoringState(
                    title=_("State when VPN status is Init"),
                    default_value=1,
                ),
            ),
        ]
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="checkpoint_tunnels",
        group=RulespecGroupCheckParametersNetworking,
        item_spec=lambda: TextInput(
            title=_("Name of VPN tunnel"),
            allow_empty=True,
        ),
        parameter_valuespec=_parameter_valuespec_checkpoint_tunnels,
        title=lambda: _("Check Point Tunnel Status"),
    )
)
