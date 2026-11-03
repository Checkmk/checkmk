#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

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
    validators,
)
from cmk.rulesets.v1.rule_specs import AgentConfig, Topic


def migrate(value: object) -> Mapping[str, object]:
    match value:
        case dict() if "check_access" in value:
            return {str(k): v for k, v in value.items()}
        case {"check_controller_access": check_access, "force_legacy": allow_legacy, **rest}:
            # Old rule ("first matching rule wins"): make all parameters explicit so that merging
            # with other rules does not change the outcome. The agent's default channel is the
            # mailslot.
            return {
                "check_access": check_access,
                "allow_legacy": allow_legacy,
                "agent_channel": rest.get("agent_channel", ("mailslot", None)),
            }
        case _:
            raise ValueError(f"Unexpected value: {value!r}")


def _form_spec() -> Dictionary:
    return Dictionary(
        migrate=migrate,
        elements={
            "check_access": DictElement(
                required=True,
                parameter_form=BooleanChoice(
                    title=Title("Limit local agent data access to the Agent Controller"),
                    label=Label("Protect agent data from unauthorized access"),
                    help_text=Help(
                        "This is a security feature to prevent unauthorized local access to agent data. "
                        "You may disable this flag in case of an emergency. For example, if the "
                        "agent can't reliably determine the Agent Controller as a valid peer which "
                        "tries to access the data. "
                    ),
                    prefill=DefaultValue(True),
                ),
            ),
            "allow_legacy": DictElement(
                required=True,
                parameter_form=BooleanChoice(
                    title=Title("Allow unencrypted legacy communication"),
                    label=Label(
                        "Always allow to use unencrypted (legacy) communication as fallback"
                    ),
                    help_text=Help(
                        "If the flag is set, then the Windows agent may use "
                        "unencrypted communication between the monitoring site and the host. "
                        "Enable this flag for compatibility reasons or if you experience "
                        "problems with the controller related to TLS or encryption. But please "
                        "pay attention, that this enables unencrypted communication if your "
                        "controller connection isn't properly configured."
                    ),
                    prefill=DefaultValue(False),
                ),
            ),
            "agent_channel": DictElement(
                parameter_form=CascadingSingleChoice(
                    title=Title("Internal agent communication channel"),
                    help_text=Help(
                        "Configure the local communication channel between the Windows agent and "
                        "the Agent Controller. By default, a mailslot is used. If you encounter "
                        "problems with mailslot communication in your environment, you can switch "
                        "to a TCP socket on localhost instead.<br> "
                        "<b>Note:</b> We highly recomment to leave this option untouched unless you "
                        "encounter problems with the default configuration."
                    ),
                    elements=(
                        CascadingSingleChoiceElement(
                            name="mailslot",
                            title=Title("Mailslot"),
                            parameter_form=FixedValue(value=None),
                        ),
                        CascadingSingleChoiceElement(
                            name="tcp",
                            title=Title("TCP socket on localhost"),
                            parameter_form=Integer(
                                title=Title("Port"),
                                prefill=DefaultValue(28250),
                                custom_validate=(validators.NetworkPort(),),
                            ),
                        ),
                    ),
                    prefill=DefaultValue("mailslot"),
                ),
            ),
        },
    )


rule_spec_win_controller = AgentConfig(
    title=Title("Windows Agent Controller troubleshooting"),
    name="win_controller",
    topic=Topic.WINDOWS,
    parameter_form=_form_spec,
)
