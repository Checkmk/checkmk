#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.check_parameters.utils import (
    get_free_used_dynamic_valuespec,
    transform_filesystem_free,
)
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Dictionary, TextInput, Transform


def _item_spec_db2_logsize():
    return TextInput(
        title=_("Instance"), help=_("DB2 instance followed by database name, e.g db2taddm:CMDBS1")
    )


def _parameter_valuespec_db2_logsize():
    return Dictionary(
        elements=[
            (
                "levels",
                Transform(
                    valuespec=get_free_used_dynamic_valuespec(
                        "free", "logfile", default_value=(20.0, 10.0)
                    ),
                    title=_("Logfile levels"),
                    forth=transform_filesystem_free,
                    back=transform_filesystem_free,
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="db2_logsize",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_db2_logsize,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_db2_logsize,
        title=lambda: _("DB2 logfile usage"),
    )
)
