#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

from typing import Any, Final, Literal

from cmk.gui.agent_bakery import RulespecGroupMonitoringAgentsAgentPlugins
from cmk.gui.exceptions import MKUserError
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.type_defs import Choices
from cmk.gui.valuespec import (
    Alternative,
    CascadingDropdown,
    CascadingDropdownChoice,
    Checkbox,
    Dictionary,
    DropdownChoice,
    FixedValue,
    Hostname,
    Integer,
    ListOf,
    ListOfStrings,
    Migrate,
    TextInput,
    Transform,
    Tuple,
    ValueSpec,
)
from cmk.gui.wato import MigrateToIndividualOrStoredPassword
from cmk.utils.rulesets.definition import RuleGroup

_SectionMode = Literal["sync", "async"] | None
_Sections = list[tuple[str, DropdownChoice[_SectionMode]]]

# must be identical to the values in the bakery
_SYSTEM_DATABASES: Final[tuple[str, str, str, str]] = ("model", "master", "msdb", "tempdb")


def _sections_selector() -> _Sections:
    dict_elements: _Sections = []
    for name, value, title in _mssql_sections_info():
        choices: Choices = [("sync", _("Run synchronously"))]
        if name not in ["instance"]:
            choices += [
                ("async", _("Run asynchronously and cached")),
                (None, _("disable this section")),
            ]
        dict_elements.append(
            (
                name,
                DropdownChoice[_SectionMode](
                    title=title,
                    choices=choices,
                    default_value=value,
                ),
            )
        )
    return dict_elements


def _mssql_sections_info() -> list[tuple[str, _SectionMode, str]]:
    return [
        ("instance", "sync", _("General instance status")),
        ("databases", "sync", _("Databases")),
        ("counters", "sync", _("Counters")),
        ("blocked_sessions", "sync", _("Blocked sessions")),
        ("transactionlogs", "sync", _("Transaction Logs")),
        ("clusters", "sync", _("Clusters")),
        ("mirroring", "sync", _("Mirroring")),
        ("availability_groups", "sync", _("Availability groups")),
        ("connections", "sync", _("Connections")),
        ("tablespaces", "async", _("Table spaces")),
        ("datafiles", "async", _("Datafiles")),
        ("backup", "async", _("Backups")),
        ("jobs", "async", _("Scheduled Jobs")),
    ]


def _migrate_sections(value: dict[str, Any]) -> dict[str, Any]:
    def _correct_name(name: str) -> str:
        if name == "transactionslog":
            return "transactionlogs"
        return name

    return {_correct_name(k): v for k, v in value.items()}


def _mssql_sections() -> ValueSpec:
    return Migrate(
        valuespec=Dictionary(
            title=_("Data to collect (sections)"),
            columns=2,
            elements=_sections_selector(),
            optional_keys=False,
        ),
        migrate=_migrate_sections,
    )


def _to_vs(config_data: list[str] | None) -> tuple[bool, bool, bool, bool]:
    if config_data is None:
        return False, False, False, False
    value_set = set(config_data)
    return (
        _SYSTEM_DATABASES[0] in value_set,
        _SYSTEM_DATABASES[1] in value_set,
        _SYSTEM_DATABASES[2] in value_set,
        _SYSTEM_DATABASES[3] in value_set,
    )


def _from_vs(value_spec_data: tuple[bool, bool, bool, bool]) -> list[str]:
    return [name for on, name in zip(value_spec_data, _SYSTEM_DATABASES) if on]


def _mssql_exclude_databases() -> ValueSpec:
    # need Transform to keep the values in config sane: list of names
    # Tuple of checkbox due to limits of valuespec and requirement to port in 2.3
    return Transform(
        Tuple(
            title="Exclude system databases",
            elements=[
                Checkbox(title=name.capitalize(), true_label=name, false_label="~")
                for name in _SYSTEM_DATABASES
            ],
        ),
        to_valuespec=_to_vs,
        from_valuespec=_from_vs,
    )


