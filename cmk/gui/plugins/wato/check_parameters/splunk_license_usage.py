#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Alternative, Dictionary, Filesize, Percentage, Tuple


def _parameter_valuespec_splunk_license_usage():
    return Dictionary(
        elements=[
            (
                "usage_bytes",
                Alternative(
                    title=_("Used quota: Absolute or relative upper levels"),
                    elements=[
                        Tuple(
                            title=_("Upper absolute levels"),
                            elements=[
                                Filesize(title=_("Warning at")),
                                Filesize(title=_("Critical at")),
                            ],
                        ),
                        Tuple(
                            title=_("Upper percentage levels"),
                            elements=[
                                Percentage(title=_("Warning at"), default_value=80.0),
                                Percentage(title=_("Critical at"), default_value=90.0),
                            ],
                        ),
                    ],
                ),
            ),
        ],
        optional_keys=["usage_bytes"],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="splunk_license_usage",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_splunk_license_usage,
        title=lambda: _("Splunk License Usage"),
    )
)
