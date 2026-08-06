#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    Levels,
    rulespec_registry,
    RulespecGroupCheckParametersNetworking,
)
from cmk.gui.valuespec import Dictionary


def _parameter_valuespec_checkpoint_packets() -> Dictionary:
    return Dictionary(
        elements=[
            (
                "accepted",
                Levels(
                    title=_("Maximum rate of accepted packets"),
                    default_value=None,
                    default_levels=(100000, 200000),
                    unit="pkts/sec",
                ),
            ),
            (
                "rejected",
                Levels(
                    title=_("Maximum rate of rejected packets"),
                    default_value=None,
                    default_levels=(100000, 200000),
                    unit="pkts/sec",
                ),
            ),
            (
                "dropped",
                Levels(
                    title=_("Maximum rate of dropped packets"),
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
        title=lambda: _("Check point firewall packet rates"),
    )
)
