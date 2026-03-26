#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

from collections.abc import Mapping, Sequence
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel

from cmk.rulesets.v1 import form_specs, Help, Label, Message, Title
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    DictElement,
    Dictionary,
    FixedValue,
    Integer,
    List,
    Password,
    SingleChoice,
    SingleChoiceElement,
    String,
    validators,
)
from cmk.rulesets.v1.rule_specs import AgentConfig, Topic

# Matches absolute paths on Unix (/...), env var references ($VAR or ${VAR}),
# and absolute Windows paths (C:\... or C:/...).
USE_HOST_CLIENT_PATH_RE = r"^(/|\$[\w{]|[a-zA-Z]:[/\\]).*"


class Affinity(StrEnum):
    ALL = "all"
    DB = "db"
    ASM = "asm"

    def __repr__(self) -> str:
        return str(self).__repr__()


type _AuthOptions = tuple[str, object]
type _NamedOption = Mapping[str, object]


class SectionOptions(BaseModel):
    section: str
    title: str
    help_text: str | None = None
    # use full name because GUI throws error if `async` name is used
    mode: Literal["synchronous", "asynchronous", "disabled"]


SECTIONS: Sequence[SectionOptions] = (
    SectionOptions(
        section="instance",
        title="General instance status",
        mode="synchronous",
    ),
    SectionOptions(
        section="asm_instance",
        title="ASM - General instance status",
        mode="synchronous",
    ),
    SectionOptions(
        section="asm_diskgroup",
        title="ASM - Disk groups",
        mode="asynchronous",
    ),
    SectionOptions(
        section="dataguard_stats",
        title="Dataguard statistics",
        mode="synchronous",
    ),
    SectionOptions(
        section="locks",
        title="Locks",
        mode="synchronous",
    ),
    SectionOptions(
        section="logswitches",
        title="Logswitches",
        mode="synchronous",
    ),
    SectionOptions(
        section="longactivesessions",
        title="Long active sessions",
        mode="synchronous",
    ),
    SectionOptions(
        section="performance",
        title="Performance",
        mode="synchronous",
    ),
    SectionOptions(
        section="processes",
        title="Current number of processes",
        mode="synchronous",
    ),
    SectionOptions(
        section="recovery_area",
        title="Recovery area",
        mode="synchronous",
    ),
    SectionOptions(
        section="recovery_status",
        title="Recovery status",
        mode="synchronous",
    ),
    SectionOptions(
        section="sessions",
        title="Current number of sessions",
        mode="synchronous",
    ),
    SectionOptions(
        section="systemparameter",
        title="System parameters",
        mode="synchronous",
    ),
    SectionOptions(
        section="undostat",
        title="Undo statistics",
        mode="synchronous",
    ),
    SectionOptions(
        section="iostats",
        title="Performance: IO stats",
        help_text="WARNING: This section will increase the load of your Checkmk server and "
        "may increase load of your Database.",
        mode="asynchronous",
    ),
    SectionOptions(
        section="jobs",
        title="Scheduled jobs",
        mode="asynchronous",
    ),
    SectionOptions(
        section="resumable",
        title="Resumables",
        mode="asynchronous",
    ),
    SectionOptions(
        section="rman",
        title="RMAN backups",
        mode="asynchronous",
    ),
    SectionOptions(
        section="tablespaces",
        title="Tablespaces",
        mode="asynchronous",
    ),
)


def _auth_roles_choices() -> SingleChoice:
    return SingleChoice(
        title=Title("Role"),
        help_text=Help("Specifies the database privilege role used when connecting to Oracle."),
        elements=[
            SingleChoiceElement(
                name="sysdba",
                title=Title("SYSDBA"),
            ),
            SingleChoiceElement(
                name="sysoper",
                title=Title("SYSOPER"),
            ),
            SingleChoiceElement(
                name="sysasm",
                title=Title("SYSASM"),
            ),
            SingleChoiceElement(
                name="sysbackup",
                title=Title("SYSBACKUP"),
            ),
            SingleChoiceElement(
                name="sysdg",
                title=Title("SYSDG"),
            ),
            SingleChoiceElement(
                name="syskm",
                title=Title("SYSKM"),
            ),
        ],
    )


