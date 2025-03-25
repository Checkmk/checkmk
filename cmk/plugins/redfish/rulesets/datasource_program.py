#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""rule for assinging the special agent to host objects"""

from collections.abc import Mapping

from cmk.plugins.redfish.lib import REDFISH_SECTIONS
from cmk.rulesets.v1 import Help, Label, Title
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    DictElement,
    Dictionary,
    FixedValue,
    Integer,
    Password,
    SingleChoice,
    SingleChoiceElement,
    String,
    TimeMagnitude,
    TimeSpan,
    validators,
)
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic


def _auth_elements() -> Mapping[str, DictElement]:
    return {
        "user": DictElement(
            parameter_form=String(
                title=Title("Username"),
            ),
            required=True,
        ),
        "password": DictElement(
            parameter_form=Password(
                title=Title("Password"),
            ),
            required=True,
        ),
    }


def _connection_elements() -> Mapping[str, DictElement]:
    return {
        "port": DictElement(
            required=True,
            parameter_form=Integer(
                title=Title("TCP Port"),
                help_text=Help("Port number for connection to the Rest API. Usually 443 (TLS)"),
                prefill=DefaultValue(443),
                custom_validate=(validators.NetworkPort(),),
            ),
        ),
        "proto": DictElement(
            required=True,
            parameter_form=SingleChoice(
                title=Title("Protocol"),
                prefill=DefaultValue("https"),
                help_text=Help("Protocol for the connection to the Rest API."),
                elements=[
                    SingleChoiceElement(
                        name="https",
                        title=Title("https"),
                    ),
                    SingleChoiceElement(
                        name="http",
                        title=Title("http (insecure)"),
                    ),
                ],
            ),
        ),
        "retries": DictElement(
            required=True,
            parameter_form=Integer(
                title=Title("Number of connection retries"),
                help_text=Help("Number of retry attempts made by the special agent."),
                prefill=DefaultValue(2),
                custom_validate=(validators.NumberInRange(min_value=1, max_value=20),),
            ),
        ),
        "timeout": DictElement(
            required=True,
            parameter_form=TimeSpan(
                title=Title("Timeout for connection"),
                help_text=Help(
                    "Number of seconds for a single connection attempt before it times out."
                ),
                prefill=DefaultValue(3.0),
                displayed_magnitudes=(TimeMagnitude.SECOND,),
                custom_validate=(validators.NumberInRange(min_value=1, max_value=20),),
            ),
        ),
    }


def migrate_redfish_common(data: object) -> Mapping[str, object]:
    """Add the defaults for the now mandatory fields"""
    if not isinstance(data, Mapping):
        raise TypeError(data)
    return {
        "user": data["user"],
        "password": data["password"],
        "port": data.get("port", 443),
        "proto": p if isinstance(p := data.get("proto", "https"), str) else p[0],
        "retries": data.get("retries", 2),
        "timeout": float(data.get("timeout", 3.0)),
    }


def _valuespec_special_agents_redfish_power() -> Dictionary:
    return Dictionary(
        title=Title("Redfish Compatible Power Equipment (PDU)"),
        elements={
            **_auth_elements(),
            **_connection_elements(),
        },
        migrate=migrate_redfish_common,
    )


rule_spec_redfish_power_datasource_programs = SpecialAgent(
    name="redfish_power",
    title=Title("Redfish Compatible Power Equipment (PDU)"),
    topic=Topic.SERVER_HARDWARE,
    parameter_form=_valuespec_special_agents_redfish_power,
    help_text=Help(
        "This rule configures the Redfish integration to query PDUs via the Redfish REST API"
    ),
)


def _fetching_settings() -> DictElement:
    return DictElement(
        required=False,
        parameter_form=Dictionary(
            title=Title("Fetching setting for individual sections"),
            help_text=Help(
                "If sections can not be fetched or take a long time, you can configure them to be fetched"
                " not as often or not at all."
            ),
            elements={
                s.name: DictElement(
                    required=True,
                    parameter_form=CascadingSingleChoice(
                        title=s.title,
                        prefill=DefaultValue("always"),
                        elements=[
                            CascadingSingleChoiceElement(
                                name="always",
                                title=Title("Always"),
                                parameter_form=FixedValue(value=0.0),
                            ),
                            CascadingSingleChoiceElement(
                                name="cached",
                                title=Title("Cache this section"),
                                parameter_form=TimeSpan(
                                    displayed_magnitudes=(
                                        TimeMagnitude.MINUTE,
                                        TimeMagnitude.HOUR,
                                    )
                                ),
                            ),
                            CascadingSingleChoiceElement(
                                name="never",
                                title=Title("Never"),
                                parameter_form=FixedValue(value=-1.0),
                            ),
                        ],
                    ),
                )
                for s in REDFISH_SECTIONS
            },
        ),
    )


def migrate_redfish(data: object) -> Mapping[str, object]:
    if not isinstance(data, Mapping):
        raise TypeError(data)
    if "fetching" in data:
        return data

    enabled_sections = data.get("sections", [s.name for s in REDFISH_SECTIONS])
    disabled_sections = data.get("disabled_sections", ())
    cached_sections = [
        (name.removeprefix("cache_time_"), interval)
        for name, interval in data.get("cached_sections", {}).items()
    ]

    fetching = {
        **{n: ("always", 0.0) for n in enabled_sections},
        **{n: ("never", -1.0) for n in disabled_sections},
        **{n: ("cached", float(i)) for n, i in cached_sections},
    }
    return {
        **migrate_redfish_common(data),
        **(
            {}
            if all(mode == "always" for (mode, _) in fetching.values())
            else {"fetching": fetching}
        ),
        "debug": data.get("debug", False),
    }


def _valuespec_special_agents_redfish() -> Dictionary:
    return Dictionary(
        title=Title("Redfish Compatible Management Controller"),
        elements={
            **_auth_elements(),
            "fetching": _fetching_settings(),
            **_connection_elements(),
            "debug": DictElement(
                required=True,
                parameter_form=BooleanChoice(
                    title=Title("Debug mode"),
                    label=Label("enabled"),
                ),
            ),
        },
        migrate=migrate_redfish,
    )


rule_spec_redfish_datasource_programs = SpecialAgent(
    name="redfish",
    title=Title("Redfish Compatible Management Controller"),
    topic=Topic.SERVER_HARDWARE,
    parameter_form=_valuespec_special_agents_redfish,
    help_text=Help(
        "This rule configures the Redfish integration to query management controller via the Redfish REST API"
    ),
)
