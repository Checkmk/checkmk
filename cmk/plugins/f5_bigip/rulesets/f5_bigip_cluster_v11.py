#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    ServiceState,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic

# The rule used to be keyed by the config sync status code the device reports. Form spec
# element names have to be Python identifiers, so the codes are renamed to the status they
# stand for; see CONFIG_SYNC_STATES in the check plugin.
_RENAMED_KEYS: Mapping[str, str] = {
    "0": "unknown",
    "1": "syncing",
    "2": "need_manual_sync",
    "3": "in_sync",
    "4": "sync_failed",
    "5": "sync_disconnected",
    "6": "standalone",
    "7": "awaiting_initial_sync",
    "8": "incompatible_version",
    "9": "partial_sync",
}


def _migrate_config_sync_states(model: object) -> Mapping[str, int]:
    if not isinstance(model, dict):
        raise TypeError(f"Expected a mapping of config sync states, got {model!r}")
    return {_RENAMED_KEYS.get(key, key): value for key, value in model.items()}


def _parameter_form_f5_bigip_cluster_v11() -> Dictionary:
    return Dictionary(
        title=Title("Interpretation of config sync status"),
        elements={
            "unknown": DictElement(
                parameter_form=ServiceState(
                    title=Title("Unknown"),
                    prefill=DefaultValue(ServiceState.UNKNOWN),
                )
            ),
            "syncing": DictElement(
                parameter_form=ServiceState(
                    title=Title("Syncing"),
                    prefill=DefaultValue(ServiceState.OK),
                )
            ),
            "need_manual_sync": DictElement(
                parameter_form=ServiceState(
                    title=Title("Need Manual Sync"),
                    prefill=DefaultValue(ServiceState.WARN),
                )
            ),
            "in_sync": DictElement(
                parameter_form=ServiceState(
                    title=Title("In Sync"),
                    prefill=DefaultValue(ServiceState.OK),
                )
            ),
            "sync_failed": DictElement(
                parameter_form=ServiceState(
                    title=Title("Sync Failed"),
                    prefill=DefaultValue(ServiceState.CRIT),
                )
            ),
            "sync_disconnected": DictElement(
                parameter_form=ServiceState(
                    title=Title("Sync Disconnected"),
                    prefill=DefaultValue(ServiceState.CRIT),
                )
            ),
            "standalone": DictElement(
                parameter_form=ServiceState(
                    title=Title("Standalone"),
                    prefill=DefaultValue(ServiceState.CRIT),
                )
            ),
            "awaiting_initial_sync": DictElement(
                parameter_form=ServiceState(
                    title=Title("Awaiting Initial Sync"),
                    prefill=DefaultValue(ServiceState.WARN),
                )
            ),
            "incompatible_version": DictElement(
                parameter_form=ServiceState(
                    title=Title("Incompatible Version"),
                    prefill=DefaultValue(ServiceState.CRIT),
                )
            ),
            "partial_sync": DictElement(
                parameter_form=ServiceState(
                    title=Title("Partial Sync"),
                    prefill=DefaultValue(ServiceState.CRIT),
                )
            ),
        },
        migrate=_migrate_config_sync_states,
    )


rule_spec_f5_bigip_cluster_v11 = CheckParameters(
    name="f5_bigip_cluster_v11",
    topic=Topic.NETWORKING,
    parameter_form=_parameter_form_f5_bigip_cluster_v11,
    title=Title("F5 BigIP configuration sync status"),
    condition=HostCondition(),
)
