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
from cmk.gui.valuespec import Age, Dictionary, Integer, TextInput, Tuple


def _parameter_valuespec_mongodb_replication_lag():
    return Dictionary(
        elements=[
            (
                "levels_mongdb_replication_lag",
                _sec_tuple(_("Levels over an extended time period on replication lag")),
            )
        ]
    )


def _sec_tuple(title: str) -> Tuple:
    return Tuple(
        title=title,
        elements=[
            Integer(
                title=_(
                    "Time between the last operation on primary's oplog and on secondary above"
                ),
                unit=_("seconds"),
                default_value=10,
                minvalue=0,
            ),
            Age(title=_("Warning equal or after "), default_value=5 * 60),
            Age(title=_("Critical equal or after "), default_value=15 * 60),
        ],
        help=_(
            "Replication lag is a delay between an operation on the primary and the application "
            "of that operation from the oplog to the secondary."
            "With this configuration, check_mk will alert if replication lag is "
            "exceeding a threshold over an extended period of time."
        ),
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="mongodb_replica_set",
        group=RulespecGroupCheckParametersStorage,
        item_spec=lambda: TextInput(
            title=_("MongoDB Replica Set"),
        ),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_mongodb_replication_lag,
        title=lambda: _("MongoDB Replica Set"),
    )
)
