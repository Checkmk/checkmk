#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.plugins.wato.check_mk_configuration import RulespecGroupHostsMonitoringRulesVarious
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import Dictionary


def _valuespec_host_groups():
    return Dictionary(elements=[])


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupHostsMonitoringRulesVarious,
        match_type="dict",
        name="test",
        valuespec=_valuespec_host_groups,
    )
)
