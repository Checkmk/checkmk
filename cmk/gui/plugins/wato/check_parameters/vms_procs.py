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
from cmk.gui.valuespec import Integer, Optional, Tuple


def _parameter_valuespec_vms_procs():
    return Optional(
        valuespec=Tuple(
            elements=[
                Integer(title=_("Warning at"), unit=_("processes"), default_value=100),
                Integer(title=_("Critical at"), unit=_("processes"), default_value=200),
            ],
        ),
        title=_("Impose levels on number of processes"),
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="vms_procs",
        group=RulespecGroupCheckParametersApplications,
        parameter_valuespec=_parameter_valuespec_vms_procs,
        title=lambda: _("OpenVMS processes"),
    )
)
