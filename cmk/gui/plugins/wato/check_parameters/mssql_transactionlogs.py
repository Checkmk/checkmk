#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.check_parameters.mssql_datafiles import levels_absolute_or_dynamic
from cmk.gui.plugins.wato.check_parameters.mssql_utils import mssql_item_spec_instance_database_file
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    HostRulespec,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
    RulespecGroupCheckParametersDiscovery,
)
from cmk.gui.valuespec import Checkbox, Dictionary


def _valuespec_mssql_transactionlogs_discovery():
    return Dictionary(
        title=_("MSSQL datafile and transactionlog discovery"),
        elements=[
            (
                "summarize_datafiles",
                Checkbox(
                    title=_("Display only a summary of all Datafiles"),
                    label=_("Summarize Datafiles"),
                ),
            ),
            (
                "summarize_transactionlogs",
                Checkbox(
                    title=_("Display only a summary of all Transactionlogs"),
                    label=_("Summarize Transactionlogs"),
                ),
            ),
        ],
        optional_keys=[],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupCheckParametersDiscovery,
        name="mssql_transactionlogs_discovery",
        valuespec=_valuespec_mssql_transactionlogs_discovery,
    )
)


def _parameter_valuespec_mssql_transactionlogs():
    return Dictionary(
        title=_("File Size Levels"),
        help=_(
            "Specify levels for transactionlogs of a database. Please note that relative "
            "levels will only work if there is a max_size set for the file on the database "
            "side."
        ),
        elements=[
            ("used_levels", levels_absolute_or_dynamic(_("Transactionlog"), _("used"))),
            (
                "allocated_used_levels",
                levels_absolute_or_dynamic(_("Transactionlog"), _("used of allocation")),
            ),
            ("allocated_levels", levels_absolute_or_dynamic(_("Transactionlog"), _("allocated"))),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="mssql_transactionlogs",
        group=RulespecGroupCheckParametersApplications,
        item_spec=mssql_item_spec_instance_database_file,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_mssql_transactionlogs,
        title=lambda: _("MSSQL Transactionlog Sizes"),
    )
)
