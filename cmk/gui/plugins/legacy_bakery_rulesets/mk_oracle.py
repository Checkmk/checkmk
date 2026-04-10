#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

from collections.abc import Callable, Sequence
from typing import Any, Literal, NamedTuple

from cmk.gui.agent_bakery import RulespecGroupMonitoringAgentsAgentPlugins
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.type_defs import Choices
from cmk.gui.valuespec import (
    AbsoluteDirname,
    Age,
    CascadingDropdown,
    Dictionary,
    DropdownChoice,
    FixedValue,
    Hostname,
    ID,
    Integer,
    ListChoice,
    ListOf,
    ListOfStrings,
    Migrate,
    NetworkPort,
    TextInput,
    Transform,
    Tuple,
)
from cmk.gui.valuespec.definitions import DictionaryEntry
from cmk.gui.wato import MigrateToIndividualOrStoredPassword
from cmk.utils.rulesets.definition import RuleGroup


def _validate_oracle_password(forbidden_chars: str) -> Callable[[tuple[str, str], str], None]:
    """Create a validator for oracle password with forbidden characters

    Validates only the explicit password entry, not password store references.
    """

    def _validate(value: tuple[str, str], varprefix: str) -> None:
        mode, password = value
        if mode == "password":
            # Only validate direct password entry, not password store references
            for char in forbidden_chars:
                if char in password:
                    raise ValueError(_("The password contains forbidden character: %s") % char)

    return _validate


UNIX_ONLY = "(Linux/AIX/Solaris only)"
WINDOWS_ONLY = "(Windows only)"


class Section(NamedTuple):
    name: str
    default_value: Literal["sync", "async"] | None
    title: str


class SectionWithHelp(NamedTuple):
    name: str
    default_value: Literal["sync", "async"] | None
    title: str
    help: str


def _agent_config_mk_oracle_oracle_section_choices() -> list[DictionaryEntry]:
    dict_elements: list[DictionaryEntry] = []
    for section in _agent_config_mk_oracle_oracle_sections():
        choices: Choices = [("sync", _("Run synchronously"))]
        if section.name not in ["instance", "asm:instance"]:
            choices += [
                ("async", _("Run asynchronously and cached")),
                (None, _("disable this section")),
            ]
        dict_elements.append(
            (
                section.name,
                DropdownChoice[str | None](
                    title=section.title,
                    choices=choices,
                    default_value=section.default_value,
                    help=section.help if isinstance(section, SectionWithHelp) else None,
                ),
            )
        )
    return dict_elements


def _agent_config_mk_oracle_oracle_sections() -> Sequence[Section | SectionWithHelp]:
    return [
        Section("instance", "sync", _("General instance status")),
        Section("performance", "sync", _("Performance")),
        SectionWithHelp(
            "iostats",
            None,
            _("Performance: IO stats"),
            _(
                "Warning: This section will increase the load of your Checkmk server and "
                "may increase the load of your database. "
                "To see results, you also have to activate 'Create additional service for IO stats bytes' or "
                "'Create additional service for IO stats requests' in 'Oracle performance discovery'."
            ),
        ),
        Section("processes", "sync", _("Current number of processes")),
        Section("sessions", "sync", _("Current number of sessions")),
        Section("longactivesessions", "sync", _("Long active sessions")),
        Section("logswitches", "sync", _("Logswitches")),
        Section("undostat", "sync", _("Undo statistics")),
        Section("recovery_area", "sync", _("Recovery area")),
        Section("recovery_status", "sync", _("Recovery status")),
        Section("dataguard_stats", "sync", _("Dataguard statistics")),
        Section("tablespaces", "async", _("Tablespaces")),
        Section("ts_quotas", None, _("TS quotas (not used)")),
        Section("rman", "async", _("RMAN backups")),
        Section("jobs", "async", _("Scheduled jobs")),
        Section("resumable", "async", _("Resumables")),
        Section("locks", "async", _("Locks")),
        Section("systemparameter", "sync", _("System parameters")),
        Section("asm:instance", "sync", _("ASM - General instance status")),
        Section("asm:processes", "sync", _("ASM - Processes")),
        Section("asm:asm_diskgroup", "async", _("ASM - Disk groups")),
    ]


