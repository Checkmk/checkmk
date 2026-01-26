#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Literal

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    ServiceState,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic

DEFAULT_STATUS_TO_STATE_MAPPING: dict[str, Literal[0, 1, 2, 3]] = {
    "created": ServiceState.CRIT,
    "running": ServiceState.OK,
    "paused": ServiceState.CRIT,
    "restarting": ServiceState.CRIT,
    "removing": ServiceState.CRIT,
    "exited_with_zero": ServiceState.OK,
    "exited_with_non_zero": ServiceState.CRIT,
    "dead": ServiceState.CRIT,
}


def podman_container_status() -> Dictionary:
    return Dictionary(
        elements={
            status: DictElement(
                parameter_form=ServiceState(
                    title=Title(  # astrein: disable=localization-checker
                        status.capitalize().replace("_", " ")
                    ),
                    prefill=DefaultValue(state),
                )
            )
            for status, state in DEFAULT_STATUS_TO_STATE_MAPPING.items()
        }
    )


rule_spec_podman_container_status = CheckParameters(
    name="podman_container_status",
    title=Title("Podman container status"),
    topic=Topic.APPLICATIONS,
    parameter_form=podman_container_status,
    condition=HostCondition(),
)
