#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Dictionary,
    Integer,
    TextAscii,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersStorage,
)


def _parameter_valuespec_ddn_s2a_port_errors():
    return Dictionary(elements=[
        ("link_failure_errs",
         Tuple(
             title=_(u"Link failure errors"),
             elements=[
                 Integer(title=_(u"Warning at")),
                 Integer(title=_(u"Critical at")),
             ],
         )),
        ("lost_sync_errs",
         Tuple(
             title=_(u"Lost synchronization errors"),
             elements=[
                 Integer(title=_(u"Warning at")),
                 Integer(title=_(u"Critical at")),
             ],
         )),
        ("loss_of_signal_errs",
         Tuple(
             title=_(u"Loss of signal errors"),
             elements=[
                 Integer(title=_(u"Warning at")),
                 Integer(title=_(u"Critical at")),
             ],
         )),
        ("prim_seq_errs",
         Tuple(
             title=_(u"PrimSeq erros"),
             elements=[
                 Integer(title=_(u"Warning at")),
                 Integer(title=_(u"Critical at")),
             ],
         )),
        ("crc_errs",
         Tuple(
             title=_(u"CRC errors"),
             elements=[
                 Integer(title=_(u"Warning at")),
                 Integer(title=_(u"Critical at")),
             ],
         )),
        ("receive_errs",
         Tuple(
             title=_(u"Receive errors"),
             elements=[
                 Integer(title=_(u"Warning at")),
                 Integer(title=_(u"Critical at")),
             ],
         )),
        ("ctio_timeouts",
         Tuple(
             title=_(u"CTIO timeouts"),
             elements=[
                 Integer(title=_(u"Warning at")),
                 Integer(title=_(u"Critical at")),
             ],
         )),
        ("ctio_xmit_errs",
         Tuple(
             title=_(u"CTIO transmission errors"),
             elements=[
                 Integer(title=_(u"Warning at")),
                 Integer(title=_(u"Critical at")),
             ],
         )),
        ("ctio_other_errs",
         Tuple(
             title=_(u"other CTIO errors"),
             elements=[
                 Integer(title=_(u"Warning at")),
                 Integer(title=_(u"Critical at")),
             ],
         )),
    ],)


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="ddn_s2a_port_errors",
        group=RulespecGroupCheckParametersStorage,
        item_spec=lambda: TextAscii(title="Port index"),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_ddn_s2a_port_errors,
        title=lambda: _("Port errors of DDN S2A devices"),
    ))