def _mssql_cache_age() -> Integer:
    return Integer(
        title=_("Cache age for asynchronous checks"), minvalue=10, maxvalue=14400, default_value=600
    )


def _mssql_piggyback_host() -> TextInput:
    return Hostname(
        title=_("Map data to specific host (piggyback)"),
    )


def _mssql_authentication_choices() -> list[CascadingDropdownChoice]:
    return [
        ("local", _("Local integrated authentication (Windows)")),
        (
            "remote",
            _("SQL database user credentials"),
            _mssql_authentication_remote(),
        ),
    ]


def _mssql_authentication_remote() -> Tuple:
    return Tuple(
        elements=[
            TextInput(
                title=_("User"),
                default_value="",
            ),
            MigrateToIndividualOrStoredPassword(
                title=_("Password"),
                help=_("This password will be saved in plain text on the configured hosts."),
            ),
        ]
    )


def _mssql_tls() -> Dictionary:
    return Dictionary(
        title=_("TLS"),
        help=_("Contains information about TLS file location on host"),
        elements=[
            (
                "client_certificate",
                TextInput(
                    title=_("User certificate path"),
                    help=_(
                        "Path to the user certificate. "
                        "If the path is not exist or empty, the user certificate will not be used."
                    ),
                    default_value="",
                ),
            ),
        ],
    )


def _mssql_authentication() -> CascadingDropdown:
    return CascadingDropdown(
        title=_("Authentication"),
        choices=_mssql_authentication_choices(),
    )


def _mssql_connection() -> Dictionary:
    return Dictionary(
        title="Connection",
        ignored_keys=["fail_over_partner"],
        elements=[
            (
                "hostname",
                Hostname(
                    title=_("Host name"),
                    allow_empty=False,
                    default_value="localhost",
                    help=_("The host name or IP address for the Microsoft SQL Server instance"),
                ),
            ),
            (
                "port",
                Integer(
                    title=_("Port"),
                    default_value=1433,
                    help=_("Port of the Microsoft SQL Server instance"),
                ),
            ),
            (
                "timeout",
                Integer(
                    title=_("Timeout"),
                    default_value=5,
                    help=_("Timeout"),
                    minvalue=1,
                    unit=_("seconds"),
                ),
            ),
            (
                "trust_server_certificate",
                DropdownChoice(
                    title=_("Server certificate policy"),
                    help=_("Determines how to treat invalid certificate"),
                    choices=[
                        (True, _("Trust")),
                        (False, _("Do not trust")),
                    ],
                ),
            ),
            (
                "tls",
                _mssql_tls(),
            ),
            (
                "backend",
                DropdownChoice(
                    title=_("Monitoring backend"),
                    help=_(
                        "MK SQL plug-in may use different monitoring backends. "
                        "In some cases you may want to use ODBC backend: typical use cases are firewall problems, "
                        "misconfigured network and for testing purposes"
                    ),
                    choices=[
                        ("auto", _("Automatically select best type of back-end")),
                        ("odbc", _("Use ODBC backend if the plug-in is deployed on Windows")),
                    ],
                ),
            ),
            (
                "exclude_databases",
                _mssql_exclude_databases(),
            ),
        ],
    )


def _get_discovery() -> Tuple:
    return Tuple(
        title="Discovery mode of database instances",
        elements=[
            Checkbox(
                title=_("Detect instances"),
                label=_("Try to detect MSSQL instances present on server"),
                help=_("MK-SQL plug-in uses different methods to detect MSSQL instances"),
                default_value=True,
            ),
            CascadingDropdown(
                title=_("Instances to monitor"),
                sorted=False,
                choices=[
                    (
                        "exclude",
                        _(
                            "Exclude from monitoring following database instances (if detected or manually added)"
                        ),
                        ListOfStrings(
                            size=12,
                            orientation="horizontal",
                            allow_empty=False,
                        ),
                    ),
                    ("all", _("Monitor all instances detected and manually added")),
                    (
                        "include",
                        _(
                            "Only monitor following database instances (if detected or manually added)"
                        ),
                        ListOfStrings(
                            size=12,
                            orientation="horizontal",
                            allow_empty=False,
                        ),
                    ),
                ],
            ),
        ],
    )


