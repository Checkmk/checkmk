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
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Dictionary


def _parameter_valuespec_checkpoint_packets():
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
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="checkpoint_packets",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_checkpoint_packets,
        title=lambda: _("Checkpoint Firewall Packet Rates"),
    )
)
