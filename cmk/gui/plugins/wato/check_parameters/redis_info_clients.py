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
from cmk.gui.valuespec import Dictionary, Integer, TextInput, Tuple


def _parameter_valuespec_redis_info_clients():
    return Dictionary(
        elements=[
            (
                "connected_lower",
                Tuple(
                    title=_("Total number of client connections lower level"),
                    elements=[
                        Integer(
                            title=_("Warning below"),
                            unit="connections",
                        ),
                        Integer(
                            title=_("Critical below"),
                            unit="connections",
                        ),
                    ],
                ),
            ),
            (
                "connected_upper",
                Tuple(
                    title=_("Total number of client connections upper level"),
                    elements=[
                        Integer(
                            title=_("Warning at"),
                            unit="connections",
                        ),
                        Integer(
                            title=_("Critical at"),
                            unit="connections",
                        ),
                    ],
                ),
            ),
            (
                "output_lower",
                Tuple(
                    title=_("Longest output list lower level"),
                    elements=[
                        Integer(title=_("Warning below")),
                        Integer(title=_("Critical below")),
                    ],
                ),
            ),
            (
                "output_upper",
                Tuple(
                    title=_("Longest output list upper level"),
                    elements=[
                        Integer(title=_("Warning at")),
                        Integer(title=_("Critical at")),
                    ],
                ),
            ),
            (
                "input_lower",
                Tuple(
                    title=_("Biggest input buffer lower level"),
                    elements=[
                        Integer(title=_("Warning below"), unit="issues"),
                        Integer(title=_("Critical below"), unit="íssues"),
                    ],
                ),
            ),
            (
                "input_upper",
                Tuple(
                    title=_("Biggest input buffer upper level"),
                    elements=[
                        Integer(title=_("Warning at")),
                        Integer(title=_("Critical at")),
                    ],
                ),
            ),
            (
                "blocked_lower",
                Tuple(
                    title=_("Total number of clients pending on a blocking call lower level"),
                    elements=[
                        Integer(
                            title=_("Warning below"),
                            unit="clients",
                        ),
                        Integer(
                            title=_("Critical below"),
                            unit="clients",
                        ),
                    ],
                ),
            ),
            (
                "blocked_upper",
                Tuple(
                    title=_("Total number of clients pending on a blocking call upper level"),
                    elements=[
                        Integer(
                            title=_("Warning at"),
                            unit="clients",
                        ),
                        Integer(
                            title=_("Critical at"),
                            unit="clients",
                        ),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="redis_info_clients",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextInput(title=_("Redis server name")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_redis_info_clients,
        title=lambda: _("Redis clients"),
    )
)