def _auth_options(is_default_options: bool = True) -> Dictionary:
    return Dictionary(
        title=Title("Authentication"),
        elements={
            "auth_type": DictElement(
                parameter_form=CascadingSingleChoice(
                    title=Title("Authentication type"),
                    help_text=Help(
                        "Select the type of authentication to use when connecting to the Oracle database."
                    ),
                    prefill=DefaultValue("standard"),
                    elements=[
                        CascadingSingleChoiceElement(
                            name="standard",
                            title=Title("User & password"),
                            parameter_form=Dictionary(
                                title=Title("Username and password"),
                                elements={
                                    "username": DictElement(
                                        parameter_form=String(
                                            title=Title("Username"),
                                            custom_validate=(
                                                validators.LengthInRange(min_value=1),
                                            ),
                                        ),
                                        required=True,
                                    ),
                                    "password": DictElement(
                                        parameter_form=Password(
                                            title=Title("Password"),
                                            custom_validate=(
                                                validators.LengthInRange(min_value=1),
                                            ),
                                        ),
                                        required=True,
                                    ),
                                },
                            ),
                        ),
                        CascadingSingleChoiceElement(
                            name="wallet",
                            title=Title("Oracle Wallet"),
                            parameter_form=FixedValue(
                                value=None,
                                help_text=Help(
                                    "Use Oracle Wallet for secure authentication to the Oracle database "
                                    "without storing passwords in plain text. "
                                    "If 'Path to tnsnames.ora or sqlnet.ora file' (TNS_ADMIN) is not set, "
                                    "the wallet must be located in $MK_CONFDIR/oracle_wallet. "
                                    "In this case, the plug-in will automatically create a sqlnet.ora file "
                                    "if it does not exist. "
                                    "If TNS_ADMIN is set to a custom path, you must ensure that sqlnet.ora "
                                    "(with the correct wallet location) and the Oracle Wallet files "
                                    "are properly configured in that directory."
                                ),
                            ),
                        ),
                    ],
                ),
                required=is_default_options,
            ),
            "role": DictElement(
                parameter_form=_auth_roles_choices(),
                required=False,
            ),
        },
    )


def _alias_entry() -> form_specs.Dictionary:
    return form_specs.Dictionary(
        title=Title("Alias Value"),
        help_text=Help(
            "A TNS alias as defined in the <tt>tnsnames.ora</tt> file. "
            "Requires a properly configured <tt>tnsnames.ora</tt> file accessible "
            "via the TNS_ADMIN directory path."
        ),
        elements={
            "alias": form_specs.DictElement(
                required=True,
                parameter_form=form_specs.String(),
            ),
        },
    )


def _sid_entry() -> form_specs.Dictionary:
    return form_specs.Dictionary(
        title=Title("SID"),
        help_text=Help(
            "The Oracle System Identifier (SID) that identifies "
            "a specific database instance on the host. "
            "Use SID-based connections for older Oracle configurations or "
            "when connecting to a database that does not use service names. "
            "If both a service name and SID are specified, "
            "the service name takes precedence."
        ),
        elements={
            "sid": form_specs.DictElement(
                required=True,
                parameter_form=form_specs.String(),
            ),
        },
    )


def _descriptor_entry() -> form_specs.Dictionary:
    return form_specs.Dictionary(
        title=Title("Oracle Service Name"),
        elements={
            "service_name": form_specs.DictElement(
                required=True,
                parameter_form=form_specs.String(
                    title=Title("Service Name"),
                    help_text=Help(
                        "The Oracle service name used to connect to the "
                        "database. A service name typically represents a "
                        "database and can map to one or more instances in "
                        "a RAC environment."
                    ),
                ),
            ),
            "instance_name": form_specs.DictElement(
                required=False,
                parameter_form=form_specs.String(
                    title=Title("Instance name"),
                    help_text=Help(
                        "The Oracle instance name (ORACLE_SID running instance) to connect to. "
                        "Use this to target a specific instance when multiple instances serve "
                        "the same service name, e.g. in Oracle RAC configurations. "
                        "If not set, the connection is made to the service name without "
                        "specifying a particular instance."
                    ),
                ),
            ),
            "sid": form_specs.DictElement(
                required=False,
                parameter_form=form_specs.String(
                    title=Title("SID"),
                    help_text=Help(
                        "The Oracle System Identifier (SID) that identifies "
                        "a specific database instance on the host. "
                    ),
                ),
            ),
        },
    )


