#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
    TextInput,
)
from cmk.gui.plugins.wato.utils.simple_levels import SimpleLevels
from cmk.gui.valuespec import Age, Dictionary, Integer


def _parameter_valuespec_replication_lag():
    return Dictionary(
        title=_("Levels replication"),
        elements=[
            (
                "levels",
                SimpleLevels(Age, title=_("Replication lag"), default_levels=(0, 0)),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="replication_lag",
        item_spec=lambda: TextInput(title=_("Replication Lag")),
        group=RulespecGroupCheckParametersApplications,
        parameter_valuespec=_parameter_valuespec_replication_lag,
        title=lambda: _("Replication Lag"),
    )
)


def _parameter_valuespec_network():
    return Dictionary(
        title=_("Levels network"),
        elements=[
            (
                "ingress_levels",
                SimpleLevels(Integer, title=_("Network in"), unit="B"),
            ),
            (
                "egress_levels",
                SimpleLevels(Integer, title=_("Network out"), unit="B"),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="network_io",
        item_spec=lambda: TextInput(title=_("Network IO")),
        group=RulespecGroupCheckParametersApplications,
        parameter_valuespec=_parameter_valuespec_network,
        title=lambda: _("Network IO"),
    )
)
