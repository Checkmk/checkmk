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
from cmk.gui.valuespec import Dictionary, Float, Percentage, TextInput, Tuple


def _item_spec_jvm_gc():
    return TextInput(
        title=_("Name of the virtual machine and/or<br>garbage collection type"),
        help=_("The name of the application server"),
        allow_empty=False,
    )


def _parameter_valuespec_jvm_gc() -> Dictionary:
    return Dictionary(
        help=_("This ruleset also covers Tomcat, Jolokia and JMX. "),
        elements=[
            (
                "collection_time",
                Tuple(
                    title=_("Time spent collecting garbage in percent"),
                    elements=[
                        Percentage(title=_("Warning at")),
                        Percentage(title=_("Critical at")),
                    ],
                ),
            ),
            (
                "collection_count",
                Tuple(
                    title=_("Count of garbage collections per second"),
                    elements=[
                        Float(title=_("Warning at")),
                        Float(title=_("Critical at")),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="jvm_gc",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_jvm_gc,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_jvm_gc,
        title=lambda: _("JVM garbage collection levels"),
    )
)
