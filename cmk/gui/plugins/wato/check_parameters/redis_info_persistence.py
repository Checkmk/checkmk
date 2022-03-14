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
from cmk.gui.valuespec import Dictionary, Integer, MonitoringState, TextInput, Tuple


def _parameter_valuespec_redis_info_persistence():
    return Dictionary(
        elements=[
            (
                "rdb_last_bgsave_state",
                MonitoringState(
                    title=_("State when last RDB save operation was faulty"), default_value=1
                ),
            ),
            (
                "aof_last_rewrite_state",
                MonitoringState(
                    title=_("State when Last AOF rewrite operation was faulty"), default_value=1
                ),
            ),
            (
                "rdb_changes_count",
                Tuple(
                    title=_("Number of changes since last dump"),
                    elements=[
                        Integer(title=_("Warning at"), unit="changes"),
                        Integer(title=_("Critical at"), unit="changes"),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="redis_info_persistence",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextInput(title=_("Redis server name")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_redis_info_persistence,
        title=lambda: _("Redis persistence"),
    )
)