def _oracle_id() -> CascadingSingleChoice:
    return CascadingSingleChoice(
        title=Title("Oracle Database Identification"),
        elements=[
            form_specs.CascadingSingleChoiceElement(
                name="alias",
                title=Title("Alias"),
                parameter_form=_alias_entry(),
            ),
            form_specs.CascadingSingleChoiceElement(
                name="descriptor",
                title=Title("Service Name"),
                parameter_form=_descriptor_entry(),
            ),
            form_specs.CascadingSingleChoiceElement(
                name="sid",
                title=Title("SID"),
                parameter_form=_sid_entry(),
            ),
        ],
    )


def _connection_options() -> Dictionary:
    base: dict[str, DictElement[str] | DictElement[int]] = {
        "host": DictElement(
            parameter_form=String(
                title=Title("Host name"),
                prefill=DefaultValue("localhost"),
            ),
            required=False,
        ),
        "port": DictElement(
            parameter_form=Integer(
                title=Title("Port"),
                prefill=DefaultValue(1521),
            ),
            required=False,
        ),
        "timeout": DictElement(
            parameter_form=Integer(
                title=Title("Connection timeout"),
                prefill=DefaultValue(5),
            ),
            required=False,
        ),
        "tns_admin": DictElement(
            parameter_form=String(
                title=Title("TNS_ADMIN directory path"),
                help_text=Help(
                    "Sets the TNS_ADMIN environment variable for the Oracle "
                    "plug-in. This directory should contain Oracle network "
                    "configuration files such as tnsnames.ora, sqlnet.ora, "
                    "or wallet files. The plug-in must have read access to "
                    "all files in this directory. If not specified, the "
                    "default plug-in's config directory will be used."
                ),
                custom_validate=(
                    validators.MatchRegex("^/.*", Message("Please enter an absolute path.")),
                ),
            ),
            required=False,
        ),
        "oracle_local_registry": DictElement(
            parameter_form=String(
                title=Title("Oracle Local Registry path"),
                custom_validate=(
                    validators.MatchRegex("^/.*", Message("Please enter an absolute path.")),
                ),
            ),
            required=False,
        ),
    }
    return Dictionary(
        title=Title("Connection options"),
        elements=base,
    )


def _section_options(title: Title, help_text: Help | None, mode: str) -> SingleChoice:
    return SingleChoice(
        title=title,
        help_text=help_text,
        prefill=DefaultValue(mode),
        elements=[
            SingleChoiceElement(
                name="synchronous",
                title=Title("Run synchronously"),
            ),
            SingleChoiceElement(
                name="asynchronous",
                title=Title("Run asynchronously and cached"),
            ),
            SingleChoiceElement(
                name="disabled",
                title=Title("Disable this section"),
            ),
        ],
    )


def _sections() -> Dictionary:
    return Dictionary(
        title=Title("Sections - data to collect"),
        help_text=Help("Select which data(sections) should be collected from the Oracle database."),
        elements={
            section.section: DictElement(
                parameter_form=_section_options(
                    title=Title("%s") % section.title,
                    help_text=Help("%s") % section.help_text
                    if section.help_text is not None
                    else None,
                    mode=section.mode,
                ),
                required=True,
            )
            for section in SECTIONS
        },
    )


