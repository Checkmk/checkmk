#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping
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
    SingleChoice,
    SingleChoiceElement,
    String,
)
from cmk.rulesets.v1.form_specs.validators import ValidationError
from cmk.rulesets.v1.rule_specs import AgentConfig, Topic


def _socket_detection_form() -> CascadingSingleChoice:
    return CascadingSingleChoice(
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
    )


def _connection_method_form() -> CascadingSingleChoice:
    return CascadingSingleChoice(
        title=Title("Connection method"),
        help_text=Help(
            "Select how the agent plug-in communicates with Podman. "
            "The <b>API</b> method connects through a Unix socket and is the default. "
            "The <b>CLI</b> method invokes the <tt>podman</tt> command directly and "
            "works without a running Podman socket service."
        ),
        prefill=DefaultValue("api"),
        elements=[
            CascadingSingleChoiceElement(
                name="api",
                title=Title("API (via Unix socket)"),
                parameter_form=_socket_detection_form(),
            ),
            CascadingSingleChoiceElement(
                name="cli",
                title=Title("CLI (podman command)"),
                parameter_form=FixedValue(
                    value=None,
                    help_text=Help(
                        "Use the <tt>podman</tt> CLI for all queries. "
                        "This works out of the box without any socket configuration and is "
                        "recommended when the Podman socket service is not available."
                    ),
                ),
            ),
        ],
    )


def _migrate(value: object) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(value)

    result = dict(value)

    if "socket_detection" in result:
        # Old format: socket_detection at top level, no connection_method
        # New format: socket_detection is nested inside connection_method
        result["connection_method"] = ("api", result.pop("socket_detection"))
    elif "connection_method" not in result:
        result["connection_method"] = ("api", ("auto", None))

    return result


def _agent_config_mk_podman() -> Dictionary:
    return Dictionary(
        help_text=Help("This will deploy the agent plug-in <tt>mk_podman</tt>."),
        migrate=_migrate,
        elements={
            "deploy": DictElement(
                required=True,
                parameter_form=BooleanChoice(
                    label=Label("Deploy Podman plug-in"),
                    prefill=DefaultValue(False),
                ),
            ),
            "connection_method": DictElement(
                required=True,
                parameter_form=_connection_method_form(),
            ),
            "piggyback_name_method": DictElement(
                required=True,
                parameter_form=SingleChoice(
                    title=Title("Host name used for containers"),
                    help_text=Help(
                        "<p>Select how piggyback hosts are named for your containers. You can choose from:</p>"
                        "<ul>"
                        "<li><tt>Use container name: mycontainername</tt></li>"
                        "<li><tt>Combine the host name and container name (default): creates names in the format "
                        "'mypodmanhost_mycontainername'. If the host name is unavailable, the container user's name is used. "
                        "This is recommended to prevent naming conflicts, e.g. if multiple containers with the name "
                        "'mycontainer' exist on different Podman hosts.</tt></li>"
                        "<li><tt>Combine container name and ID: 'mycontainername_containerID'. Please note that in some cases "
                        "the container IDs can change. Therefore this option can cause piggyback host names to change.</tt></li>"
                        "</ul>"
                    ),
                    prefill=DefaultValue("nodename_name"),
                    elements=[
                        SingleChoiceElement(
                            name="name",
                            title=Title("Use container name"),
                        ),
                        SingleChoiceElement(
                            name="nodename_name",
                            title=Title("Combine the host name and the container name"),
                        ),
                        SingleChoiceElement(
                            name="name_id",
                            title=Title("Combine the container name and container ID"),
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
    title=Title("Podman hosts and containers (Linux)"),
    topic=Topic.APPLICATIONS,
    parameter_form=_agent_config_mk_podman,
)
