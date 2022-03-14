#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersNetworking,
)
from cmk.gui.valuespec import Dictionary, MonitoringState, TextInput


def _parameter_valuespec_threepar_ports():
    return Dictionary(
        elements=[
            ("1_link", MonitoringState(title=_("Link State: CONFIG_WAIT"), default_value=1)),
            ("2_link", MonitoringState(title=_("Link State: ALPA_WAIT"), default_value=1)),
            ("3_link", MonitoringState(title=_("Link State: LOGIN_WAIT"), default_value=1)),
            ("4_link", MonitoringState(title=_("Link State: READY"), default_value=0)),
            ("5_link", MonitoringState(title=_("Link State: LOSS_SYNC"), default_value=2)),
            ("6_link", MonitoringState(title=_("Link State: ERROR_STATE"), default_value=2)),
            ("7_link", MonitoringState(title=_("Link State: XXX"), default_value=1)),
            ("8_link", MonitoringState(title=_("Link State: NOPARTICIPATE"), default_value=0)),
            ("9_link", MonitoringState(title=_("Link State: COREDUMP"), default_value=1)),
            ("10_link", MonitoringState(title=_("Link State: OFFLINE"), default_value=1)),
            ("11_link", MonitoringState(title=_("Link State: FWDEAD"), default_value=1)),
            ("12_link", MonitoringState(title=_("Link State: IDLE_FOR_RESET"), default_value=1)),
            ("13_link", MonitoringState(title=_("Link State: DHCP_IN_PROGESS"), default_value=1)),
            ("14_link", MonitoringState(title=_("Link State: PENDING_RESET"), default_value=1)),
            ("1_fail", MonitoringState(title=_("Failover State: NONE"), default_value=0)),
            (
                "2_fail",
                MonitoringState(title=_("Failover State: FAILOVER_PENDING"), default_value=2),
            ),
            ("3_fail", MonitoringState(title=_("Failover State: FAILED_OVER"), default_value=2)),
            ("4_fail", MonitoringState(title=_("Failover State: ACTIVE"), default_value=2)),
            ("5_fail", MonitoringState(title=_("Failover State: ACTIVE_DOWN"), default_value=2)),
            ("6_fail", MonitoringState(title=_("Failover State: ACTIVE_FAILED"), default_value=2)),
            (
                "7_fail",
                MonitoringState(title=_("Failover State: FAILBACK_PENDING"), default_value=1),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="threepar_ports",
        group=RulespecGroupCheckParametersNetworking,
        item_spec=lambda: TextInput(title=_("Port"), help=_("The Port Description")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_threepar_ports,
        title=lambda: _("3PAR Ports"),
    )
)
