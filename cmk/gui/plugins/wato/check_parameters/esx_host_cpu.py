#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Dictionary,
    Percentage,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersOperatingSystem,
)


def _parameter_valuespec_esx_host_memory():
    return Dictionary(elements=[
        ("cpu_ready",
         Tuple(
             title=_("CPU ready"),
             elements=[
                 Percentage(title=_("Warning at a CPU ready time of"), default_value=5.0),
                 Percentage(title=_("Critical at a CPU ready time of"), default_value=10.0),
             ],
         )),
        ("cpu_costop",
         Tuple(
             title=_("Co-Stop"),
             elements=[
                 Percentage(title=_("Warning at a Co-Stop time of"), default_value=5.0),
                 Percentage(title=_("Critical at a Co-Stop time of"), default_value=10.0),
             ],
         )),
    ])


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="esx_host_cpu",
        group=RulespecGroupCheckParametersOperatingSystem,
        parameter_valuespec=_parameter_valuespec_esx_host_memory,
        title=lambda: _("CPU usage of ESX host system"),
    ))
