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
from cmk.gui.valuespec import Dictionary, Integer, MonitoringState, TextInput, Tuple


def _parameter_valuespec_emcvnx_disks():
    return Dictionary(
        elements=[
            (
                "state_read_error",
                Tuple(
                    title=_("State on hard read error"),
                    elements=[
                        MonitoringState(
                            title=_("State"),
                            default_value=2,
                        ),
                        Integer(
                            title=_("Minimum error count"),
                            default_value=2,
                        ),
                    ],
                ),
            ),
            (
                "state_write_error",
                Tuple(
                    title=_("State on hard write error"),
                    elements=[
                        MonitoringState(
                            title=_("State"),
                            default_value=2,
                        ),
                        Integer(
                            title=_("Minimum error count"),
                            default_value=2,
                        ),
                    ],
                ),
            ),
            (
                "state_rebuilding",
                MonitoringState(default_value=1, title=_("State when rebuildung enclosure")),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="emcvnx_disks",
        group=RulespecGroupCheckParametersStorage,
        item_spec=lambda: TextInput(title=_("Enclosure ID"), allow_empty=True),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_emcvnx_disks,
        title=lambda: _("EMC VNX Enclosures"),
    )
)
