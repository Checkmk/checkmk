#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from pathlib import PurePosixPath

from cmk.rulesets.v1 import Help, Label, Message, Title
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    DictElement,
    Dictionary,
    FieldSize,
    FixedValue,
    InputHint,
    List,
    String,
)
from cmk.rulesets.v1.form_specs.validators import ValidationError
from cmk.rulesets.v1.rule_specs import AgentConfig, Topic


def _agent_config_mk_podman() -> Dictionary:
    return Dictionary(
        help_text=Help("This will deploy the agent plug-in <tt>mk_podman</tt>."),
        elements={
            "deploy": DictElement(
                required=True,
                parameter_form=BooleanChoice(
                    label=Label("Deploy Podman plug-in"),
                    prefill=DefaultValue(False),
                ),
            ),
            "socket_detection": DictElement(
                required=True,
                parameter_form=CascadingSingleChoice(
                    title=Title("Socket detection method"),
                    prefill=DefaultValue("auto"),
                    elements=[
                        CascadingSingleChoiceElement(
                            name="auto",
                            title=Title("Automatic detection"),
                            parameter_form=FixedValue(
                                value=None,
                                help_text=Help(
                                    "The agent will automatically discover Podman sockets on the system. "
                                    "This includes the root socket (/run/podman/podman.sock) and all user sockets matching the pattern "
                                    "/run/user/{user_id}/podman/podman.sock"
                                ),
                            ),
                        ),
                        CascadingSingleChoiceElement(
                            name="only_root_socket",
                            title=Title("Only root socket"),
                            parameter_form=FixedValue(
                                value=None,
                                help_text=Help(
                                    "The agent will automatically discover root Podman socket on the system. "
                                    "This includes the root socket (/run/podman/podman.sock)"
                                ),
                            ),
                        ),
                        CascadingSingleChoiceElement(
                            name="only_user_sockets",
                            title=Title("Only user sockets"),
                            parameter_form=FixedValue(
                                value=None,
                                help_text=Help(
                                    "The agent will automatically discover user Podman sockets on the system. "
                                    "This includes all user sockets matching the pattern /run/user/{user_id}/podman/podman.sock"
                                ),
                            ),
                        ),
                        CascadingSingleChoiceElement(
                            name="manual",
                            title=Title("Manual configuration"),
                            parameter_form=List(
                                title=Title("Podman socket paths"),
                                element_template=String(
                                    label=Label("Podman socket path"),
                                    prefill=InputHint("/run/user/1000/podman/podman.sock"),
                                    custom_validate=(_validate_absolute_posix_path,),
                                    field_size=FieldSize.LARGE,
                                ),
                            ),
                        ),
                    ],
                ),
            ),
        },
    )


def _validate_absolute_posix_path(value: str) -> None:
    if not PurePosixPath(value).is_absolute():
        raise ValidationError(Message("Please provide an absolute path"))


rule_spec_podman_bakelet = AgentConfig(
    name="mk_podman",
    title=Title("Podman node and containers"),
    topic=Topic.APPLICATIONS,
    parameter_form=_agent_config_mk_podman,
)
