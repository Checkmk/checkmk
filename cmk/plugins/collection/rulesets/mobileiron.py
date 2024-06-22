#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.rulesets.v1 import Help, Label, Message, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    List,
    MatchingScope,
    migrate_to_password,
    migrate_to_proxy,
    Password,
    Proxy,
    RegularExpression,
    SingleChoice,
    SingleChoiceElement,
    String,
)
from cmk.rulesets.v1.form_specs.validators import LengthInRange, ValidationError
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic


def _validate_regex_choices(value: Mapping[str, object]) -> None:
    """At least one device type should be monitored."""

    if not {"android_regex", "ios_regex", "other_regex"}.intersection(value):
        raise ValidationError(
            Message(
                "Please activate the monitoring of at least one device type: Android, iOS or other devices"
            ),
        )


def _migrate(value: object) -> Mapping[str, object]:
    if not isinstance(value, dict):
        raise TypeError(value)

    if "key-fields" in value:
        fields = value.pop("key-fields")
        value["key_fields"] = f"{fields[0]}_{fields[1]}" if len(fields) == 2 else fields[0]

    if "android-regex" in value:
        value["android_regex"] = value.pop("android-regex")
    if "ios-regex" in value:
        value["ios_regex"] = value.pop("ios-regex")
    if "other-regex" in value:
        value["other_regex"] = value.pop("other-regex")

    return value


def _parameter_form_special_agents_mobileiron() -> Dictionary:
    return Dictionary(
        help_text=Help(
            "Requests data from the API of IvantiNeurons for MDM (formerly MobileIron Cloud) and outputs a piggyback host per returned device."
        ),
        elements={
            "username": DictElement(
                parameter_form=String(
                    title=Title("Username"),
                    custom_validate=(LengthInRange(min_value=1),),
                ),
                required=True,
            ),
            "password": DictElement(
                parameter_form=Password(
                    title=Title("Password"),
                    custom_validate=(LengthInRange(min_value=1),),
                    migrate=migrate_to_password,
                ),
                required=True,
            ),
            "proxy": DictElement(parameter_form=Proxy(migrate=migrate_to_proxy), required=False),
            "partition": DictElement(
                parameter_form=List(
                    element_template=String(macro_support=True),
                    title=Title("Retrieve information about the following partitions"),
                    custom_validate=(LengthInRange(min_value=1),),
                ),
                required=True,
            ),
            "key_fields": DictElement(
                parameter_form=SingleChoice(
                    title=Title("Field(s) to use as a hostname key"),
                    elements=[
                        SingleChoiceElement(name="serialNumber", title=Title("serialNumber")),
                        SingleChoiceElement(name="emailAddress", title=Title("emailAddress")),
                        SingleChoiceElement(
                            name="emailAddress_serialNumber",
                            title=Title("emailAddress and serialNumber"),
                        ),
                        SingleChoiceElement(
                            name="deviceModel_serialNumber",
                            title=Title("deviceModel and serialNumber"),
                        ),
                        SingleChoiceElement(name="uid", title=Title("uid")),
                        SingleChoiceElement(
                            name="uid_serialNumber", title=Title("uid and serialNumber")
                        ),
                        SingleChoiceElement(name="guid", title=Title("guid")),
                    ],
                    help_text=Help("Compound fields will be joined with a '-' symbol."),
                    prefill=DefaultValue("deviceModel_serialNumber"),
                ),
                required=True,
            ),
            "android_regex": DictElement(
                parameter_form=List(
                    element_template=RegularExpression(
                        title=Title("Pattern"),
                        predefined_help_text=MatchingScope.INFIX,
                        custom_validate=(LengthInRange(min_value=1),),
                        prefill=DefaultValue(".*"),
                    ),
                    title=Title("Monitor Android devices"),
                    help_text=Help(
                        "You can specify a list of regex patterns for android host names. "
                        "Several patterns can be provided. "
                        "Only those that match any of the patterns will be monitored. "
                        "By default all host names are accepted"
                    ),
                    add_element_label=Label("Add new pattern"),
                    custom_validate=(LengthInRange(min_value=1),),
                ),
                required=False,
            ),
            "ios_regex": DictElement(
                parameter_form=List(
                    element_template=RegularExpression(
                        title=Title("Pattern"),
                        predefined_help_text=MatchingScope.INFIX,
                        custom_validate=(LengthInRange(min_value=1),),
                        prefill=DefaultValue(".*"),
                    ),
                    title=Title("Monitor iOS devices"),
                    help_text=Help(
                        "You can specify a list of regex patterns for iOS host names. "
                        "Several patterns can be provided. "
                        "Only those that match any of the patterns will be monitored. "
                        "By default all host names are accepted"
                    ),
                    add_element_label=Label("Add new pattern"),
                    custom_validate=(LengthInRange(min_value=1),),
                ),
                required=False,
            ),
            "other_regex": DictElement(
                parameter_form=List(
                    element_template=RegularExpression(
                        title=Title("Pattern"),
                        predefined_help_text=MatchingScope.INFIX,
                        custom_validate=(LengthInRange(min_value=1),),
                        prefill=DefaultValue(".*"),
                    ),
                    title=Title("Monitor other than Android or iOS devices"),
                    help_text=Help(
                        "You can specify a list of regex patterns for other host names "
                        "which are not android and not iOS. "
                        "Several patterns can be provided. "
                        "Only those that match any of the patterns will be monitored. "
                        "By default all host names are accepted"
                    ),
                    add_element_label=Label("Add new pattern"),
                    custom_validate=(LengthInRange(min_value=1),),
                ),
                required=False,
            ),
        },
        custom_validate=(_validate_regex_choices,),
        migrate=_migrate,
    )


rule_spec_special_agent_mobileiron = SpecialAgent(
    topic=Topic.APPLICATIONS,
    name="mobileiron",
    parameter_form=_parameter_form_special_agents_mobileiron,
    title=Title("IvantiNeurons for MDM (formerly MobileIron Cloud)"),
)
