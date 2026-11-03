#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Final, Literal

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
    List,
    migrate_to_password,
    MultipleChoice,
    MultipleChoiceElement,
    Password,
    SingleChoice,
    SingleChoiceElement,
    String,
    validators,
)
from cmk.rulesets.v1.rule_specs import AgentConfig, Topic

_SectionMode = Literal["sync", "asynchronous", "disabled"]

_SECTION_MODES: Final = ("sync", "asynchronous", "disabled")

_OLD_SECTION_MODES: Final[Mapping[object, str]] = {None: "disabled", "async": "asynchronous"}


def _sections_selector() -> dict[str, DictElement[str]]:
    return {
        name: DictElement(
            required=True,
            parameter_form=SingleChoice(
                title=title,
                elements=[
                    SingleChoiceElement(name="sync", title=Title("Run synchronously")),
                    *(
                        ()
                        if name == "instance"
                        else (
                            SingleChoiceElement(
                                name="asynchronous",
                                title=Title("Run asynchronously and cached"),
                            ),
                            SingleChoiceElement(
                                name="disabled", title=Title("Disable this section")
                            ),
                        )
                    ),
                ],
                prefill=DefaultValue(mode),
            ),
        )
        for name, mode, title in _mssql_sections_info()
    }


def _mssql_sections_info() -> list[tuple[str, _SectionMode, Title]]:
    return [
        ("instance", "sync", Title("General instance status")),
        ("databases", "sync", Title("Databases")),
        ("counters", "sync", Title("Counters")),
        ("blocked_sessions", "sync", Title("Blocked sessions")),
        ("transactionlogs", "sync", Title("Transaction Logs")),
        ("clusters", "sync", Title("Clusters")),
        ("mirroring", "sync", Title("Mirroring")),
        ("availability_groups", "sync", Title("Availability groups")),
        ("connections", "sync", Title("Connections")),
        ("tablespaces", "asynchronous", Title("Table spaces")),
        ("datafiles", "asynchronous", Title("Datafiles")),
        ("backup", "asynchronous", Title("Backups")),
        ("jobs", "asynchronous", Title("Scheduled Jobs")),
    ]


def _migrate_sections(value: object) -> Mapping[str, object]:
    if not isinstance(value, dict) or not all(
        mode is None or isinstance(mode, str) for mode in value.values()
    ):
        raise ValueError(f"Unexpected value: {value!r}")
    # The old rule set stored None for a disabled section, and "async" (a keyword, which is not
    # allowed as a choice name) for an asynchronous one.
    migrated = {name: _OLD_SECTION_MODES.get(mode, mode) for name, mode in value.items()}
    if any(mode not in _SECTION_MODES for mode in migrated.values()):
        raise ValueError(f"Unexpected value: {value!r}")
    return migrated


def _migrate_auth(value: object) -> tuple[str, object]:
    match value:
        case "local" | ("local", None):
            return "local", None
        case ("remote", dict() as credentials) if "user" in credentials:
            return "remote", credentials
        case ("remote", (str() as user, password)):
            return "remote", {"user": user, "password": migrate_to_password(password)}
        case _:
            raise ValueError(f"Unexpected value: {value!r}")


def _migrate_discovery(value: object) -> Mapping[str, object]:
    match value:
        case {"detect": bool(), "instances": _} if isinstance(value, dict):
            return value
        case (bool() as detect, "all"):
            return {"detect": detect, "instances": ("all", None)}
        case (bool() as detect, (("include" | "exclude") as kind, list() as instances)):
            return {"detect": detect, "instances": (kind, instances)}
        case _:
            raise ValueError(f"Unexpected value: {value!r}")


def _migrate_instance(value: object) -> Mapping[str, object]:
    if not isinstance(value, dict) or "sid" not in value:
        raise ValueError(f"Unexpected value: {value!r}")
    migrated = dict(value)
    if "auth" in value:
        migrated["auth"] = _migrate_auth(value["auth"])
    if isinstance(piggyback := value.get("piggyback"), dict):
        if not piggyback.get("hostname"):
            # The old rule set allowed to enable the option without a host name, to no effect.
            del migrated["piggyback"]
        elif "sections" in piggyback:
            migrated["piggyback"] = {
                **piggyback,
                "sections": _migrate_sections(piggyback["sections"]),
            }
    return migrated


