#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from enum import Enum
from typing import cast

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    ServiceState,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


class HAProxyFrontendStatus(Enum):
    OPEN = "OPEN"
    STOP = "STOP"


class HAProxyServerStatus(Enum):
    """
    https://www.haproxy.com/documentation/haproxy-configuration-manual/2-5r1/management/

    Notes:
        * MAINT (resolution) and MAINT (via) are listed explicitly as states in the linked
        documentation, therefore including them in the enum instead of treating them as a partial
        status.
    """

    UP = "UP"
    DOWN = "DOWN"
    NOLB = "NOLB"
    MAINT = "MAINT"
    MAINT_RES = "MAINT (resolution)"
    MAINT_VIA = "MAINT (via)"
    DRAIN = "DRAIN"
    NO_CHECK = "no check"


FRONTEND_STATES = {
    HAProxyFrontendStatus.OPEN: ServiceState.OK,
    HAProxyFrontendStatus.STOP: ServiceState.CRIT,
}
SERVER_STATES = {
    HAProxyServerStatus.UP: ServiceState.OK,
    HAProxyServerStatus.DOWN: ServiceState.CRIT,
    HAProxyServerStatus.NOLB: ServiceState.CRIT,
    HAProxyServerStatus.MAINT: ServiceState.CRIT,
    HAProxyServerStatus.MAINT_VIA: ServiceState.WARN,
    HAProxyServerStatus.MAINT_RES: ServiceState.WARN,
    HAProxyServerStatus.DRAIN: ServiceState.CRIT,
    HAProxyServerStatus.NO_CHECK: ServiceState.CRIT,
}


def _migrate_dict_keys(
    value: object, pool: type[HAProxyServerStatus | HAProxyFrontendStatus]
) -> dict[str, ServiceState]:
    # FYI: Form specs require that dictionary names are valid Python identifiers
    value = cast(dict[str, ServiceState], value)

    def _transform_key(old_key: str) -> str:
        if old_key in pool:
            return pool(old_key).name

        return str(getattr(pool, old_key).name)

    return {_transform_key(key): _value for key, _value in value.items()}


def _parameter_formspec_haproxy_frontend() -> Dictionary:
    return Dictionary(
        migrate=lambda x: _migrate_dict_keys(value=x, pool=HAProxyFrontendStatus),
        title=Title("Translation of HAProxy state to monitoring state"),
        help_text=Help(
            "Define a direct translation of the possible states of the HAProxy frontend "
            "to monitoring states, i.e. to the result of the check. This overwrites the default "
            "mapping used by the check."
        ),
        elements={
            state.name: DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("Monitoring state of HAProxy frontend is %s") % state.value,
                    prefill=DefaultValue(default),
                ),
            )
            for state, default in FRONTEND_STATES.items()
        },
    )


rule_spec_haproxy_frontend = CheckParameters(
    name="haproxy_frontend",
    title=Title("HAproxy Frontend State"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_formspec_haproxy_frontend,
    condition=HostAndItemCondition(item_title=Title("Name of HAproxy Frontend")),
)


def _parameter_formspec_haproxy_server() -> Dictionary:
    return Dictionary(
        migrate=lambda x: _migrate_dict_keys(value=x, pool=HAProxyServerStatus),
        title=Title("Translation of HAProxy state to monitoring state"),
        help_text=Help(
            "Define a direct translation of the possible states of the HAProxy server "
            "to monitoring states, i.e. to the result of the check. This overwrites the default "
            "mapping used by the check."
        ),
        elements={
            state.name: DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("Monitoring state if HAProxy server is '%s'") % state.value,
                    prefill=DefaultValue(default),
                ),
            )
            for state, default in SERVER_STATES.items()
        },
    )


rule_spec_haproxy_server = CheckParameters(
    name="haproxy_server",
    title=Title("HAproxy Server State"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_formspec_haproxy_server,
    condition=HostAndItemCondition(item_title=Title("Name of HAproxy Server")),
)
