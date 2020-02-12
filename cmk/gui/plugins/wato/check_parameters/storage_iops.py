#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Dictionary,
    Float,
    TextAscii,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersStorage,
)


def _parameter_valuespec_storage_iops():
    return Dictionary(elements=[
        ("read",
         Tuple(
             title=_(u"Read IO operations per second"),
             elements=[
                 Float(title=_(u"Warning at"), unit="1/s"),
                 Float(title=_(u"Critical at"), unit="1/s"),
             ],
         )),
        ("write",
         Tuple(
             title=_(u"Write IO operations per second"),
             elements=[
                 Float(title=_(u"Warning at"), unit="1/s"),
                 Float(title=_(u"Critical at"), unit="1/s"),
             ],
         )),
        ("total",
         Tuple(
             title=_(u"Total IO operations per second"),
             elements=[
                 Float(title=_(u"Warning at"), unit="1/s"),
                 Float(title=_(u"Critical at"), unit="1/s"),
             ],
         )),
    ],)


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="storage_iops",
        group=RulespecGroupCheckParametersStorage,
        item_spec=lambda: TextAscii(title=_("Port index or 'Total'")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_storage_iops,
        title=lambda: _("I/O operations for DDN S2A devices"),
    ))
