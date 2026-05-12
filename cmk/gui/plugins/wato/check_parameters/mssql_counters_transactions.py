#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.i18n import _
from cmk.gui.plugins.wato.check_parameters.mssql_utils import mssql_item_spec_instance_tablespace
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Dictionary, Float, Tuple


def _parameter_valuespec_mssql_counters_transactions() -> Dictionary:
    return Dictionary(
        help=_("This check monitors the transactions of MSSQL tablespaces."),
        elements=[
            (
                "transactions/sec",
                Tuple(
                    title=_("Transactions / sec"),
                    help=_("Total number of transactions per second."),
                    elements=[
                        Float(title=_("Warning at"), unit=_("transactions/sec")),
                        Float(title=_("Critical at"), unit=_("transactions/sec")),
                    ],
                ),
            ),
            (
                "write_transactions/sec",
                Tuple(
                    title=_("Write Transactions / sec"),
                    help=_("Number of write transactions per second."),
                    elements=[
                        Float(title=_("Warning at"), unit=_("transactions/sec")),
                        Float(title=_("Critical at"), unit=_("transactions/sec")),
                    ],
                ),
            ),
            (
                "tracked_transactions/sec",
                Tuple(
                    title=_("Tracked Transactions / sec"),
                    help=_("Number of tracked transactions per second."),
                    elements=[
                        Float(title=_("Warning at"), unit=_("transactions/sec")),
                        Float(title=_("Critical at"), unit=_("transactions/sec")),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="mssql_counters_transactions",
        group=RulespecGroupCheckParametersApplications,
        item_spec=mssql_item_spec_instance_tablespace,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_mssql_counters_transactions,
        title=lambda: _("MSSQL Transactions"),
    )
)
