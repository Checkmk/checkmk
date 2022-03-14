#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.check_parameters.websphere_mq import websphere_mq_common_elements
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Dictionary, MonitoringState, TextInput


def _parameter_valuespec_websphere_mq_channels():
    return Dictionary(
        elements=websphere_mq_common_elements()
        + [
            (
                "status",
                Dictionary(
                    title=_("Override check state based on channel state"),
                    elements=[
                        (
                            "INACTIVE",
                            MonitoringState(
                                title=_("State when channel is inactive"), default_value=2
                            ),
                        ),
                        (
                            "INITIALIZING",
                            MonitoringState(
                                title=_("State when channel is initializing"), default_value=2
                            ),
                        ),
                        (
                            "BINDING",
                            MonitoringState(
                                title=_("State when channel is binding"), default_value=2
                            ),
                        ),
                        (
                            "STARTING",
                            MonitoringState(
                                title=_("State when channel is starting"), default_value=2
                            ),
                        ),
                        (
                            "RUNNING",
                            MonitoringState(
                                title=_("State when channel is running"), default_value=0
                            ),
                        ),
                        (
                            "RETRYING",
                            MonitoringState(
                                title=_("State when channel is retrying"), default_value=2
                            ),
                        ),
                        (
                            "STOPPING",
                            MonitoringState(
                                title=_("State when channel is stopping"), default_value=2
                            ),
                        ),
                        (
                            "STOPPED",
                            MonitoringState(
                                title=_("State when channel is stopped"), default_value=1
                            ),
                        ),
                        (
                            "other",
                            MonitoringState(
                                title=_("State when channel status is unknown"), default_value=2
                            ),
                        ),
                    ],
                    optional_keys=[],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="websphere_mq_channels",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextInput(title=_("Name of channel")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_websphere_mq_channels,
        title=lambda: _("Websphere MQ Channels"),
    )
)