def _migrate_config(value: object) -> Mapping[str, object]:
    if not isinstance(value, dict) or "auth" not in value:
        raise ValueError(f"Unexpected value: {value!r}")
    migrated = dict(value)
    migrated["auth"] = _migrate_auth(value["auth"])
    if "sections" in value:
        migrated["sections"] = _migrate_sections(value["sections"])
    if "discovery" in value:
        migrated["discovery"] = _migrate_discovery(value["discovery"])
    if "instances" in value:
        migrated["instances"] = [_migrate_instance(i) for i in value["instances"]]
    return migrated


def migrate(value: object) -> Mapping[str, object]:
    if value is None:
        return {"deployment": ("do_not_deploy", None)}
    if not isinstance(value, dict):
        raise ValueError(f"Unexpected value: {value!r}")
    if "deployment" in value:
        return value
    if "main" not in value:
        raise ValueError(f"Unexpected value: {value!r}")
    # Old rule ("first matching rule wins"): make all parameters explicit so that merging with
    # other rules does not change the outcome.
    return {
        "deployment": ("sync", None),
        "main": _migrate_config(value["main"]),
        "other": [_migrate_config(c) for c in value.get("other", [])],
    }


def _mssql_sections() -> Dictionary:
    return Dictionary(
        title=Title("Data to collect (sections)"),
        elements=_sections_selector(),
    )


def _mssql_exclude_databases() -> MultipleChoice:
    return MultipleChoice(
        title=Title("Exclude system databases"),
        elements=[
            MultipleChoiceElement(name="model", title=Title("Model")),
            MultipleChoiceElement(name="master", title=Title("Master")),
            MultipleChoiceElement(name="msdb", title=Title("Msdb")),
            MultipleChoiceElement(name="tempdb", title=Title("Tempdb")),
        ],
    )


def _mssql_cache_age() -> Integer:
    return Integer(
        title=Title("Cache age for asynchronous checks"),
        prefill=DefaultValue(600),
        custom_validate=(validators.NumberInRange(min_value=10, max_value=14400),),
    )


def _mssql_piggyback_host() -> String:
    return String(
        title=Title("Map data to specific host (piggyback)"),
        custom_validate=(validators.LengthInRange(min_value=1),),
    )


def _mssql_authentication_choices() -> tuple[
    CascadingSingleChoiceElement[None], CascadingSingleChoiceElement[Mapping[str, object]]
]:
    return (
        CascadingSingleChoiceElement(
            name="local",
            title=Title("Local integrated authentication (Windows)"),
            parameter_form=FixedValue(value=None),
        ),
        CascadingSingleChoiceElement(
            name="remote",
            title=Title("SQL database user credentials"),
            parameter_form=_mssql_authentication_remote(),
        ),
    )


def _mssql_authentication_remote() -> Dictionary:
    return Dictionary(
        elements={
            "user": DictElement(
                required=True,
                parameter_form=String(title=Title("User")),
            ),
            "password": DictElement(
                required=True,
                parameter_form=Password(
                    title=Title("Password"),
                    help_text=Help(
                        "This password will be saved in plain text on the configured hosts."
                    ),
                ),
            ),
        },
    )


def _mssql_tls() -> Dictionary:
    return Dictionary(
        title=Title("TLS"),
        help_text=Help("Contains information about TLS file location on host"),
        elements={
            "client_certificate": DictElement(
                parameter_form=String(
                    title=Title("User certificate path"),
                    help_text=Help(
                        "Path to the user certificate. If the path does not exist "
                        "or is empty, the user certificate will not be used."
                    ),
                ),
            ),
        },
    )


def _mssql_authentication() -> CascadingSingleChoice:
    return CascadingSingleChoice(
        title=Title("Authentication"),
        elements=_mssql_authentication_choices(),
        prefill=DefaultValue("local"),
    )


