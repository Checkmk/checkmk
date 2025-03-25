#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Age, Checkbox, Dictionary, Migrate, MonitoringState, TextInput, Tuple


def _migrate(params: dict) -> dict:
    params.pop("mrp_option", None)
    return params


def _parameter_valuespec_oracle_dataguard_stats():
    return Migrate(
        Dictionary(
            help=_(
                "The Data-Guard statistics are available in Oracle Enterprise Edition with enabled Data-Guard. "
                "The <tt>init.ora</tt> parameter <tt>dg_broker_start</tt> must be <tt>TRUE</tt> for this check. "
                "The apply and transport lag can be configured with this rule."
            ),
            elements=[
                (
                    "active_dataguard_option",
                    MonitoringState(
                        title=_("State in case of Active Data-Guard Option is active: "),
                        help=_(
                            "The Active Data-Guard Option needs an addional license from Oracle."
                        ),
                        default_value=1,
                    ),
                ),
                (
                    "primary_broker_state",
                    Checkbox(
                        title=_("Check State of Broker on Primary: "),
                        default_value=False,
                        help=_(
                            "Data-Guards with dg_broker_start=false needs Ignore Brokerstate to monitor "
                            "the Switchoverstate on Primary."
                        ),
                    ),
                ),
                (
                    "apply_lag",
                    Tuple(
                        title=_("Apply lag: Maximum time"),
                        help=_(
                            "The maximum limit for the apply lag in <tt>v$dataguard_stats</tt>."
                        ),
                        elements=[
                            Age(
                                title=_("Warning at"),
                            ),
                            Age(
                                title=_("Critical at"),
                            ),
                        ],
                    ),
                ),
                (
                    "apply_lag_min",
                    Tuple(
                        title=_("Apply lag: Minimum time"),
                        help=_(
                            "The minimum limit for the apply lag in <tt>v$dataguard_stats</tt>. "
                            "This is only useful if also <i>%s</i> has been configured."
                        )
                        % _("Apply lag: Maximum time"),
                        elements=[
                            Age(
                                title=_("Warning at"),
                            ),
                            Age(
                                title=_("Critical at"),
                            ),
                        ],
                    ),
                ),
                (
                    "missing_apply_lag_state",
                    MonitoringState(
                        title=_("Apply lag: State in case the apply lag is not known"),
                        default_value=1,
                    ),
                ),
                (
                    "transport_lag",
                    Tuple(
                        title=_("Transport Lag"),
                        help=_("The limit for the transport lag in <tt>v$dataguard_stats</tt>"),
                        elements=[
                            Age(
                                title=_("Warning at"),
                            ),
                            Age(
                                title=_("Critical at"),
                            ),
                        ],
                    ),
                ),
            ],
        ),
        migrate=_migrate,
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="oracle_dataguard_stats",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextInput(title=_("Database SID"), size=12, allow_empty=False),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_oracle_dataguard_stats,
        title=lambda: _("Oracle Data-Guard Stats"),
    )
)
