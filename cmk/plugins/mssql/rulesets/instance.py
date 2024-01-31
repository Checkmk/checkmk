#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Localizable
from cmk.rulesets.v1.form_specs.basic import ServiceState, Text
from cmk.rulesets.v1.form_specs.composed import DictElement, Dictionary
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _parameter_form_mssql_instance() -> Dictionary:
    return Dictionary(
        elements={
            "map_connection_state": DictElement(
                parameter_form=ServiceState(
                    title=Localizable("Connection status"), prefill_value=ServiceState.CRIT
                )
            ),
        }
    )


rule_spec_mssql_instance = CheckParameters(
    name="mssql_instance",
    title=Localizable("MSSQL Instance"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_mssql_instance,
    condition=HostAndItemCondition(item_form=Text(title=Localizable("Instance identifier"))),
)
