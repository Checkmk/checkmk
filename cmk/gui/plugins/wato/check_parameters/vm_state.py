#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato import (
    RulespecGroupEnforcedServicesVirtualization,
    ManualCheckParameterRulespec,
    rulespec_registry,
)

rulespec_registry.register(
    ManualCheckParameterRulespec(
        check_group_name="vm_state",
        group=RulespecGroupEnforcedServicesVirtualization,
        title=lambda: _("Overall state of a virtual machine (for example ESX VMs)"),
    ))
