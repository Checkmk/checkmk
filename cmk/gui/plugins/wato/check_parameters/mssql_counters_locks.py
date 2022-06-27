#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.check_parameters.mssql_utils import mssql_item_spec_instance_tablespace
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    HostRulespec,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
    RulespecGroupCheckParametersDiscovery,
)
from cmk.gui.valuespec import Checkbox, Dictionary, Float, Tuple


def _valuespec_inventory_mssql_counters_rules():
    return Dictionary(
        title=_("MSSQL counter discovery"),
        elements=[
            ("add_zero_based_services", Checkbox(title=_("Include service with zero base."))),
        ],
        optional_keys=[],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupCheckParametersDiscovery,
        match_type="dict",
        name="inventory_mssql_counters_rules",
        valuespec=_valuespec_inventory_mssql_counters_rules,
    )
)


def _parameter_valuespec_mssql_counters_locks():
    return Dictionary(
        help=_("This check monitors locking related information of MSSQL tablespaces."),
        elements=[
            (
                "lock_requests/sec",
                Tuple(
                    title=_("Lock Requests / sec"),
                    help=_(
                        "Number of new locks and lock conversions per second requested from the lock manager."
                    ),
                    elements=[
                        Float(title=_("Warning at"), unit=_("requests/sec")),
                        Float(title=_("Critical at"), unit=_("requests/sec")),
                    ],
                ),
            ),
            (
                "lock_timeouts/sec",
                Tuple(
                    title=_("Lock Timeouts / sec"),
                    help=_(
                        "Number of lock requests per second that timed out, including requests for NOWAIT locks."
                    ),
                    elements=[
                        Float(title=_("Warning at"), unit=_("timeouts/sec")),
                        Float(title=_("Critical at"), unit=_("timeouts/sec")),
                    ],
                ),
            ),
            (
                "number_of_deadlocks/sec",
                Tuple(
                    title=_("Number of Deadlocks / sec"),
                    help=_("Number of lock requests per second that resulted in a deadlock."),
                    elements=[
                        Float(title=_("Warning at"), unit=_("deadlocks/sec")),
                        Float(title=_("Critical at"), unit=_("deadlocks/sec")),
                    ],
                ),
            ),
            (
                "lock_waits/sec",
                Tuple(
                    title=_("Lock Waits / sec"),
                    help=_("Number of lock requests per second that required the caller to wait."),
                    elements=[
                        Float(title=_("Warning at"), unit=_("waits/sec")),
                        Float(title=_("Critical at"), unit=_("waits/sec")),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="mssql_counters_locks",
        group=RulespecGroupCheckParametersApplications,
        item_spec=mssql_item_spec_instance_tablespace,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_mssql_counters_locks,
        title=lambda: _("MSSQL Locks"),
    )
)
