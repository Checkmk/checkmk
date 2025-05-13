#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import form_specs, Label, rule_specs, Title


def _parameters_valuespec_prism_hosts() -> form_specs.Dictionary:
    return form_specs.Dictionary(
        elements={
            "system_state": form_specs.DictElement(
                parameter_form=form_specs.String(
                    title=Title("Wanted Host State"),
                    prefill=form_specs.DefaultValue("NORMAL"),
                    custom_validate=(form_specs.validators.LengthInRange(min_value=1),),
                ),
            ),
            "acropolis_connection_state": form_specs.DictElement(
                parameter_form=form_specs.BooleanChoice(
                    title=Title("Monitor Acropolis State"),
                    label=Label("Alert if Acropolis disconnects from hypervisor"),
                    prefill=form_specs.DefaultValue(True),
                ),
            ),
        },
        title=Title("States of Nutanix Host"),
    )


rule_spec_prism_hosts = rule_specs.CheckParameters(
    name="prism_hosts",
    topic=rule_specs.Topic.VIRTUALIZATION,
    parameter_form=_parameters_valuespec_prism_hosts,
    title=Title("Nutanix Host State"),
    condition=rule_specs.HostAndItemCondition(item_title=Title("Host")),
)
