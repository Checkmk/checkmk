#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"

from collections.abc import Mapping

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    DictGroup,
    Dictionary,
    Integer,
    LevelDirection,
    ServiceState,
    SimpleLevels,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic

NODE_STATUS_DEFAULT = {
    "online": 0,
    "offline": 1,
    "unknown": 1,
}

SUBSCRIPTION_STATUS_DEFAULT = {
    "new": 0,
    "active": 0,
    "notfound": 1,
    "invalid": 1,
    "expired": 2,
    "suspended": 1,
}


def _migrate_ruleset(value: object) -> Mapping[str, object]:
    if not isinstance(value, dict):
        raise TypeError(value)

    if not value.get("required_node_status"):
        value.pop("required_node_status", None)

    if not value.get("required_subscription_status"):
        value.pop("required_subscription_status", None)

    return value


def _migrate_required_status(value: object, default_status: Mapping[str, int]) -> Mapping[str, int]:
    if not value:
        return {}

    if isinstance(value, dict):
        return value

    if isinstance(value, str):
        req_status = value.lower()
        if req_status not in default_status:
            return default_status
        return {
            key: 0 if key == req_status else (2 if key == "expired" else 1)
            for key in default_status
        }

    return default_status


def _parameter_rulespec_proxmox_ve_node_info():
    return Dictionary(
        migrate=_migrate_ruleset,
        elements={
            "required_node_status": DictElement(
                required=False,
                parameter_form=Dictionary(
                    migrate=lambda v: _migrate_required_status(v, NODE_STATUS_DEFAULT),
                    title=Title("Node Status"),
                    elements={
                        "active": DictElement(
                            group=DictGroup(),
                            required=True,
                            parameter_form=ServiceState(
                                title=Title("Active"),
                                prefill=DefaultValue(ServiceState.OK),
                            ),
                        ),
                        "offline": DictElement(
                            group=DictGroup(),
                            required=True,
                            parameter_form=ServiceState(
                                title=Title("Offline"),
                                prefill=DefaultValue(ServiceState.WARN),
                            ),
                        ),
                        "unknown": DictElement(
                            group=DictGroup(),
                            required=True,
                            parameter_form=ServiceState(
                                title=Title("Unknown"),
                                prefill=DefaultValue(ServiceState.WARN),
                            ),
                        ),
                    },
                ),
            ),
            "required_subscription_status": DictElement(
                required=False,
                parameter_form=Dictionary(
                    migrate=lambda v: _migrate_required_status(v, SUBSCRIPTION_STATUS_DEFAULT),
                    title=Title("Subscription Status"),
                    elements={
                        "new": DictElement(
                            group=DictGroup(),
                            required=True,
                            parameter_form=ServiceState(
                                title=Title("New"),
                                prefill=DefaultValue(ServiceState.OK),
                            ),
                        ),
                        "active": DictElement(
                            group=DictGroup(),
                            required=True,
                            parameter_form=ServiceState(
                                title=Title("Active"),
                                prefill=DefaultValue(ServiceState.OK),
                            ),
                        ),
                        "notfound": DictElement(
                            group=DictGroup(),
                            required=True,
                            parameter_form=ServiceState(
                                title=Title("Not Found"),
                                prefill=DefaultValue(ServiceState.WARN),
                            ),
                        ),
                        "invalid": DictElement(
                            group=DictGroup(),
                            required=True,
                            parameter_form=ServiceState(
                                title=Title("Invalid"),
                                prefill=DefaultValue(ServiceState.WARN),
                            ),
                        ),
                        "expired": DictElement(
                            group=DictGroup(),
                            required=True,
                            parameter_form=ServiceState(
                                title=Title("Expired"),
                                prefill=DefaultValue(ServiceState.CRIT),
                            ),
                        ),
                        "suspended": DictElement(
                            group=DictGroup(),
                            required=True,
                            parameter_form=ServiceState(
                                title=Title("Suspended"),
                                prefill=DefaultValue(ServiceState.WARN),
                            ),
                        ),
                    },
                ),
            ),
            "subscription_expiration_days_levels": DictElement(
                required=True,
                parameter_form=SimpleLevels(
                    title=Title("Days until Subscription Expiration"),
                    form_spec_template=Integer(),
                    level_direction=LevelDirection.LOWER,
                    prefill_fixed_levels=DefaultValue((30, 7)),
                ),
            ),
        },
    )


rule_spec_proxmox_ve_node_info = CheckParameters(
    name="proxmox_ve_node_info",
    topic=Topic.VIRTUALIZATION,
    parameter_form=_parameter_rulespec_proxmox_ve_node_info,
    title=Title("Proxmox VE Node Info"),
    condition=HostCondition(),
)
