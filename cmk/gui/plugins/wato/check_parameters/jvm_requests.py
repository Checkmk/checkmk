#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Integer, TextInput, Tuple


def _item_spec_jvm_requests():
    return TextInput(
        title=_("Name of the virtual machine"),
        help=_("The name of the application server"),
        allow_empty=False,
    )


def _parameter_valuespec_jvm_requests():
    return Tuple(
        help=_(
            "This rule sets the warn and crit levels for the number "
            "of incoming requests to a JVM application server."
        ),
        elements=[
            Integer(
                title=_("Warning if below"),
                unit=_("requests/sec"),
                default_value=-1,
            ),
            Integer(
                title=_("Critical if below"),
                unit=_("requests/sec"),
                default_value=-1,
            ),
            Integer(
                title=_("Warning at"),
                unit=_("requests/sec"),
                default_value=800,
            ),
            Integer(
                title=_("Critical at"),
                unit=_("requests/sec"),
                default_value=1000,
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="jvm_requests",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_jvm_requests,
        parameter_valuespec=_parameter_valuespec_jvm_requests,
        title=lambda: _("JVM request count"),
    )
)