def _agent_config_mk_oracle_oracle_auth_choices(title: str, asm: bool) -> Dictionary:
    as_choices: Choices = []
    if not asm:
        as_choices.append((None, _("normal connection")))
    as_choices += [
        ("sysdba", _("sysdba")),
        ("sysdg", _("sysdg")),
        ("sysoper", _("sysoper")),
    ]
    if asm:
        as_choices.append(("sysasm", _("sysasm")))
    return Dictionary(
        title=title,
        elements=[
            (
                "auth",
                CascadingDropdown(
                    title=_("Authentication method"),
                    choices=[
                        (
                            "explicit",
                            _("Login with the following credentials"),
                            Tuple(
                                elements=[
                                    TextInput(
                                        title=_("User"),
                                        size=30,
                                        allow_empty=False,
                                    ),
                                    MigrateToIndividualOrStoredPassword(
                                        title=_("Password"),
                                        size=16,
                                        allow_empty=False,
                                        validate=_validate_oracle_password(":$'\""),
                                    ),
                                ]
                            ),
                        ),
                        ("wallet", _("Use manually created Oracle password wallet")),
                    ],
                ),
            ),
            (
                "as",
                DropdownChoice(
                    title=_("login as role"),
                    choices=as_choices,
                ),
            ),
            (
                "host",
                Hostname(
                    title=_("Host name or IPv4 address for listener"),
                    default_value="localhost",
                ),
            ),
            (
                "port",
                NetworkPort(
                    title=_("TCP-Port for Listener"),
                    default_value=1521,
                ),
            ),
            (
                "tnsalias",
                TextInput(
                    title=_("TNS Alias %s") % UNIX_ONLY,
                    allow_empty=True,
                ),
            ),
        ],
    )


def _migrate_oracle_sections(value: object) -> object:
    if isinstance(value, dict) and "iostats" not in value:
        value["iostats"] = None
    return value


