#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    Integer,
    LevelDirection,
    Percentage,
    ServiceState,
    SimpleLevels,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _parameter_valuespec_graylog_nodes():
    return Dictionary(
        elements={
            "lb_alive": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("State when load balancer state is alive"),
                    prefill=DefaultValue(ServiceState.OK),
                ),
            ),
            "lb_throttled": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("State when load balancer state is throttled"),
                    prefill=DefaultValue(ServiceState.CRIT),
                ),
            ),
            "lb_dead": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("State when load balancer state is dead"),
                    prefill=DefaultValue(ServiceState.CRIT),
                ),
            ),
            "lc_running": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("State when life cycle state is running"),
                    prefill=DefaultValue(ServiceState.OK),
                ),
            ),
            "lc_starting": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("State when life cycle state is starting"),
                    prefill=DefaultValue(ServiceState.WARN),
                ),
            ),
            "lc_halting": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("State when life cycle state is halting"),
                    prefill=DefaultValue(ServiceState.WARN),
                ),
            ),
            "lc_paused": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("State when life cycle state is paused"),
                    prefill=DefaultValue(ServiceState.WARN),
                ),
            ),
            "lc_uninitialized": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("State when life cycle state is uninitialized"),
                    prefill=DefaultValue(ServiceState.WARN),
                ),
            ),
            "lc_failed": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("State when life cycle state is failed"),
                    prefill=DefaultValue(ServiceState.CRIT),
                ),
            ),
            "lc_throttled": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("State when life cycle state is throttled"),
                    prefill=DefaultValue(ServiceState.CRIT),
                ),
            ),
            "lc_override_lb_alive": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("State when life cycle state is override_lb_alive"),
                    prefill=DefaultValue(ServiceState.OK),
                ),
            ),
            "lc_override_lb_dead": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("State when life cycle state is override_lb_dead"),
                    prefill=DefaultValue(ServiceState.WARN),
                ),
            ),
            "lc_override_lb_throttled": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("State when life cycle state is override_lb_throttled"),
                    prefill=DefaultValue(ServiceState.WARN),
                ),
            ),
            "ps_true": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("State when index is processing"),
                    prefill=DefaultValue(ServiceState.OK),
                ),
            ),
            "ps_false": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("State when index is not processing"),
                    prefill=DefaultValue(ServiceState.CRIT),
                ),
            ),
            "input_state": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("State when input is not in state running"),
                    prefill=DefaultValue(ServiceState.WARN),
                ),
            ),
            "input_count_lower": DictElement(
                required=False,
                parameter_form=Dictionary(
                    title=Title("Total number of inputs lower level"),
                    elements={
                        "key_0": DictElement(
                            required=True,
                            parameter_form=Integer(
                                title=Title("Warning if less then"), unit_symbol="inputs"
                            ),
                        ),
                        "key_1": DictElement(
                            required=True,
                            parameter_form=Integer(
                                title=Title("Critical if less then"), unit_symbol="inputs"
                            ),
                        ),
                    },
                ),
            ),
            "input_count_upper": DictElement(
                required=False,
                parameter_form=Dictionary(
                    title=Title("Total number of inputs upper level"),
                    elements={
                        "key_0": DictElement(
                            required=True,
                            parameter_form=Integer(title=Title("Warning at"), unit_symbol="inputs"),
                        ),
                        "key_1": DictElement(
                            required=True,
                            parameter_form=Integer(
                                title=Title("Critical at"), unit_symbol="inputs"
                            ),
                        ),
                    },
                ),
            ),
            "journal_usage_limits": DictElement(
                parameter_form=SimpleLevels(
                    title=Title("Upper levels for disk journal usage"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Percentage(),
                    migrate=None,
                    prefill_fixed_levels=DefaultValue(value=(80.0, 90.0)),
                ),
            ),
        }
    )


rule_spec_graylog_nodes = CheckParameters(
    name="graylog_nodes",
    title=Title("Graylog nodes"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_valuespec_graylog_nodes,
    condition=HostAndItemCondition(item_title=Title("Node name")),
)
