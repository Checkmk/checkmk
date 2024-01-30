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
from cmk.gui.valuespec import Dictionary, ListOf, Migrate, RegExp, TextInput, Tuple


def _valuespec_sap_value_groups():
    return Migrate(
        valuespec=Dictionary(
            title=_("SAP R/3 grouped values discovery"),
            elements=[
                (
                    "grouping_patterns",
                    ListOf(
                        valuespec=Tuple(
                            help=_("This defines one value grouping pattern"),
                            show_titles=True,
                            orientation="horizontal",
                            elements=[
                                TextInput(
                                    title=_("Name of group"),
                                ),
                                Tuple(
                                    show_titles=True,
                                    orientation="vertical",
                                    elements=[
                                        RegExp(
                                            title=_("Include Pattern"),
                                            mode=RegExp.prefix,
                                        ),
                                        RegExp(
                                            title=_("Exclude Pattern"),
                                            mode=RegExp.prefix,
                                        ),
                                    ],
                                ),
                            ],
                        ),
                        add_label=_("Add pattern group"),
                    ),
                )
            ],
            optional_keys=[],
            help=_(
                "The check <tt>sap.value</tt> normally creates one service for each SAP value. "
                "By defining grouping patterns, you can switch to the check <tt>sap.value_groups</tt>. "
                "That check monitors a list of SAP values at once."
            ),
        ),
        migrate=lambda p: p if isinstance(p, dict) else {"grouping_patterns": p},
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupCheckParametersDiscovery,
        match_type="all",
        name="sap_value_groups",
        valuespec=_valuespec_sap_value_groups,
    )
)
