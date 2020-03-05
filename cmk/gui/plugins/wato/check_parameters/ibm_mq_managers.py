#!/usr/bin/env python
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
    RulespecGroupCheckParametersApplications,
)

from cmk.gui.plugins.wato.check_parameters.ibm_mq_plugin import ibm_mq_version


def _parameter_valuespec_ibm_mq_managers():
    return Dictionary(elements=[
        ("status",
         Dictionary(
             title=_('Override check state based on queue manager state'),
             elements=[
                 ("STARTING", MonitoringState(title=_("When STARTING"), default_value=0)),
                 ("RUNNING", MonitoringState(title=_("When RUNNING"), default_value=0)),
                 ("RUNNING AS STANDBY",
                  MonitoringState(title=_("When RUNNING AS STANDBY"), default_value=0)),
                 ("RUNNING ELSEWHERE",
                  MonitoringState(title=_("When RUNNING ELSEWHERE"), default_value=0)),
                 ("QUIESCING", MonitoringState(title=_("When QUIESCING"), default_value=0)),
                 ("ENDING IMMEDIATELY",
                  MonitoringState(title=_("When ENDING IMMEDIATELY"), default_value=0)),
                 ("ENDING PREEMPTIVELY",
                  MonitoringState(title=_("When ENDING PREEMPTIVELY"), default_value=0)),
                 ("ENDING PRE-EMPTIVELY",
                  MonitoringState(title=_("When ENDING PRE-EMPTIVELY"), default_value=0)),
                 ("ENDED NORMALLY", MonitoringState(title=_("When ENDED NORMALLY"),
                                                    default_value=0)),
                 ("ENDED IMMEDIATELY",
                  MonitoringState(title=_("When ENDED IMMEDIATELY"), default_value=0)),
                 ("ENDED UNEXPECTEDLY",
                  MonitoringState(title=_("When UNEXPECTEDLY"), default_value=2)),
                 ("ENDED PREEMPTIVELY",
                  MonitoringState(title=_("When ENDED PREEMPTIVELY"), default_value=2)),
                 ("ENDED PRE-EMPTIVELY",
                  MonitoringState(title=_("When ENDED PRE-EMPTIVELY"), default_value=2)),
                 ("NOT AVAILABLE", MonitoringState(title=_("When NOT AVAILABLE"), default_value=0)),
                 ("STATUS NOT AVAILABLE",
                  MonitoringState(title=_("When STATUS NOT AVAILABLE"), default_value=0)),
             ],
             optional_keys=[])),
    ] + ibm_mq_version(),)


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="ibm_mq_managers",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextAscii(title=_("Name of Queue Manager")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_ibm_mq_managers,
        title=lambda: _("IBM MQ Managers"),
    ))
