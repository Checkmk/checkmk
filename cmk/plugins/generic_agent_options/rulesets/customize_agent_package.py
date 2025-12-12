#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.plugins.generic_agent_options.rulesets._topic import (
    TOPIC_LINUX_UNIX_AGENT_OPTIONS,
)
from cmk.rulesets.v1 import Help, Label, Title
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    DictElement,
    Dictionary,
    Integer,
    SingleChoice,
    SingleChoiceElement,
    String,
)
from cmk.rulesets.v1.rule_specs import AgentConfig


def _deployment_mode_form() -> CascadingSingleChoice:
    return CascadingSingleChoice(
        title=Title("Customize user"),
        help_text=Help(
            "By default, the Checkmk agent runs under root. The agent controller, if deployed, runs"
            " under the fixed user <i>cmk-agent</i>, which will be created automatically if it "
            " doesn't exist yet.<br>"
            "If you want to change this default behavior, you can configure this rule for setting"
            " a custom agent/agent controller user.<br>"
            "<b>Note</b>: You can only use this configuration with the new single directory"
            " structure. Please enable <i>Customize installation directories</i> before saving the"
            " rule."
        ),
        prefill=DefaultValue("root"),
        elements=[
            CascadingSingleChoiceElement(
                name="root",
                title=Title("Run agent as root, set agent controller user"),
                parameter_form=_user_form(
                    Title("Agent controller user"),
                    Help(
                        "This is identical to a normal agent deployment, but with a custom"
                        " agent controller user instead of <i>cmk-agent</i>."
                    ),
                ),
            ),
            CascadingSingleChoiceElement(
                name="non_root",
                title=Title("Run agent as non-root, set agent user"),
                parameter_form=_user_form(
                    Title("Agent user"),
                    Help(
                        'This setting will lead to a "non-root agent deployment". Both agent'
                        " and agent controller will be operated under the configured agent user."
                        " Additionally, the agent package will set proper permissions on the"
                        " agent package's resources."
                    ),
                ),
            ),
        ],
    )


def _user_form(user_title: Title, help_text: Help) -> Dictionary:
    return Dictionary(
        help_text=help_text,
        elements={
            "user": DictElement(
                parameter_form=String(
                    title=user_title,
                    help_text=Help(
                        "Agent or agent controller user. Will also be used as name for the"
                        " corresponding group on creation."
                    ),
                    prefill=DefaultValue("cmk-agent"),
                ),
                required=True,
            ),
            "uid": DictElement(
                parameter_form=Integer(
                    title=Title("Set custom UID"),
                    help_text=Help(
                        "Optional. Usage depends on user creation option:<br>"
                        "<i>Automatic</i>: Create the user under the specified UID, or verify that"
                        " it's associated to it if UID and/or username already exist."
                        "<i>No user creation</i>: Verify that the UID exists and is associated to"
                        " the specified username."
                    ),
                ),
                required=False,
            ),
            "gid": DictElement(
                parameter_form=Integer(
                    title=Title("Set custom GID"),
                    help_text=Help(
                        "Optional. Usage depends on user creation option:<br>"
                        "<i>Automatic</i>: Create the users's group with the specified GID, or add"
                        " the user to the GID's group if it already exists.<br>"
                        "<i>No user creation</i>: Verify that the user is member of the GID's"
                        " group."
                    ),
                ),
                required=False,
            ),
            "creation_options": DictElement(
                parameter_form=SingleChoice(
                    title=Title("User creation options"),
                    help_text=Help(
                        "Decide how to apply the configured name and optional UID/GID.<br>"
                        "<b>Note</b>: In this context, failing means that the agent installation"
                        " will issue a warning and abort to setup the agent user and the"
                        " corresponding permissions, but will continue with all other parts of the"
                        " agent installation. Hence, you can especially specify the UID/GID as"
                        " a security measure, but please be aware that the agent installation might"
                        " remain in an unusable state when the agent user installation script"
                        " fails."
                    ),
                    prefill=DefaultValue("auto"),
                    elements=[
                        SingleChoiceElement(
                            name="auto",
                            title=Title(
                                "Automatic: Use existing user, if available. Otherwise create"
                                " new user."
                            ),
                        ),
                        SingleChoiceElement(
                            name="use_existing",
                            title=Title(
                                "No user creation: Use existing user. Fail if it doesn't exist."
                            ),
                        ),
                    ],
                ),
                required=True,
            ),
        },
    )