def _mssql_piggyback() -> Dictionary:
    return Dictionary(
        title="Map data to specific host (Piggyback)",
        elements=[
            (
                "hostname",
                Hostname(
                    title=_("Host to which the data will be assigned"),
                    default_value="",
                    allow_empty=False,
                ),
            ),
            (
                "sections",
                _mssql_sections(),
            ),
            (
                "cache_age",
                _mssql_cache_age(),
            ),
        ],
        required_keys=["piggyback_host"],
    )


def _get_custom_instances() -> ListOf:
    return ListOf(
        title="Custom instances",
        valuespec=Dictionary(
            elements=[
                (
                    "sid",
                    TextInput(
                        title=_("Instance"),
                        allow_empty=False,
                        help=_("Name of Microsoft SQL Server instance"),
                    ),
                ),
                (
                    "auth",
                    _mssql_authentication(),
                ),
                (
                    "conn",
                    _mssql_connection(),
                ),
                (
                    "alias",
                    TextInput(
                        title=_("Alias"),
                        allow_empty=True,
                        help=_("Alias"),
                    ),
                ),
                (
                    "piggyback",
                    _mssql_piggyback(),
                ),
            ],
            required_keys=["sid"],
        ),
    )


def _get_config() -> list[tuple[str, ValueSpec]]:
    return [
        (
            "auth",
            _mssql_authentication(),
        ),
        (
            "conn",
            _mssql_connection(),
        ),
        (
            "sections",
            _mssql_sections(),
        ),
        (
            "cache_age",
            _mssql_cache_age(),
        ),
        (
            "piggyback_host",
            _mssql_piggyback_host(),
        ),
        (
            "discovery",
            _get_discovery(),
        ),
        (
            "instances",
            _get_custom_instances(),
        ),
        (
            "options",
            Dictionary(
                title=_("Options"),
                elements=_get_options(),
                required_keys=[],
            ),
        ),
    ]


def validate_max_connections(count: int, varprefix: str) -> None:
    if count < 1:
        raise MKUserError(varprefix, _("Value should be positive"))


def _get_options() -> list[tuple[str, ValueSpec]]:
    return [
        (
            "max_connections",
            Integer(
                title=_("Max allowed connections"),
                default_value=6,
                validate=validate_max_connections,
                help=_("Maximal count of connections to the SQL server"),
            ),
        ),
    ]


def _valuespec_agent_config_mk_ms_sql() -> Alternative:
    return Alternative(
        title=_("Microsoft SQL Server (Linux, Windows)"),
        help=_(
            "This plug-in can be used to collect information of all running MSSQL servers "
            "on the local and remote system. "
        ),
        elements=[
            Dictionary(
                title="Deploy MSSQL Server plug-in",
                required_keys=["main"],
                # optional_keys = ["suppl"],
                # title_br=False,
                elements=[
                    (
                        "main",
                        Dictionary(
                            title=_("Monitor databases"),
                            elements=_get_config(),
                            required_keys=["auth"],
                        ),
                    ),
                    (
                        "other",
                        ListOf(
                            title=_("Monitor databases on other hosts"),
                            add_label="Add config to monitor MS SQL database on other hosts",
                            del_label="Remove config",
                            valuespec=Dictionary(
                                elements=_get_config(),
                                required_keys=["auth", "conn"],
                            ),
                        ),
                    ),
                ],
            ),
            FixedValue(
                value=None,
                title=_("Do not deploy MSSQL Server plug-in"),
                totext=_("(disabled)"),
            ),
        ],
        default_value={"main": {"auth": "local"}},
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringAgentsAgentPlugins,
        name=RuleGroup.AgentConfig("mk_ms_sql"),
        valuespec=_valuespec_agent_config_mk_ms_sql,
    )
)
