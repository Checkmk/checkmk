#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Dictionary, MonitoringState, TextInput


def _parameter_valuespec_veritas_vcs():
    return Dictionary(
        elements=[
            (
                "map_states",
                Dictionary(
                    title=_("Map Attribute 'State'"),
                    elements=[
                        ("ONLINE", MonitoringState(title=_("ONLINE"), default_value=0)),
                        ("RUNNING", MonitoringState(title=_("RUNNING"), default_value=0)),
                        ("OK", MonitoringState(title=_("OK"), default_value=0)),
                        ("OFFLINE", MonitoringState(title=_("OFFLINE"), default_value=1)),
                        ("EXITED", MonitoringState(title=_("EXITED"), default_value=1)),
                        ("PARTIAL", MonitoringState(title=_("PARTIAL"), default_value=1)),
                        ("FAULTED", MonitoringState(title=_("FAULTED"), default_value=2)),
                        ("UNKNOWN", MonitoringState(title=_("UNKNOWN"), default_value=3)),
                        (
                            "default",
                            MonitoringState(
                                title=_("States other than the above"), default_value=1
                            ),
                        ),
                    ],
                    optional_keys=False,
                ),
            ),
            (
                "map_frozen",
                Dictionary(
                    title=_("Map Attribute 'Frozen'"),
                    elements=[
                        (
                            "tfrozen",
                            MonitoringState(title=_("Temporarily frozen"), default_value=1),
                        ),
                        ("frozen", MonitoringState(title=_("Frozen"), default_value=2)),
                    ],
                    optional_keys=False,
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="veritas_vcs",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextInput(title=_("Cluster Name")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_veritas_vcs,
        title=lambda: _("Veritas Cluster Server"),
    )
)
