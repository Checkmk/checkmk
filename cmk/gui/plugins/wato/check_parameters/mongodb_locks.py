#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersStorage,
)
from cmk.gui.valuespec import Dictionary, Integer, Tuple


def _parameter_valuespec_mongodb_locks():
    return Dictionary(
        elements=[
            (
                "%s_locks" % what,
                Tuple(
                    title=_("%s Locks") % what.title().replace("_", " "),
                    elements=[
                        Integer(title=_("Warning at"), minvalue=0),
                        Integer(title=_("Critical at"), minvalue=0),
                    ],
                ),
            )
            for what in [
                "clients_readers",
                "clients_writers",
                "clients_total",
                "queue_readers",
                "queue_writers",
                "queue_total",
            ]
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="mongodb_locks",
        group=RulespecGroupCheckParametersStorage,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_mongodb_locks,
        title=lambda: _("MongoDB Locks"),
    )
)