def _discovery() -> Dictionary:
    return Dictionary(
        title=Title("Instance discovery"),
        help_text=Help(
            "When enabled, the plugin will automatically discover local Oracle database instances. "
            "This feature only works when the plugin is installed on the same machine where the "
            "Oracle database instances are running."
        ),
        elements={
            "enabled": DictElement(
                parameter_form=BooleanChoice(
                    title=Title("Enable service discovery"),
                    prefill=DefaultValue(True),
                ),
                required=True,
            ),
            "include": DictElement(
                parameter_form=List(
                    title=Title("Include patterns"),
                    help_text=Help(
                        "Only services matching one of these patterns"
                        " will be discovered. If no pattern is defined,"
                        " all services are included."
                    ),
                    add_element_label=Label("Add new include pattern"),
                    element_template=String(
                        title=Title("Include pattern"),
                    ),
                ),
                required=False,
            ),
            "exclude": DictElement(
                parameter_form=List(
                    title=Title("Exclude patterns"),
                    help_text=Help(
                        "Services matching one of these patterns will be excluded from discovery."
                    ),
                    add_element_label=Label("Add new exclude pattern"),
                    element_template=String(
                        title=Title("Exclude pattern"),
                    ),
                ),
                required=False,
            ),
        },
    )


def _oracle_client_library_options() -> Dictionary:
    return Dictionary(
        title=Title("Oracle Instant Client options"),
        elements={
            "use_host_client": DictElement(
                parameter_form=CascadingSingleChoice(
                    title=Title("Oracle Instant Client usage"),
                    help_text=Help(
                        "Controls which Oracle Instant Client the plugin uses to connect to databases. "
                        "Two sources are available: "
                        "the <b>agent-local client</b> — Oracle Instant Client libraries manually installed "
                        "alongside the Checkmk agent under "
                        "<tt>$MK_LIBDIR/packages/mk-oracle/</tt> — "
                        "and the <b>host client</b> — an Oracle installation already present on the monitored host. "
                        "Note: Checkmk does <b>not</b> deploy Oracle Instant Client automatically; "
                        "you must install it manually if you want to use the agent-local client. "
                        "<b>Auto-detect</b>: tries the host client first, falls back to the agent-local client. "
                        "<b>Never use host client</b>: uses only the agent-local client, ignores any host installation. "
                        "<b>Always use host client</b>: uses only the host client, ignores the agent-local client. "
                        "<b>Custom path</b>: uses the Oracle Instant Client at the specified path; "
                        "supports environment variable expansion (e.g. <tt>${ORACLE_HOME}/lib</tt>)."
                    ),
                    elements=[
                        CascadingSingleChoiceElement(
                            name="auto",
                            title=Title("Auto-detect (default)"),
                            parameter_form=FixedValue(value=None),
                        ),
                        CascadingSingleChoiceElement(
                            name="never",
                            title=Title("Never use host client (only agent-local client)"),
                            parameter_form=FixedValue(value=None),
                        ),
                        CascadingSingleChoiceElement(
                            name="always",
                            title=Title("Always use host client (ignore agent-local client)"),
                            parameter_form=FixedValue(value=None),
                        ),
                        CascadingSingleChoiceElement(
                            name="custom",
                            title=Title("Use custom path"),
                            parameter_form=String(
                                title=Title("Custom path to Oracle client libraries"),
                                custom_validate=(
                                    validators.MatchRegex(
                                        USE_HOST_CLIENT_PATH_RE,
                                        Message(
                                            "Please enter an absolute path or a path starting with an environment variable (e.g. $VAR/lib)."
                                        ),
                                    ),
                                ),
                            ),
                        ),
                    ],
                ),
                required=False,
            ),
        },
    )


