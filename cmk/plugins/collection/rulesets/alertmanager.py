#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from enum import StrEnum

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    DictElement,
    Dictionary,
    FixedValue,
    Integer,
    List,
    ServiceState,
    String,
    validators,
)
from cmk.rulesets.v1.rule_specs import (
    CheckParameters,
    DiscoveryParameters,
    HostAndItemCondition,
    HostCondition,
    Topic,
)


class ServiceNumber(StrEnum):
    MULTIPLE = "multiple_services"
    ONE = "one_service"


# introduced in version 2.3
def migrate_dropdown_ident(raw_value: object) -> tuple[str, object]:
    if not isinstance(raw_value, tuple):
        raise TypeError("Invalid type. group_services should be a tuple.")

    ident, dropdown_element = raw_value

    if isinstance(ident, str):
        return ident, dropdown_element

    if ident:
        return ("multiple_services", dropdown_element)

    return ("one_service", None)


def _discovery_parameters_form_alertmanager():
    return Dictionary(
        title=Title("Alertmanager discovery"),
        elements={
            "group_services": DictElement(
                parameter_form=CascadingSingleChoice(
                    title=Title("Service creation"),
                    elements=[
                        CascadingSingleChoiceElement(
                            name=ServiceNumber.MULTIPLE,
                            title=Title("Create services for alert rule groups"),
                            parameter_form=Dictionary(
                                elements={
                                    "min_amount_rules": DictElement(
                                        parameter_form=Integer(
                                            title=Title(
                                                "Minimum amount of alert rules in a group to create a group service"
                                            ),
                                            custom_validate=(
                                                validators.NumberInRange(min_value=1),
                                            ),
                                            prefill=DefaultValue(3),
                                            help_text=Help(
                                                "Below the specified value alert rules will be monitored as a"
                                                "single service."
                                            ),
                                        ),
                                        required=True,
                                    ),
                                    "no_group_services": DictElement(
                                        parameter_form=List(
                                            element_template=String(),
                                            title=Title(
                                                "Don't create a group service for the following groups"
                                            ),
                                        ),
                                        required=True,
                                    ),
                                },
                            ),
                        ),
                        CascadingSingleChoiceElement(
                            name=ServiceNumber.ONE,
                            title=Title("Create one service per alert rule"),
                            parameter_form=FixedValue(value=None),
                        ),
                    ],
                    migrate=migrate_dropdown_ident,
                ),
                required=True,
            ),
            "summary_service": DictElement(
                parameter_form=FixedValue(
                    value=True,
                    title=Title("Create a summary service for all alert rules"),
                ),
            ),
        },
    )


rule_spec_discovery_alertmanager = DiscoveryParameters(
    topic=Topic.GENERAL,
    name="discovery_alertmanager",
    parameter_form=_discovery_parameters_form_alertmanager,
    title=Title("Alertmanager discovery"),
)


# introduced in version 2.3
def migrate_non_identifier_key(raw_value: object) -> Mapping[str, object]:
    if not isinstance(raw_value, dict):
        raise TypeError("Invalid type. map should be a dict.")

    if "n/a" in raw_value:
        raw_value["not_applicable"] = raw_value.pop("n/a")

    return raw_value


def form_alert_remapping():
    return List(
        element_template=Dictionary(
            elements={
                "rule_names": DictElement(
                    parameter_form=List(
                        element_template=String(prefill=DefaultValue("Watchdog")),
                        title=Title("Alert rule names"),
                        help_text=Help("A list of rule names as defined in Alertmanager."),
                    ),
                    required=True,
                ),
                "map": DictElement(
                    parameter_form=Dictionary(
                        title=Title("States"),
                        elements={
                            "inactive": DictElement(
                                parameter_form=ServiceState(
                                    title=Title("inactive"), prefill=DefaultValue(2)
                                ),
                                required=True,
                            ),
                            "pending": DictElement(
                                parameter_form=ServiceState(
                                    title=Title("pending"), prefill=DefaultValue(2)
                                ),
                                required=True,
                            ),
                            "firing": DictElement(
                                parameter_form=ServiceState(
                                    title=Title("firing"), prefill=DefaultValue(0)
                                ),
                                required=True,
                            ),
                            "none": DictElement(
                                parameter_form=ServiceState(
                                    title=Title("none"), prefill=DefaultValue(2)
                                ),
                                required=True,
                            ),
                            "not_applicable": DictElement(
                                parameter_form=ServiceState(
                                    title=Title("n/a"), prefill=DefaultValue(2)
                                ),
                                required=True,
                            ),
                        },
                        migrate=migrate_non_identifier_key,
                    ),
                    required=True,
                ),
            },
        ),
        title=Title("Remap alert rule states"),
        help_text=Help("Configure the monitoring state for Alertmanager rules."),
        custom_validate=(validators.LengthInRange(min_value=1),),
    )


def _check_parameters_form_alertmanager():
    return Dictionary(
        title=Title("Alert manager rule state"),
        elements={
            "alert_remapping": DictElement(parameter_form=form_alert_remapping()),
        },
    )


rule_spec_alertmanager_rule_state = CheckParameters(
    name="alertmanager_rule_state",
    topic=Topic.APPLICATIONS,
    parameter_form=_check_parameters_form_alertmanager,
    title=Title("Alertmanager rule states"),
    condition=HostAndItemCondition(
        item_title=Title("Name of Alert rules/Alert rule groups"),
    ),
)

rule_spec_alertmanager_rule_state_summary = CheckParameters(
    name="alertmanager_rule_state_summary",
    topic=Topic.APPLICATIONS,
    parameter_form=_check_parameters_form_alertmanager,
    title=Title("Alertmanager rule states (Summary)"),
    condition=HostCondition(),
)