def _mssql_connection() -> Dictionary:
    return Dictionary(
        title=Title("Connection"),
        ignored_elements=("fail_over_partner",),
        elements={
            "hostname": DictElement(
                parameter_form=String(
                    title=Title("Host name"),
                    help_text=Help(
                        "The host name or IP address for the Microsoft SQL Server instance"
                    ),
                    prefill=DefaultValue("localhost"),
                    custom_validate=(validators.LengthInRange(min_value=1),),
                ),
            ),
            "port": DictElement(
                parameter_form=Integer(
                    title=Title("Port"),
                    help_text=Help("Port of the Microsoft SQL Server instance"),
                    prefill=DefaultValue(1433),
                ),
            ),
            "timeout": DictElement(
                parameter_form=Integer(
                    title=Title("Timeout"),
                    help_text=Help("Timeout"),
                    unit_symbol="s",
                    prefill=DefaultValue(5),
                    custom_validate=(validators.NumberInRange(min_value=1),),
                ),
            ),
            "trust_server_certificate": DictElement(
                parameter_form=BooleanChoice(
                    title=Title("Server certificate policy"),
                    help_text=Help("Determines how to treat an invalid certificate"),
                    label=Label("Trust the server certificate"),
                    prefill=DefaultValue(True),
                ),
            ),
            "tls": DictElement(parameter_form=_mssql_tls()),
            "backend": DictElement(
                parameter_form=SingleChoice(
                    title=Title("Monitoring backend"),
                    help_text=Help(
                        "MK-SQL plug-in may use different monitoring backends. "
                        "In some cases you may want to use ODBC backend: typical use cases are "
                        "firewall problems, misconfigured network and for testing purposes"
                    ),
                    elements=[
                        SingleChoiceElement(
                            name="auto",
                            title=Title("Automatically select best type of backend"),
                        ),
                        SingleChoiceElement(
                            name="odbc",
                            title=Title("Use ODBC backend if the plug-in is deployed on Windows"),
                        ),
                    ],
                    prefill=DefaultValue("auto"),
                ),
            ),
            "exclude_databases": DictElement(parameter_form=_mssql_exclude_databases()),
        },
    )


def _get_discovery() -> Dictionary:
    return Dictionary(
        title=Title("Discovery mode of database instances"),
        elements={
            "detect": DictElement(
                required=True,
                parameter_form=BooleanChoice(
                    title=Title("Detect instances"),
                    help_text=Help(
                        "MK SQL plug-in uses different methods to detect MSSQL instances"
                    ),
                    label=Label("Try to detect MSSQL instances present on server"),
                    prefill=DefaultValue(True),
                ),
            ),
            "instances": DictElement(
                required=True,
                parameter_form=CascadingSingleChoice(
                    title=Title("Instances to monitor"),
                    elements=(
                        CascadingSingleChoiceElement(
                            name="exclude",
                            title=Title(
                                "Exclude from monitoring following database instances "
                                "(if detected or manually added)"
                            ),
                            parameter_form=List(
                                element_template=String(
                                    custom_validate=(validators.LengthInRange(min_value=1),)
                                ),
                                custom_validate=(validators.LengthInRange(min_value=1),),
                            ),
                        ),
                        CascadingSingleChoiceElement(
                            name="all",
                            title=Title("Monitor all instances detected and manually added"),
                            parameter_form=FixedValue(value=None),
                        ),
                        CascadingSingleChoiceElement(
                            name="include",
                            title=Title(
                                "Only monitor following database instances "
                                "(if detected or manually added)"
                            ),
                            parameter_form=List(
                                element_template=String(
                                    custom_validate=(validators.LengthInRange(min_value=1),)
                                ),
                                custom_validate=(validators.LengthInRange(min_value=1),),
                            ),
                        ),
                    ),
                    prefill=DefaultValue("all"),
                ),
            ),
        },
    )


def _mssql_piggyback() -> Dictionary:
    return Dictionary(
        title=Title("Map data to specific host (Piggyback)"),
        elements={
            "hostname": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("Host to which the data will be assigned"),
                    custom_validate=(validators.LengthInRange(min_value=1),),
                ),
            ),
            "sections": DictElement(parameter_form=_mssql_sections()),
            "cache_age": DictElement(parameter_form=_mssql_cache_age()),
        },
    )


