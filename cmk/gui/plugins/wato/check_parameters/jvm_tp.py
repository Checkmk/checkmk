#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Alternative,
    Dictionary,
    Integer,
    TextAscii,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)


def _item_spec_jvm_tp() -> TextAscii:
    return TextAscii(
        title=_("Name of the virtual machine and/or<br>threadpool"),
        help=_("The name of the application server"),
        allow_empty=False,
    )


def _parameter_valuespec_jvm_tp() -> Dictionary:
    return Dictionary(
        help=_("This ruleset also covers Tomcat, Jolokia and JMX. "),
        elements=[
            ("currentThreadCount",
             Alternative(
                 title=_("Current thread count levels"),
                 elements=[
                     Tuple(
                         title=_("Percentage levels of current thread count in threadpool"),
                         elements=[
                             Integer(title=_("Warning at"), unit=_("%")),
                             Integer(title=_("Critical at"), unit=_("%")),
                         ],
                     )
                 ],
             )),
            ("currentThreadsBusy",
             Alternative(
                 title=_("Current threads busy levels"),
                 elements=[
                     Tuple(
                         title=_("Percentage of current threads busy in threadpool"),
                         elements=[
                             Integer(title=_("Warning at"), unit=_("%")),
                             Integer(title=_("Critical at"), unit=_("%")),
                         ],
                     )
                 ],
             )),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="jvm_tp",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_jvm_tp,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_jvm_tp,
        title=lambda: _("JVM tomcat threadpool levels"),
    ))
