#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Integer,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)


def _parameter_valuespec_checkpoint_connections():
    return Tuple(
        help=_("This rule sets limits to the current number of connections through "
               "a Checkpoint firewall."),
        title=_("Maximum number of firewall connections"),
        elements=[
            Integer(title=_("Warning at"), default_value=40000),
            Integer(title=_("Critical at"), default_value=50000),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="checkpoint_connections",
        group=RulespecGroupCheckParametersApplications,
        parameter_valuespec=_parameter_valuespec_checkpoint_connections,
        title=lambda: _("Checkpoint Firewall Connections"),
    ))
