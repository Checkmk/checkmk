#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Dictionary, Filesize, Percentage, TextInput, Tuple


def _item_spec_jvm_memory() -> TextInput:
    return TextInput(
        title=_("Name of the virtual machine"),
        help=_("The name of the application server"),
        allow_empty=False,
    )


def _get_memory_level_elements(mem_type: str) -> Iterable[tuple[str, Tuple]]:
    return [
        (
            "perc_%s" % mem_type,
            Tuple(
                title=_("Percentual levels for %s memory") % mem_type,
                elements=[
                    Percentage(
                        title=_("Warning at"),
                        # xgettext: no-python-format
                        label=_("% usage"),
                        default_value=80.0,
                        maxvalue=None,
                    ),
                    Percentage(
                        title=_("Critical at"),
                        # xgettext: no-python-format
                        label=_("% usage"),
                        default_value=90.0,
                        maxvalue=None,
                    ),
                ],
            ),
        ),
        (
            "abs_%s" % mem_type,
            Tuple(
                title=_("Absolute levels for %s memory") % mem_type,
                elements=[
                    Filesize(title=_("Warning at")),
                    Filesize(title=_("Critical at")),
                ],
            ),
        ),
    ]


def _parameter_valuespec_jvm_memory() -> Dictionary:
    return Dictionary(
        help=(
            _(
                "This rule allows to set the warn and crit levels of the heap / "
                "non-heap and total memory area usage on web application servers."
            )
            + " "
            + _("Other keywords for this rule: %s") % "Tomcat, Jolokia, JMX"
        ),
        elements=[
            element
            for mem_type in ("heap", "nonheap", "total")
            for element in _get_memory_level_elements(mem_type)
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="jvm_memory",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_jvm_memory,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_jvm_memory,
        title=lambda: _("JVM memory levels"),
    )
)


def _item_spec_jvm_memory_pools() -> TextInput:
    return TextInput(
        title=_("Name of the memory pool"),
        help=_("The name of the memory pool in the format 'INSTANCE Memory Pool POOLNAME'"),
        allow_empty=False,
    )


def _parameter_valuespec_jvm_memory_pools() -> Dictionary:
    return Dictionary(
        help=(
            _(
                "This rule allows to set the warn and crit levels of the memory"
                " pools on web application servers."
            )
            + " "
            + _("Other keywords for this rule: %s") % "Tomcat, Jolokia, JMX"
        ),
        elements=_get_memory_level_elements("used"),
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="jvm_memory_pools",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_jvm_memory_pools,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_jvm_memory_pools,
        title=lambda: _("JVM memory pool levels"),
    )
)
