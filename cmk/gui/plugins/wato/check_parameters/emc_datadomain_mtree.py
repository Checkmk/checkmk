#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersStorage,
)
from cmk.gui.valuespec import Dictionary, MonitoringState, TextInput

STATES_CHECK_RES = [
    ("deleted", 2),
    ("read-only", 1),
    ("read-write", 0),
    ("replication destination", 0),
    ("retention lock disabled", 0),
    ("retention lock enabled", 0),
    ("unknown", 3),
]


def _parameter_valuespec_emc_datadomain_mtree() -> Dictionary:
    return Dictionary(
        title=_("Mapping of MTree state to monitoring state"),
        help=_(
            "Define a translation of the possible states of the MTree to monitoring "
            "states, i.e. to the result of the check. This overwrites the default "
            "mapping used by the check."
        ),
        elements=[
            (
                state,
                MonitoringState(
                    title=_("Monitoring state if MTree state is '%s'") % state,
                    default_value=check_res,
                ),
            )
            for state, check_res in STATES_CHECK_RES
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="emc_datadomain_mtree",
        group=RulespecGroupCheckParametersStorage,
        item_spec=lambda: TextInput(title=_("MTree name")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_emc_datadomain_mtree,
        title=lambda: _("EMC Data Domain MTree state"),
    )
)