def _valuespec_agent_config_mk_oracle() -> Dictionary:
    return Dictionary(
        title=_("Oracle databases (Linux, Solaris, AIX, Windows)"),
        help=_(
            "This will deploy the agent plug-in <tt>mk_oracle</tt> on your target system. "
            "Currently not all options are available in all operating systems.<br>"
            "<b>Note:</b> This plugin cannot be used together with the "
            "'Unified Oracle Plugin (Beta)'. Please configure only one of the two."
        ),
        elements=[
            (
                "activated",
                DropdownChoice(
                    title=_("Activation"),
                    help=_(
                        "Do not forget to activate the plug-in in at least one of your rules. "
                        "It can be useful to create rules that are only partially filled out. "
                        "Since the rule execution is done on a <i>per parameter</i> base "
                        "you can for example create one rule at the top of your list that "
                        "just sets the activation to <i>no</i> for just some of your hosts without "
                        "setting any of the other parameters."
                    ),
                    choices=[
                        (False, _("Do not deploy Oracle databases plug-in")),
                        (True, _("Deploy Oracle databases plug-in")),
                    ],
                    default_value=True,
                ),
            ),
            (
                "xinetd_or_systemd",
                CascadingDropdown(
                    title=_("Host uses xinetd or systemd %s") % UNIX_ONLY,
                    choices=[
                        ("xinetd", _("xinetd"), FixedValue(None, totext="")),
                        (
                            "systemd",
                            _("systemd"),
                            Age(
                                label=_("Interval"),
                                help=_(
                                    "The interval the plug-in is triggered by"
                                    " check-mk-agent-async.service"
                                ),
                                default_value=60,
                            ),
                        ),
                    ],
                    sorted=False,
                    default_value="xinetd",
                ),
            ),
            (
                "login",
                _agent_config_mk_oracle_oracle_auth_choices(_("Login Defaults"), asm=False),
            ),
            (
                "login_exceptions",
                ListOf(
                    valuespec=Tuple(
                        elements=[
                            ID(
                                title=_("SID"),
                                allow_empty=False,
                                size=12,
                            ),
                            _agent_config_mk_oracle_oracle_auth_choices(
                                _("Authentication"), asm=False
                            ),
                        ]
                    ),
                    title=_("Login for selected databases"),
                ),
            ),
            (
                "login_asm",
                _agent_config_mk_oracle_oracle_auth_choices(_("Login for ASM"), asm=True),
            ),
            (
                "sids",
                CascadingDropdown(
                    title=_("Instances to monitor"),
                    choices=[
                        (None, _("Monitor all instances found")),
                        (
                            "only",
                            _("Only query the following SIDs (if found)"),
                            ListOfStrings(
                                size=12,
                                orientation="horizontal",
                            ),
                        ),
                        (
                            "skip",
                            _("Skip the following SIDs (if found)"),
                            ListOfStrings(
                                size=12,
                                orientation="horizontal",
                            ),
                        ),
                        (
                            "exclude",
                            _("Exclude the following SIDs (if found)"),
                            ListOfStrings(
                                size=12,
                                orientation="horizontal",
                            ),
                        ),
                    ],
                ),
            ),
            (
                "tnsalias_pre_postfix",
                CascadingDropdown(
                    title=_("Add pre or postfix to TNSALIASes %s") % UNIX_ONLY,
                    choices=[
                        (
                            "all_sids",
                            _("For all SIDs"),
                            Tuple(
                                elements=[
                                    TextInput(title=_("Prefix")),
                                    TextInput(title=_("Postfix")),
                                ]
                            ),
                        ),
                        (
                            "per_sid",
                            _("For specific SIDs"),
                            ListOf(
                                valuespec=Tuple(
                                    title=_("Pre-/Postfix for TNSALIAS"),
                                    elements=[
                                        TextInput(
                                            title=_("SID"),
                                        ),
                                        TextInput(
                                            title=_("Prefix"),
                                        ),
                                        TextInput(
                                            title=_("Postfix"),
                                        ),
                                    ],
                                )
                            ),
                        ),
                    ],
                ),
            ),
            (
                "sections",
                Migrate(
                    valuespec=Dictionary(
                        title=_("Sections - data to collect"),
                        columns=2,
                        elements=_agent_config_mk_oracle_oracle_section_choices(),
                        optional_keys=False,
                    ),
                    migrate=_migrate_oracle_sections,
                ),
            ),
            (
                "excluded_sections",
                ListOf(
                    valuespec=Tuple(
                        elements=[
                            ID(
                                title=_("SID"),
                                size=12,
                                allow_empty=False,
                            ),
                            ListChoice(
                                title=_("Sections to exclude"),
                                choices=[
                                    (i[0], i[2])
                                    for i in _agent_config_mk_oracle_oracle_sections()
                                    if not i[0].startswith("asm:") and i[0] != "instance"
                                ],
                            ),
                        ],
                    ),
                    add_label=_("Add exclusion"),
                    title=_("Exclude some sections on certain instances"),
                ),
            ),
            (
                "async_interval",
                Age(
                    title=_("Cache age for background checks"),
                    help=_(
                        "The data for the background checks is recomputed at most in this interval."
                    ),
                    default_value=600,
                ),
            ),
            (
                "sqlnet_send_timeout",
                Age(
                    title=_("Sqlnet Send timeout"),
                    minvalue=1,
                    maxvalue=65535,
                    default_value=30,
                ),
            ),
            (
                "remote_instances",
                ListOf(
                    valuespec=Dictionary(
                        optional_keys=["piggyhost"],
                        elements=[
                            (
                                "id",
                                CascadingDropdown(
                                    title=_("Unique ID"),
                                    orientation="horizontal",
                                    choices=[
                                        ("piggyhost", _("Use monitoring host name")),
                                        ("sid", _("Use the remote SID")),
                                        (
                                            "explicit",
                                            _("Use the following ID"),
                                            ID(size=12),
                                        ),
                                    ],
                                ),
                            ),
                            (
                                "piggyhost",
                                Hostname(
                                    title=_("Monitoring host this database should be mapped to"),
                                    help=_(
                                        "If you leave this empty then the database will appear on the host "
                                        "where the <tt>mk_oracle</tt> plug-in is running. In this case the "
                                        "SIDs of all monitored databases must be unique."
                                    ),
                                ),
                            ),
                            (
                                "sid",
                                ID(
                                    title=_("Oracle SID of the remote database"),
                                    allow_empty=False,
                                    size=12,
                                    default_value="OACL",
                                ),
                            ),
                            (
                                "host",
                                TextInput(
                                    title=_("DNS host name or IP address of database server"),
                                    allow_empty=False,
                                ),
                            ),
                            (
                                "port",
                                Integer(
                                    title=_("TCP port number"),
                                    minvalue=1,
                                    maxvalue=65535,
                                    default_value=1521,
                                ),
                            ),
                            (
                                "release",
                                DropdownChoice(
                                    title=_("Oracle release of the remote database"),
                                    choices=[
                                        ("9.2", "9.2"),
                                        ("10.1", "10.1"),
                                        ("10.2", "10.2"),
                                        ("11.1", "11.1"),
                                        ("11.2", "11.2"),
                                        ("12.1", _("12.1 or newer")),
                                    ],
                                ),
                            ),
                            (
                                "tnsalias",
                                TextInput(
                                    title=_("TNS Alias %s") % UNIX_ONLY,
                                    allow_empty=True,
                                ),
                            ),
                        ],
                    ),
                    title=_("Remote sites %s") % UNIX_ONLY,
                    help=_(
                        "You can monitor database instances that are hosted on another server. This can be "
                        "helpful if you want to monitoring Oracle databases on Windows without deploying the "
                        "mk_oracle plug-in for Windows. For each remote instance you need to specify a unique "
                        "ID. This can be the same as the SID. This ID is then being used as a reference "
                        "in the other configuration - for example for the <i>Login for selected databases</i> "
                        "and for <i>Sections to exclude</i>."
                    ),
                    add_label=_("Add remote site"),
                    movable=False,
                ),
            ),
            (
                "remote_oracle_home",
                AbsoluteDirname(
                    title=_("<tt>ORACLE_HOME</tt> to use for remote access %s") % UNIX_ONLY,
                    help=_(
                        "Here you can specify an <tt>ORACLE_HOME</tt> for the access to the "
                        "remote databases. Omitting this empty will fall back to the system "
                        "<tt>ORACLE_HOME</tt>."
                    ),
                    size=40,
                ),
            ),
            (
                "tns_admin",
                AbsoluteDirname(
                    title=_(
                        "<tt>TNS_ADMIN</tt> to use for <tt>sqlnet.ora</tt> and <tt>tnsnames.ora</tt> %s"
                    )
                    % UNIX_ONLY,
                    help=_(
                        "Here you can specify an <tt>TNS_ADMIN</tt> for the access to the "
                        "configuration files <tt>sqlnet.ora</tt> and <tt>tnsnames.ora</tt>. "
                        "Omitting this empty will fall back to <tt>/etc/check_mk</tt>."
                    ),
                    size=40,
                ),
            ),
            (
                "sqlnet_ora_group",
                TextInput(
                    title=_("<tt>sqlnet.ora</tt> permission group %s") % UNIX_ONLY,
                    help=_(
                        "mk_oracle for Linux will change to an unprivileged user before executing any "
                        "Oracle binaries. This means that <tt>sqlnet.ora</tt> (which is created by the Bakery) "
                        "has to be readable by this user. At runtime the agent uses the owner of the "
                        "Oracle binary as the user to switch to. But we don't know this user nor their "
                        "groups at agent installation time. You have to explicitly configure a group here, "
                        "so the user can read <tt>sqlnet.ora</tt>. For a default Oracle installation "
                        "<tt>oinstall</tt> can be used."
                    ),
                ),
            ),
            (
                "validate_permissions",
                CascadingDropdown(
                    title=_("Oracle binaries permissions check %s") % WINDOWS_ONLY,
                    help=_(
                        "Due to security reasons the plug-in being executed as admin will check "
                        "permissions for Oracle executables. If the modification of Oracle binaries "
                        "is allowed for non-admin users or groups then the plug-in stops processing "
                        "thus breaking Oracle monitoring: execution of normal user code at "
                        "elevated level means security vulnerability. "
                        "You may <tt>disable</tt> this option if it is the only method to "
                        "continue monitoring the Oracle database. "
                        "Usually you need to <tt>disable</tt> the option only in the following case: "
                        "It's impossible to correctly adjust permissions for Oracle binaries, "
                        "mode group with group Administrator is not applicable and "
                        "it is not possible to use a custom account to monitor the Oracle database. "
                        "Even if the check is enabled you may allow some groups and/or users to "
                        "still have write access to the Oracle binaries."
                    ),
                    choices=[
                        (
                            "enable",
                            _("Enable"),
                            Dictionary(
                                elements=[
                                    (
                                        "groups_and_users_white_list",
                                        ListOf(
                                            valuespec=TextInput(
                                                title=_(
                                                    "Groups and/or users in format domain\\name"
                                                ),
                                                empty_text="Group or user",
                                                size=70,
                                                allow_empty=False,
                                            ),
                                            add_label=_("Add group or user"),
                                            title=_(
                                                "Groups and/or users allowed to have write access to Oracle binaries"
                                            ),
                                            help=_(
                                                "Add here only groups and users which do not have administrator "
                                                "rights but, for some reason, must have write access to the Oracle "
                                                "binaries. For example, it may be a dedicated installer account in "
                                                "a domain. The values are case insensitive."
                                            ),
                                        ),
                                    ),
                                ]
                            ),
                        ),
                        ("disable", _("Disable")),
                    ],
                    default_value=("enable", {"groups_and_users_white_list": []}),
                ),
            ),
        ],
    )


# TODO(sk): add to this function patching code for security checks or remove it all
# Lack of typing below is intentional: this code will die with 2.2
def _adjust_security_check(_config: dict[str, Any]) -> dict[str, Any]:
    # if config contains permission_check -> do nothing
    # if config is old -> set permission_check to disabled
    # if config is new -> do nothing
    # Not clear how distinct new config without permission_check from old config
    # probably, hidden_keys or smth like should help
    return _config


def _adjusted_valuespec_agent_config_mk_oracle() -> Transform:
    return Transform(
        _valuespec_agent_config_mk_oracle(),
        to_valuespec=_adjust_security_check,
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringAgentsAgentPlugins,
        match_type="dict",
        name=RuleGroup.AgentConfig("mk_oracle"),
        valuespec=_adjusted_valuespec_agent_config_mk_oracle,
    )
)
