#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Dictionary,
    MonitoringState,
    TextAscii,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersNetworking,
)


def _parameter_valuespec_cisco_stack():
    return Dictionary(
        elements=[
            ("waiting",
             MonitoringState(title=u"waiting",
                             default_value=0,
                             help=_(u"Waiting for other switches to come online"))),
            ("progressing",
             MonitoringState(title=u"progressing",
                             default_value=0,
                             help=_(u"Master election or mismatch checks in progress"))),
            ("added", MonitoringState(title=u"added", default_value=0, help=_(u"Added to stack"))),
            ("ready", MonitoringState(title=u"ready", default_value=0, help=_(u"Ready"))),
            ("sdmMismatch",
             MonitoringState(title=u"sdmMismatch",
                             default_value=1,
                             help=_(u"SDM template mismatch"))),
            ("verMismatch",
             MonitoringState(title=u"verMismatch", default_value=1,
                             help=_(u"OS version mismatch"))),
            ("featureMismatch",
             MonitoringState(title=u"featureMismatch",
                             default_value=1,
                             help=_(u"Configured feature mismatch"))),
            ("newMasterInit",
             MonitoringState(title=u"newMasterInit",
                             default_value=0,
                             help=_(u"Waiting for new master initialization"))),
            ("provisioned",
             MonitoringState(title=u"provisioned",
                             default_value=0,
                             help=_(u"Not an active member of the stack"))),
            ("invalid",
             MonitoringState(title=u"invalid",
                             default_value=2,
                             help=_(u"State machine in invalid state"))),
            ("removed",
             MonitoringState(title=u"removed", default_value=2, help=_(u"Removed from stack"))),
        ],
        optional_keys=[],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="cisco_stack",
        group=RulespecGroupCheckParametersNetworking,
        item_spec=lambda: TextAscii(title=_("Switch number"),),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_cisco_stack,
        title=lambda: _("Cisco Stack Switch Status"),
    ))
