#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    Levels,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)


def _parameter_valuespec_safenet_ntls_clients():
    return Levels(
        title=_("NTLS Clients"),
        help=_("Number of connected clients"),
        default_value=None,
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="safenet_ntls_clients",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_safenet_ntls_clients,
        title=lambda: _("Safenet NTLS Clients"),
    )
)
