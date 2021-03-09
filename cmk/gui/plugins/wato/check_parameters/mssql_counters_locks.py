#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Checkbox,
    Dictionary,
    Float,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
    RulespecGroupCheckParametersDiscovery,
    HostRulespec,
)

from cmk.gui.plugins.wato.check_parameters.utils import mssql_item_spec_instance_tablespace


def _valuespec_inventory_mssql_counters_rules():
    return Dictionary(
        title=_("Include MSSQL Counters services"),
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
    ))


def _parameter_valuespec_mssql_counters_locks():
    return Dictionary(
        help=_("This check monitors locking related information of MSSQL tablespaces."),
        elements=[
            (
                "lock_requests/sec",
                Tuple(
                    title=_("Lock Requests / sec"),
                    help=
                    _("Number of new locks and lock conversions per second requested from the lock manager."
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
                    help=
                    _("Number of lock requests per second that timed out, including requests for NOWAIT locks."
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
    ))