def _options(is_default_options: bool = True) -> Dictionary:
    elements: dict[str, DictElement[int] | DictElement[bool] | DictElement[_NamedOption]] = {
        "max_connections": DictElement(
            parameter_form=Integer(
                title=Title("Maximum connections"),
                help_text=Help("Maximum number of database connections to open."),
                prefill=DefaultValue(5),
            ),
            required=False,
        ),
        "max_queries": DictElement(
            parameter_form=Integer(
                title=Title("Maximum queries"),
                help_text=Help("Maximum number of queries to execute per connection."),
                prefill=DefaultValue(16),
            ),
            required=False,
        ),
        "ignore_db_name": DictElement(
            parameter_form=FixedValue(
                title=Title("Ignore database name"),
                help_text=Help(
                    "If enabled, the instance name will be queried "
                    "from the database instead of the database name."
                ),
                label=Label("Ignore database name and use instance name instead"),
                value=False,
            ),
            required=False,
        ),
        "oracle_client_library": DictElement(
            parameter_form=_oracle_client_library_options(),
            required=False,
        ),
    }
    if not is_default_options:
        _ = elements.pop("max_connections")
        _ = elements.pop("max_queries")
    return Dictionary(
        title=Title("Additional options"),
        elements=elements,
    )


def _endpoint(
    *, is_main_entry: bool
) -> Mapping[str, DictElement[_AuthOptions] | DictElement[_NamedOption]]:
    return {
        "auth": DictElement(
            parameter_form=_auth_options(is_default_options=is_main_entry),
            required=is_main_entry,
        ),
        "connection": DictElement(
            parameter_form=_connection_options(),
            required=is_main_entry,
        ),
    }


def _main() -> Dictionary:
    return Dictionary(
        title=Title("Default settings"),
        help_text=Help(
            "These settings apply to all monitored Oracle databases by default. "
            "They define the authentication, connection, and data collection options "
            "used unless overridden for a specific database in the instance list below."
        ),
        elements={
            **_endpoint(is_main_entry=True),
            "cache_age": DictElement(
                parameter_form=Integer(
                    title=Title("Cache age"),
                    help_text=Help("How old (in minutes) the cache file is allowed to be."),
                    prefill=DefaultValue(600),
                ),
                required=False,
            ),
            "discovery": DictElement(
                parameter_form=_discovery(),
                required=False,
            ),
            "sections": DictElement(
                parameter_form=_sections(),
                required=False,
            ),
        },
    )


def _instances() -> List[_NamedOption]:
    return List(
        title=Title("Databases to monitor"),
        help_text=Help(
            "Define the Oracle databases you want to monitor. Each entry must include "
            "an Oracle database identifier (service name, instance name, SID, or TNS alias). "
            "Authentication and connection options from the default settings are used "
            "automatically, but can be overridden per database if needed."
        ),
        add_element_label=Label("Add new database"),
        element_template=Dictionary(
            title=Title("Database"),
            elements={
                "oracle_id": DictElement(
                    parameter_form=_oracle_id(),
                    required=True,
                ),
                **_endpoint(is_main_entry=False),
            },
        ),
    )


def _agent_config_mk_oracle() -> Dictionary:
    return Dictionary(
        elements={
            "deploy": DictElement(
                required=True,
                parameter_form=CascadingSingleChoice(
                    prefill=DefaultValue("deploy"),
                    elements=[
                        CascadingSingleChoiceElement(
                            name="deploy",
                            title=Title("Deploy Oracle plug-in"),
                            parameter_form=FixedValue(value=None),
                        ),
                        CascadingSingleChoiceElement(
                            name="do_not_deploy",
                            title=Title("Do not deploy Oracle plug-in"),
                            parameter_form=FixedValue(
                                title=Title("Do not deploy Oracle plug-in"),
                                label=Label("(disabled)"),
                                value=None,
                            ),
                        ),
                    ],
                ),
            ),
            "options": DictElement(
                parameter_form=_options(),
                required=False,
            ),
            "main": DictElement(
                parameter_form=_main(),
                required=True,
            ),
            "instances": DictElement(
                parameter_form=_instances(),
                required=True,
            ),
        },
    )


rule_spec_oracle_bakelet = AgentConfig(
    name="mk_oracle_unified",
    title=Title("Unified Oracle Plugin (Beta)"),
    topic=Topic.DATABASES,
    parameter_form=_agent_config_mk_oracle,
    help_text=Help(
        "This will deploy the agent plug-in <tt>mk_oracle</tt> on your target system.<br>"
        "ARM architecture is not supported."
    ),
)
