#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from enum import StrEnum

from cmk.rulesets.v1 import Localizable, validators
from cmk.rulesets.v1.form_specs import (
    CascadingDropdown,
    CascadingDropdownElement,
    DictElement,
    Dictionary,
    FixedValue,
    Integer,
    List,
    Migrate,
    ServiceState,
    TextInput,
)
from cmk.rulesets.v1.rule_specs import (
    CheckParameterRuleSpecWithItem,
    CheckParameterRuleSpecWithoutItem,
    RuleEvalType,
    ServiceDiscoveryRuleSpec,
    Topic,
)


class ServiceNumber(StrEnum):
    MULTIPLE = "multiple_services"
    ONE = "one_service"


# introduced in version 2.3
def migrate_dropdown_ident(raw_value: object) -> tuple[str, object] | None:
    if raw_value is None:
        return raw_value

    if not isinstance(raw_value, tuple):
        raise TypeError("Invalid type. group_services should be a tuple.")

    ident, dropdown_element = raw_value

    if not isinstance(ident, bool):
        return raw_value

    if ident:
        return ("multiple_services", dropdown_element)

    return ("one_service", None)


def _discovery_parameters_form_alertmanager():
    return Dictionary(
        title=Localizable("Alertmanager discovery"),
        elements={
            "group_services": DictElement(
                parameter_form=CascadingDropdown(
                    title=Localizable("Service creation"),
                    elements=[
                        CascadingDropdownElement(
                            name=ServiceNumber.MULTIPLE,
                            title=Localizable("Create services for alert rule groups"),
                            parameter_form=Dictionary(
                                elements={
                                    "min_amount_rules": DictElement(
                                        parameter_form=Integer(
                                            title=Localizable(
                                                "Minimum amount of alert rules in a group to create a group service"
                                            ),
                                            custom_validate=validators.InRange(min_value=1),
                                            prefill_value=3,
                                            help_text=Localizable(
                                                "Below the specified value alert rules will be monitored as a"
                                                "single service."
                                            ),
                                        ),
                                        required=True,
                                    ),
                                    "no_group_services": DictElement(
                                        parameter_form=List(
                                            parameter_form=TextInput(),
                                            title=Localizable(
                                                "Don't create a group service for the following groups"
                                            ),
                                        ),
                                        required=True,
                                    ),
                                },
                            ),
                        ),
                        CascadingDropdownElement(
                            name=ServiceNumber.ONE,
                            title=Localizable("Create one service per alert rule"),
                            parameter_form=FixedValue(value=None),
                        ),
                    ],
                    transform=Migrate(raw_to_form=migrate_dropdown_ident),
                ),
                required=True,
            ),
            "summary_service": DictElement(
                parameter_form=FixedValue(
                    value=True,
                    title=Localizable("Create a summary service for all alert rules"),
                ),
            ),
        },
    )


rule_spec_discovery_alertmanager = ServiceDiscoveryRuleSpec(
    topic=Topic.GENERAL,
    eval_type=RuleEvalType.MERGE,
    name="discovery_alertmanager",
    parameter_form=_discovery_parameters_form_alertmanager,
    title=Localizable("Alertmanager discovery"),
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
        parameter_form=Dictionary(
            elements={
                "rule_names": DictElement(
                    parameter_form=List(
                        parameter_form=TextInput(),
                        title=Localizable("Alert rule names"),
                        help_text=Localizable("A list of rule names as defined in Alertmanager."),
                    ),
                    required=True,
                ),
                "map": DictElement(
                    parameter_form=Dictionary(
                        title=Localizable("States"),
                        elements={
                            "inactive": DictElement(
                                parameter_form=ServiceState(title=Localizable("inactive")),
                                required=True,
                            ),
                            "pending": DictElement(
                                parameter_form=ServiceState(title=Localizable("pending")),
                                required=True,
                            ),
                            "firing": DictElement(
                                parameter_form=ServiceState(title=Localizable("firing")),
                                required=True,
                            ),
                            "none": DictElement(
                                parameter_form=ServiceState(title=Localizable("none")),
                                required=True,
                            ),
                            "not_applicable": DictElement(
                                parameter_form=ServiceState(title=Localizable("n/a")),
                                required=True,
                            ),
                        },
                        transform=Migrate(migrate_non_identifier_key),
                    ),
                    required=True,
                ),
            },
        ),
        title=Localizable("Remap alert rule states"),
        help_text=Localizable("Configure the monitoring state for Alertmanager rules."),
        custom_validate=validators.DisallowEmpty(),
        prefill_value=[
            {
                "map": {
                    "inactive": 2,
                    "pending": 2,
                    "firing": 0,
                    "none": 2,
                    "not_applicable": 2,
                },
                "rule_names": ["Watchdog"],
            }
        ],
    )


def _check_parameters_form_alertmanager():
    return Dictionary(
        title=Localizable("Alert manager rule state"),
        elements={
            "alert_remapping": DictElement(parameter_form=form_alert_remapping()),
        },
    )


rule_spec_alertmanager_rule_state = CheckParameterRuleSpecWithItem(
    name="alertmanager_rule_state",
    topic=Topic.APPLICATIONS,
    item_form=TextInput(
        title=Localizable("Name of Alert rules/Alert rule groups"),
        custom_validate=validators.DisallowEmpty(),
    ),
    parameter_form=_check_parameters_form_alertmanager,
    title=Localizable("Alertmanager rule states"),
)

rule_spec_alertmanager_rule_state_summary = CheckParameterRuleSpecWithoutItem(
    name="alertmanager_rule_state_summary",
    topic=Topic.APPLICATIONS,
    parameter_form=_check_parameters_form_alertmanager,
    title=Localizable("Alertmanager rule states (Summary)"),
)
