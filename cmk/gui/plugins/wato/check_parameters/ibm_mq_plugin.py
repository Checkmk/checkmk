#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    CascadingDropdown,
    Dictionary,
    TextAscii,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)


# Also used in ibm_mq_managers
def ibm_mq_version():
    return [
        (
            "version",
            CascadingDropdown(
                title=_("Check for correct version"),
                help=_("You can make sure that the plugin is running"
                       " with a specific or a minimal version."),
                choices=[
                    ('at_least', _("At least"), TextAscii(title=_("At least"), allow_empty=False)),
                    ('specific', _("Specific version"),
                     TextAscii(title=_("Specific version"), allow_empty=False)),
                ],
            ),
        ),
    ]


def _parameter_valuespec_ibm_mq_plugin():
    return Dictionary(elements=ibm_mq_version(),)


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="ibm_mq_plugin",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_ibm_mq_plugin,
        title=lambda: _("IBM MQ Plugin"),
    ))
