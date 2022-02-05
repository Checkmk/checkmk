#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersStorage,
)
from cmk.gui.valuespec import Dictionary, MonitoringState, TextInput


def _item_spec_ibm_svc_mdisk():
    return TextInput(
        title=_("IBM SVC disk"),
        help=_("Name of the disk, e.g. mdisk0"),
    )


def _parameter_valuespec_ibm_svc_mdisk():
    return Dictionary(
        optional_keys=False,
        elements=[
            (
                "online_state",
                MonitoringState(
                    title=_("Resulting state if disk is online"),
                    default_value=0,
                ),
            ),
            (
                "degraded_state",
                MonitoringState(
                    title=_("Resulting state if disk is degraded"),
                    default_value=1,
                ),
            ),
            (
                "offline_state",
                MonitoringState(
                    title=_("Resulting state if disk is offline"),
                    default_value=2,
                ),
            ),
            (
                "excluded_state",
                MonitoringState(
                    title=_("Resulting state if disk is excluded"),
                    default_value=2,
                ),
            ),
            (
                "managed_mode",
                MonitoringState(
                    title=_("Resulting state if disk is in managed mode"),
                    default_value=0,
                ),
            ),
            (
                "array_mode",
                MonitoringState(
                    title=_("Resulting state if disk is in array mode"),
                    default_value=0,
                ),
            ),
            (
                "image_mode",
                MonitoringState(
                    title=_("Resulting state if disk is in image mode"),
                    default_value=0,
                ),
            ),
            (
                "unmanaged_mode",
                MonitoringState(
                    title=_("Resulting state if disk is in unmanaged mode"),
                    default_value=1,
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="ibm_svc_mdisk",
        group=RulespecGroupCheckParametersStorage,
        item_spec=_item_spec_ibm_svc_mdisk,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_ibm_svc_mdisk,
        title=lambda: _("IBM SVC Disk"),
    )
)