def _directory_form() -> Dictionary:
    return Dictionary(
        title=Title("Installation directories"),
        elements={
            "installation_directory": DictElement(
                parameter_form=String(
                    title=Title("Directory for Checkmk agent"),
                    help_text=Help(
                        "Instead of the classic approach of distributing the agent package's"
                        " files over multiple places on the file system, all files of the"
                        " package will be placed below this directory.<br>"
                        "<b>Note</b>: Some files, like systemd units, will still be generated"
                        " outside of this directory for proper operation of the agent"
                        " installation."
                    ),
                    prefill=DefaultValue("/opt/checkmk/agent"),
                ),
                required=True,
            ),
            "tmpdir": DictElement(
                parameter_form=String(
                    title=Title(
                        "Directory for storage of temporary data (set TMPDIR environment variable)"
                    ),
                    help_text=Help(
                        "<b>Warning</b>: The agent installation will neither create this directory,"
                        " nor set needed permissions on it. We recommend to use this setting only"
                        " if you encounter problems with the default TMPDIR directory on a target"
                        " system.<br>"
                        "Especially when running the agent as non-root, the agent user must have"
                        " write access to this directory!"
                    ),
                ),
            ),
        },
    )


def _agent_controller_form() -> Dictionary:
    # return SingleChoice(
    #     prefill=DefaultValue("x86_64"),
    #     elements=[
    #         SingleChoiceElement(
    #             name="x86_64",
    #             title=Title("Deploy x86_64 agent controller"),
    #         ),
    #         SingleChoiceElement(
    #             name="aarch64",
    #             title=Title("Deploy aarch64 agent controller"),
    #         ),
    #         SingleChoiceElement(
    #             name="both",
    #             title=Title("Deploy both x86_64 and aarch64 agent controllers"),
    #         ),
    #     ],
    # )
    return Dictionary(
        title=Title("Customize Linux agent controller deployment"),
        help_text=Help(
            "The Linux agent controller is available as x86 64bit (x86-64)"
            " and ARM 64-bit (aarch644) executables.\n"
            "By default, only the x86-64 version will be included in Linux agent packages.\n"
            "Here you can choose to alternatively or additionally include the ARM executable, or"
            " none at all.\n"
            "The agent package installation scripts will automatically select the correct binary,"
            " depending on the target system's architecture and the available binaries."
        ),
        elements={
            "x86_64": DictElement(
                parameter_form=BooleanChoice(
                    label=Label("Include x86 version"),
                    prefill=DefaultValue(True),
                ),
                required=True,
            ),
            "aarch64": DictElement(
                parameter_form=BooleanChoice(
                    label=Label("Include ARM version"),
                ),
                required=True,
            ),
        },
    )


def _parameter_form() -> Dictionary:
    return Dictionary(
        help_text=Help(
            "This rule allows you to customize the user and installation directory of the agent."
            " When using this rule, all agent files will be installed into a directory defined in"
            " this rule."
        ),
        elements={
            "directory": DictElement(parameter_form=_directory_form(), required=True),
            "deployment_mode": DictElement(parameter_form=_deployment_mode_form()),
            "agent_controller_deployment": DictElement(parameter_form=_agent_controller_form()),
        },
    )


rule_spec_customize_agent_package = AgentConfig(
    name="customize_agent_package",
    title=Title("Customize agent package (Linux)"),
    topic=TOPIC_LINUX_UNIX_AGENT_OPTIONS,
    parameter_form=_parameter_form,
)
