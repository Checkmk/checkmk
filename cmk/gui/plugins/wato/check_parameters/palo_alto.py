#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersNetworking,
)
from cmk.gui.valuespec import Dictionary, MonitoringState

_STATE_MAPPING_DEFAULT: Mapping[str, int] = {
    "mode_disabled": 0,
    "mode_active_active": 0,
    "mode_active_passive": 0,
    "ha_local_state_active": 0,
    "ha_local_state_passive": 0,
    "ha_local_state_active_primary": 0,
    "ha_local_state_active_secondary": 0,
    "ha_local_state_disabled": 0,
    "ha_local_state_tentative": 1,
    "ha_local_state_non_functional": 2,
    "ha_local_state_suspended": 2,
    "ha_local_state_unknown": 3,
    "ha_peer_state_active": 0,
    "ha_peer_state_passive": 0,
    "ha_peer_state_active_primary": 0,
    "ha_peer_state_active_secondary": 0,
    "ha_peer_state_disabled": 0,
    "ha_peer_state_tentative": 1,
    "ha_peer_state_non_functional": 2,
    "ha_peer_state_suspended": 2,
    "ha_peer_state_unknown": 3,
}


def _parameter_valuespec_palo_alto() -> Dictionary:
    return Dictionary(
        optional_keys=True,
        elements=[
            (
                key := "mode_disabled",
                MonitoringState(
                    title=_("State if mode is Disabled"),
                    default_value=_STATE_MAPPING_DEFAULT[key],
                ),
            ),
            (
                key := "mode_active_active",
                MonitoringState(
                    title=_("State if mode is Active-Active"),
                    default_value=_STATE_MAPPING_DEFAULT[key],
                ),
            ),
            (
                key := "mode_active_passive",
                MonitoringState(
                    title=_("State if mode is Active-Passive"),
                    default_value=_STATE_MAPPING_DEFAULT[key],
                ),
            ),
            (
                key := "ha_local_state_active",
                MonitoringState(
                    title=_("State if ha local State is Active"),
                    default_value=_STATE_MAPPING_DEFAULT[key],
                ),
            ),
            (
                key := "ha_local_state_passive",
                MonitoringState(
                    title=_("State if ha local State is Passive"),
                    default_value=_STATE_MAPPING_DEFAULT[key],
                ),
            ),
            (
                key := "ha_local_state_active_primary",
                MonitoringState(
                    title=_("State if ha local State is Active-Primary"),
                    default_value=_STATE_MAPPING_DEFAULT[key],
                ),
            ),
            (
                key := "ha_local_state_active_secondary",
                MonitoringState(
                    title=_("State if ha local State is Active-Secondary"),
                    default_value=_STATE_MAPPING_DEFAULT[key],
                ),
            ),
            (
                key := "ha_local_state_disabled",
                MonitoringState(
                    title=_("State if ha local State is Disabled"),
                    default_value=_STATE_MAPPING_DEFAULT[key],
                ),
            ),
            (
                key := "ha_local_state_tentative",
                MonitoringState(
                    title=_("State if ha local State is Tentative"),
                    default_value=_STATE_MAPPING_DEFAULT[key],
                ),
            ),
            (
                key := "ha_local_state_non_functional",
                MonitoringState(
                    title=_("State if ha local State is Non-Functional"),
                    default_value=_STATE_MAPPING_DEFAULT[key],
                ),
            ),
            (
                key := "ha_local_state_suspended",
                MonitoringState(
                    title=_("State if ha local State is Suspended"),
                    default_value=_STATE_MAPPING_DEFAULT[key],
                ),
            ),
            (
                key := "ha_local_state_unknown",
                MonitoringState(
                    title=_("State if ha local State is Unknown"),
                    default_value=_STATE_MAPPING_DEFAULT[key],
                ),
            ),
            (
                key := "ha_peer_state_active",
                MonitoringState(
                    title=_("State if ha peer State is Active"),
                    default_value=_STATE_MAPPING_DEFAULT[key],
                ),
            ),
            (
                key := "ha_peer_state_passive",
                MonitoringState(
                    title=_("State if ha peer State is Passive"),
                    default_value=_STATE_MAPPING_DEFAULT[key],
                ),
            ),
            (
                key := "ha_peer_state_active_primary",
                MonitoringState(
                    title=_("State if ha peer State is Active-Primary"),
                    default_value=_STATE_MAPPING_DEFAULT[key],
                ),
            ),
            (
                key := "ha_peer_state_active_secondary",
                MonitoringState(
                    title=_("State if ha peer State is Active-Secondary"),
                    default_value=_STATE_MAPPING_DEFAULT[key],
                ),
            ),
            (
                key := "ha_peer_state_disabled",
                MonitoringState(
                    title=_("State if ha peer State is Disabled"),
                    default_value=_STATE_MAPPING_DEFAULT[key],
                ),
            ),
            (
                key := "ha_peer_state_tentative",
                MonitoringState(
                    title=_("State if ha peer State is Tentative"),
                    default_value=_STATE_MAPPING_DEFAULT[key],
                ),
            ),
            (
                key := "ha_peer_state_non_functional",
                MonitoringState(
                    title=_("State if ha peer State is Non-Functional"),
                    default_value=_STATE_MAPPING_DEFAULT[key],
                ),
            ),
            (
                key := "ha_peer_state_suspended",
                MonitoringState(
                    title=_("State if ha peer State is Suspended"),
                    default_value=_STATE_MAPPING_DEFAULT[key],
                ),
            ),
            (
                key := "ha_peer_state_unknown",
                MonitoringState(
                    title=_("State if ha peer State is Unknown"),
                    default_value=_STATE_MAPPING_DEFAULT[key],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="palo_alto",
        group=RulespecGroupCheckParametersNetworking,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_palo_alto,
        title=lambda: _("Palo Alto State"),
    )
)
