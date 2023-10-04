#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersOperatingSystem,
)
from cmk.gui.valuespec import Dictionary, Migrate, MonitoringState


def _parameter_valuespec():
    return Migrate(
        valuespec=Dictionary(
            elements=[
                (
                    "security",
                    MonitoringState(
                        title=_("State when security updates are pending"),
                        default_value=2,
                    ),
                ),
                (
                    "recommended",
                    MonitoringState(
                        title=_("State when recommended updates are pending"),
                        default_value=1,
                    ),
                ),
                (
                    "other",
                    MonitoringState(
                        title=_(
                            "State when updates are pending, which are neither recommended or a security update"
                        ),
                        default_value=0,
                    ),
                ),
                (
                    "locks",
                    MonitoringState(
                        title=_("State when packages are locked"),
                        default_value=1,
                    ),
                ),
            ],
        ),
        migrate=lambda v: v or {},
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="zypper",
        group=RulespecGroupCheckParametersOperatingSystem,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec,
        title=lambda: _("Zypper Updates"),
    )
)
