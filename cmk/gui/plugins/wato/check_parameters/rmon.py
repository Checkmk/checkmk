#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    HostRulespec,
    rulespec_registry,
    RulespecGroupCheckParametersDiscovery,
)
from cmk.gui.valuespec import Checkbox, Dictionary, Migrate


def _discover_rmon() -> Migrate:
    return Migrate(
        valuespec=Dictionary(
            elements=[
                (
                    "discover",
                    Checkbox(
                        label=_("Discover RMON statistics services"),
                        default_value=True,
                        help=_(
                            "Enabling this option will result in an additional service for every RMON-capable "
                            "switch port. This service will provide detailed information on the distribution of "
                            "packet sizes transferred over the port. Note: currently, this additional RMON check "
                            "does not honor the inventory settings for switch ports."
                        ),
                    ),
                ),
            ],
            optional_keys=[],
        ),
        migrate=lambda p: p if isinstance(p, dict) else {"discover": p},
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupCheckParametersDiscovery,
        match_type="merge",
        name="rmon_discovery",
        title=lambda: _("RMON statistics"),
        valuespec=_discover_rmon,
    )
)