def _get_custom_instances() -> List[Mapping[str, object]]:
    return List(
        title=Title("Custom instances"),
        element_template=Dictionary(
            elements={
                "sid": DictElement(
                    required=True,
                    parameter_form=String(
                        title=Title("Instance"),
                        help_text=Help("Name of Microsoft SQL Server instance"),
                        custom_validate=(validators.LengthInRange(min_value=1),),
                    ),
                ),
                "auth": DictElement(parameter_form=_mssql_authentication()),
                "conn": DictElement(parameter_form=_mssql_connection()),
                "alias": DictElement(
                    parameter_form=String(title=Title("Alias"), help_text=Help("Alias")),
                ),
                "piggyback": DictElement(parameter_form=_mssql_piggyback()),
            },
        ),
    )


def _get_config(title: Title | None, conn_required: bool) -> Dictionary:
    return Dictionary(
        title=title,
        elements={
            "auth": DictElement(required=True, parameter_form=_mssql_authentication()),
            "conn": DictElement(required=conn_required, parameter_form=_mssql_connection()),
            "sections": DictElement(parameter_form=_mssql_sections()),
            "cache_age": DictElement(parameter_form=_mssql_cache_age()),
            "piggyback_host": DictElement(parameter_form=_mssql_piggyback_host()),
            "discovery": DictElement(parameter_form=_get_discovery()),
            "instances": DictElement(parameter_form=_get_custom_instances()),
            "options": DictElement(parameter_form=_get_options()),
        },
    )


def _get_options() -> Dictionary:
    return Dictionary(
        title=Title("Options"),
        elements={
            "max_connections": DictElement(
                parameter_form=Integer(
                    title=Title("Max allowed connections"),
                    help_text=Help("Maximal count of connections to the SQL server"),
                    prefill=DefaultValue(6),
                    custom_validate=(validators.NumberInRange(min_value=1),),
                ),
            ),
            "ignore_inactive_local_instances": DictElement(
                parameter_form=BooleanChoice(
                    title=Title("Ignore inactive local instances (Windows)"),
                    help_text=Help(
                        "If enabled, the plug-in will not attempt to connect to "
                        "locally detected instances that are currently stopped. "
                        "Only applicable for Windows."
                    ),
                    label=Label("Skip local instances that are not running"),
                ),
            ),
        },
    )


def _valuespec_agent_config_mk_ms_sql() -> Dictionary:
    return Dictionary(
        help_text=Help(
            "This plug-in can be used to collect information of all running MSSQL servers "
            "on the local and remote system. "
        ),
        migrate=migrate,
        elements={
            "deployment": DictElement(
                required=True,
                parameter_form=CascadingSingleChoice(
                    title=Title("Deployment type"),
                    elements=(
                        CascadingSingleChoiceElement(
                            name="sync",
                            title=Title("Deploy the MSSQL Server plug-in"),
                            parameter_form=FixedValue(value=None),
                        ),
                        CascadingSingleChoiceElement(
                            name="do_not_deploy",
                            title=Title("Do not deploy the MSSQL Server plug-in"),
                            parameter_form=FixedValue(value=None),
                        ),
                    ),
                    prefill=DefaultValue("sync"),
                ),
            ),
            "main": DictElement(
                parameter_form=_get_config(Title("Monitor databases"), conn_required=False),
            ),
            "other": DictElement(
                parameter_form=List(
                    title=Title("Monitor databases on other hosts"),
                    add_element_label=Label("Add config to monitor MS SQL database on other hosts"),
                    remove_element_label=Label("Remove config"),
                    element_template=_get_config(None, conn_required=True),
                ),
            ),
        },
    )


rule_spec_mk_ms_sql = AgentConfig(
    title=Title("Microsoft SQL Server (Linux, Windows)"),
    name="mk_ms_sql",
    topic=Topic.DATABASES,
    parameter_form=_valuespec_agent_config_mk_ms_sql,
)
