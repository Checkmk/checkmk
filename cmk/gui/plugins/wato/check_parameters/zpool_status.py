#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    ManualCheckParameterRulespec,
    rulespec_registry,
    RulespecGroupEnforcedServicesStorage,
)
from cmk.gui.valuespec import Dictionary

rulespec_registry.register(
    ManualCheckParameterRulespec(
        check_group_name="zpool_status",
        group=RulespecGroupEnforcedServicesStorage,
        parameter_valuespec=lambda: Dictionary(
            elements=(),
            title=_("This plug-in has no paramaters"),
            empty_text=_("This plug-in has no paramaters"),
        ),
        title=lambda: _("ZFS storage pool status"),
    )
)
