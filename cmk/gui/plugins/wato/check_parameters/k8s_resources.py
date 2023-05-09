#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Dictionary,
    Tuple,
    Percentage,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)


def _parameter_valuespec_k8s_resources():
    return Dictionary(elements=[
        ('pods',
         Tuple(
             title=_('Pods'),
             default_value=(80.0, 90.0),
             elements=[
                 Percentage(title=_("Warning above")),
                 Percentage(title=_("Critical above")),
             ],
         )),
        ('cpu',
         Tuple(
             title=_('CPU'),
             default_value=(80.0, 90.0),
             elements=[
                 Percentage(title=_("Warning above")),
                 Percentage(title=_("Critical above")),
             ],
         )),
        ('memory',
         Tuple(
             title=_('Memory'),
             default_value=(80.0, 90.0),
             elements=[
                 Percentage(title=_("Warning above")),
                 Percentage(title=_("Critical above")),
             ],
         )),
    ],)


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="k8s_resources",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_k8s_resources,
        title=lambda: _("Kubernetes resources"),
    ))
