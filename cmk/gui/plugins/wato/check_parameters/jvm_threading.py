#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    Levels,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Dictionary, TextInput


def _item_spec_jvm_threading():
    return TextInput(
        title=_("Name of the virtual machine"),
        help=_("The name of the application server"),
        allow_empty=False,
    )


def _parameter_valuespec_jvm_threading():
    return Dictionary(
        elements=[
            (
                "threadcount_levels",
                Levels(
                    title=_("Maximal number of threads"),
                    default_value=None,
                ),
            ),
            (
                "threadrate_levels",
                Levels(
                    title=_("Maximal rate of thread count"),
                    default_value=None,
                ),
            ),
            ("daemonthreadcount_levels", Levels(title=_("Maximal number of daemon threads"))),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="jvm_threading",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_jvm_threading,
        parameter_valuespec=_parameter_valuespec_jvm_threading,
        title=lambda: _("JVM threading"),
    )
)
