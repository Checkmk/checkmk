#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Dictionary,
    DropdownChoice,
    Float,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersStorage,
)


def _item_spec_ddn_s2a_wait():
    return DropdownChoice(title=_(u"Host or Disk"),
                          choices=[
                              ("Disk", _(u"Disk")),
                              ("Host", _(u"Host")),
                          ])


def _parameter_valuespec_ddn_s2a_wait():
    return Dictionary(elements=[
        ("read_avg",
         Tuple(
             title=_(u"Read wait average"),
             elements=[
                 Float(title=_(u"Warning at"), unit="s"),
                 Float(title=_(u"Critical at"), unit="s"),
             ],
         )),
        ("read_min",
         Tuple(
             title=_(u"Read wait minimum"),
             elements=[
                 Float(title=_(u"Warning at"), unit="s"),
                 Float(title=_(u"Critical at"), unit="s"),
             ],
         )),
        ("read_max",
         Tuple(
             title=_(u"Read wait maximum"),
             elements=[
                 Float(title=_(u"Warning at"), unit="s"),
                 Float(title=_(u"Critical at"), unit="s"),
             ],
         )),
        ("write_avg",
         Tuple(
             title=_(u"Write wait average"),
             elements=[
                 Float(title=_(u"Warning at"), unit="s"),
                 Float(title=_(u"Critical at"), unit="s"),
             ],
         )),
        ("write_min",
         Tuple(
             title=_(u"Write wait minimum"),
             elements=[
                 Float(title=_(u"Warning at"), unit="s"),
                 Float(title=_(u"Critical at"), unit="s"),
             ],
         )),
        ("write_max",
         Tuple(
             title=_(u"Write wait maximum"),
             elements=[
                 Float(title=_(u"Warning at"), unit="s"),
                 Float(title=_(u"Critical at"), unit="s"),
             ],
         )),
    ],)


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="ddn_s2a_wait",
        group=RulespecGroupCheckParametersStorage,
        item_spec=_item_spec_ddn_s2a_wait,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_ddn_s2a_wait,
        title=lambda: _("Read/write wait for DDN S2A devices"),
    ))
