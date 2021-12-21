#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    BinaryHostRulespec,
    rulespec_registry,
    RulespecGroupCheckParametersNetworking,
)

rulespec_registry.register(
    BinaryHostRulespec(
        group=RulespecGroupCheckParametersNetworking,
        help_func=lambda: _(
            "Enabling this option will result in an additional service for every RMON-capable "
            "switch port. This service will provide detailed information on the distribution of "
            "packet sizes transferred over the port. Note: currently, this additional RMON check "
            "does not honor the inventory settings for switch ports."
        ),
        name="rmon_discovery",
        title=lambda: _("RMON statistics"),
    )
)
