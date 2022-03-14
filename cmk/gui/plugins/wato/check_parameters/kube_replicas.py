#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.check_parameters.kube import age_levels_dropdown
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Dictionary


def _parameter_valuespec():
    return Dictionary(
        help=_(
            (
                "This ruleset is relevant for Kubernetes replicas. You can set "
                "a maximum allowed duration during which replicas may be in a not "
                "ready or not up-to-date state. Keep in mind that replicas may "
                "temporarily be in these states during the process of an update. "
                "Therefore, it is recommended to always have a grace period "
                "configured."
            )
        ),
        elements=[
            ("update_duration", age_levels_dropdown(_("Update duration"))),
            ("not_ready_duration", age_levels_dropdown(_("Not ready duration"))),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="kube_replicas",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec,
        title=lambda: _("Kubernetes replicas"),
    )
)
