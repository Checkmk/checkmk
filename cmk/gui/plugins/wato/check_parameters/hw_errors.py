#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    ManualCheckParameterRulespec,
    rulespec_registry,
    RulespecGroupEnforcedServicesHardware,
)

rulespec_registry.register(
    ManualCheckParameterRulespec(
        check_group_name="hw_errors",
        group=RulespecGroupEnforcedServicesHardware,
        title=lambda: _("Simple checks for BIOS/Hardware errors"),
    )
)
