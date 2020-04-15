#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Transform,
    Dictionary,
    Integer,
    Tuple,
)
from cmk.gui.plugins.wato import (
    RulespecGroupCheckParametersApplications,
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
)


def _transform_asa_svc_sessions(p):
    if isinstance(p, tuple):
        return {"levels_svc": p}
    return p


def _parameter_valuespec_asa_svc_sessions():
    return Transform(
        Dictionary(title=_("Number of active sessions"),
                   elements=[(
                       "levels_%s" % vpn_type.lower(),
                       Tuple(
                           title="Active %s sessions" % vpn_type,
                           elements=[
                               Integer(
                                   title=_("Warning at"),
                                   unit=_("sessions"),
                               ),
                               Integer(
                                   title=_("Critical at"),
                                   unit=_("sessions"),
                               ),
                           ],
                       ),
                   ) for vpn_type in ["SVC", "WebVPN", "IPsec"]]),
        forth=_transform_asa_svc_sessions,
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="asa_svc_sessions",
        group=RulespecGroupCheckParametersApplications,
        parameter_valuespec=_parameter_valuespec_asa_svc_sessions,
        title=lambda: _("Cisco SVC/WebVPN/IPsec Sessions"),
    ))
