#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

from collections.abc import Mapping, Sequence
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel

from cmk.rulesets.v1 import Help, Label, Message, Title
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
    # use full name because GUI throws error if `async` name is used
    mode: Literal["synchronous", "asynchronous", "disabled"]


SECTIONS: Sequence[SectionOptions] = (
    SectionOptions(
        section="instance",
        mode="synchronous",
    ),
    SectionOptions(
        section="asm_instance",
        mode="synchronous",
    ),
    SectionOptions(
        section="dataguard_stats",
        mode="synchronous",
    ),
    SectionOptions(
        section="locks",
        mode="synchronous",
    ),
    SectionOptions(
        section="logswitches",
        mode="synchronous",
    ),
    SectionOptions(
        section="longactivesessions",
        mode="synchronous",
    ),
    SectionOptions(
        section="performance",
        mode="synchronous",
    ),
    SectionOptions(
        section="processes",
        mode="synchronous",
    ),
    SectionOptions(
        section="recovery_area",
        mode="synchronous",
    ),
    SectionOptions(
        section="recovery_status",
        mode="synchronous",
    ),
    SectionOptions(
        section="sessions",
        mode="synchronous",
    ),
    SectionOptions(
        section="systemparameter",
        mode="synchronous",
    ),
    SectionOptions(
        section="undostat",
        mode="synchronous",
    ),
    SectionOptions(
        section="asm_diskgroup",
        mode="asynchronous",
    ),
    SectionOptions(
        section="iostats",
        mode="asynchronous",
    ),
    SectionOptions(
        section="jobs",
        mode="asynchronous",
    ),
    SectionOptions(
        section="resumable",
        mode="asynchronous",
    ),
    SectionOptions(
        section="rman",
        mode="asynchronous",
    ),
    SectionOptions(
        section="tablespaces",
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


def _auth_options(is_default_options: bool = True) -> CascadingSingleChoice:
    return CascadingSingleChoice(
        title=Title("Oracle type of authentication"),
        help_text=Help(
            "Select the type of authentication to use when connecting to the Oracle database."
        ),
        prefill=DefaultValue("standard"),
        elements=[
            CascadingSingleChoiceElement(
                name="standard",
                title=Title("User & Password"),
                parameter_form=Dictionary(
                    title=Title("Username and Password"),
                    elements={
                        "username": DictElement(
                            parameter_form=String(
                                title=Title("Username"),
                                custom_validate=(validators.LengthInRange(min_value=1),)
                                if is_default_options
                                else None,
                            ),
                            required=is_default_options,
                        ),
                        "password": DictElement(
                            parameter_form=Password(
                                title=Title("Password"),
                                custom_validate=(validators.LengthInRange(min_value=1),)
                                if is_default_options
                                else None,
                            ),
                            required=is_default_options,
                        ),
                        "role": DictElement(
                            parameter_form=_auth_roles_choices(),
                            required=False,
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
                        "the wallet must be located in /etc/check_mk/oracle_wallet. "
                        "In this case, the plugin will automatically create a sqlnet.ora file "
                        "if it does not exist. "
                        "If TNS_ADMIN is set to a custom path, you must ensure that sqlnet.ora "
                        "(with the correct wallet location) and the Oracle Wallet files "
                        "are properly configured in that directory."
                    ),
                ),
            ),
        ],
    )


def _oracle_id() -> Dictionary:
    return Dictionary(
        title=Title("Oracle Database Identification"),
        elements={
            "service_name": DictElement(
                parameter_form=String(
                    title=Title("Service Name"),
                    help_text=Help("Oracle Service Name of the database instance."),
                ),
                required=True,
            ),
            "instance_name": DictElement(
                parameter_form=String(
                    title=Title("Instance Name(SID)"),
                    help_text=Help(
                        "Oracle Instance Name of the database instance. May be the same as SID."
                    ),
                ),
                required=False,
            ),
        },
    )


def _connection_options(*, with_service_name: bool) -> Dictionary:
    base: dict[str, DictElement[str] | DictElement[int]] = {
        "host": DictElement(
            parameter_form=String(
                title=Title("Hostname"),
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
                title=Title("Path to tnsnames.ora or sqlnet.ora file"),
                custom_validate=(
                    validators.MatchRegex("^/.*", Message("Please enter an absolute path.")),
                ),
            ),
            required=False,
        ),
        "oracle_local_registry": DictElement(
            parameter_form=String(
                title=Title("Folder of oracle configuration files(oratab,  for example)"),
                custom_validate=(
                    validators.MatchRegex("^/.*", Message("Please enter an absolute path.")),
                ),
            ),
            required=False,
        ),
    }

    extension: dict[str, DictElement[_NamedOption]] = {
        "oracle_id": DictElement(
            parameter_form=_oracle_id(),
            required=False,
        ),
    }
    return Dictionary(
        title=Title("Connection options"),
        elements=base | extension if with_service_name else base,
    )


def _section_options(title: Title, help_text: Help, mode: str) -> SingleChoice:
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
        title=Title("Data to collect (Sections)"),
        help_text=Help("Select which data(sections) should be collected from the Oracle database."),
        elements={
            section.section: DictElement(
                parameter_form=_section_options(
                    title=Title("%s section") % section.section,
                    help_text=Help("Configuration options for the %s section.") % section.section,
                    mode=section.mode,
                ),
                required=True,
            )
            for section in SECTIONS
        },
    )


def _discovery() -> Dictionary:
    return Dictionary(
        title=Title("Discovery options"),
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
                        "Controls usage of host Oracle Instant Client. Allowed values: "
                        "'auto' (auto-detect, fallback to bundled), "
                        "'never' (force bundled), "
                        "'always' (force host), "
                        "or an absolute path to an OCI library directory "
                        "(e.g. /usr/lib/oracle/...)."
                    ),
                    elements=[
                        CascadingSingleChoiceElement(
                            name="auto",
                            title=Title("Auto-detect (default)"),
                            parameter_form=FixedValue(value=None),
                        ),
                        CascadingSingleChoiceElement(
                            name="never",
                            title=Title("Never use host libraries (force bundled)"),
                            parameter_form=FixedValue(value=None),
                        ),
                        CascadingSingleChoiceElement(
                            name="always",
                            title=Title("Always use host libraries (force host)"),
                            parameter_form=FixedValue(value=None),
                        ),
                        CascadingSingleChoiceElement(
                            name="custom",
                            title=Title("Use custom path"),
                            parameter_form=String(
                                title=Title("Custom path to Oracle client libraries"),
                                custom_validate=(
                                    validators.MatchRegex(
                                        "^/.*",
                                        Message("Please enter an absolute path."),
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
            parameter_form=_connection_options(with_service_name=is_main_entry),
            required=is_main_entry,
        ),
    }


def _main() -> Dictionary:
    return Dictionary(
        title=Title("Oracle Database default configuration"),
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
        title=Title("Database instances"),
        help_text=Help(
            "Define Oracle database instances to monitor to overwrite default settings."
        ),
        add_element_label=Label("Add new database instance"),
        element_template=Dictionary(
            title=Title("Database instance"),
            elements={
                "sid": DictElement(
                    parameter_form=String(
                        title=Title("SID"),
                        help_text=Help("Oracle System Identifier of the database instance."),
                    ),
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
    help_text=Help("This will deploy the agent plug-in <tt>mk_oracle</tt> on your target system."),
)
