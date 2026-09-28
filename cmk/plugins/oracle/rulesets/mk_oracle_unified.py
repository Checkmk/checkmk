#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator, Mapping, Sequence
from typing import Final, Literal

from pydantic import BaseModel

from cmk.rulesets.internal.form_specs import (
    DictGroupExtended,
    DictionaryExtended,
    DictionaryGroupLayout,
    ListOfStrings,
    ListOfStringsLayout,
)
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
    MultipleChoice,
    MultipleChoiceElement,
    NoGroup,
    Password,
    SingleChoice,
    SingleChoiceElement,
    String,
    TimeMagnitude,
    TimeSpan,
    validators,
)
from cmk.rulesets.v1.rule_specs import AgentConfig, Topic

# Matches absolute paths on Unix (/...), env var references ($VAR or ${VAR}),
# and absolute Windows paths (C:\... or C:/...).
USE_HOST_CLIENT_PATH_RE = r"^(/|\$[\w{]|[a-zA-Z]:[/\\]).*"


def _group(title: Title, help_text: Help | None = None) -> DictGroupExtended:
    return DictGroupExtended(
        title=title,
        help_text=help_text,
        layout=DictionaryGroupLayout.vertical,
    )


_ACTIVATION: Final = _group(Title("Activation"))
_WHICH_INSTANCES: Final = _group(Title("Instances to monitor"))
_STANDARD_SETTINGS: Final = _group(
    Title("Standard settings for all instances"),
    Help("Used for every monitored database unless the database overrides it below."),
)
_MONITORING_OPTIONS: Final = _group(Title("Monitoring options"))
_CLIENT_OPTIONS: Final = _group(Title("Oracle client options"))
_PLUGIN_BEHAVIOR: Final = _group(Title("Plug-in behavior"))
_PER_INSTANCE: Final = _group(
    Title("Instance-specific settings"),
    Help("Override the standard settings above for this database."),
)
# Without a group of its own the entry below would render inside the box the
# preceding group opened, under a heading that does not describe it.
_PER_INSTANCE_MONITORING: Final = _group(Title("Monitoring"))


type _AuthOptions = tuple[str, object]
type _NamedOption = Mapping[str, object]


class SectionOptions(BaseModel):
    section: str
    title: Title
    help_text: Help | None = None
    # use full name because GUI throws error if `async` name is used
    mode: Literal["synchronous", "asynchronous", "disabled"]


SECTIONS: Sequence[SectionOptions] = (
    SectionOptions(
        section="instance",
        title=Title("General instance status"),
        mode="synchronous",
    ),
    SectionOptions(
        section="asm_instance",
        title=Title("ASM - General instance status"),
        mode="synchronous",
    ),
    SectionOptions(
        section="asm_diskgroup",
        title=Title("ASM - Disk groups"),
        mode="asynchronous",
    ),
    SectionOptions(
        section="dataguard_stats",
        title=Title("Data Guard statistics"),
        mode="synchronous",
    ),
    SectionOptions(
        section="locks",
        title=Title("Locks"),
        mode="asynchronous",
    ),
    SectionOptions(
        section="logswitches",
        title=Title("Logswitches"),
        mode="synchronous",
    ),
    SectionOptions(
        section="longactivesessions",
        title=Title("Long active sessions"),
        mode="synchronous",
    ),
    SectionOptions(
        section="performance",
        title=Title("Performance"),
        mode="synchronous",
    ),
    SectionOptions(
        section="processes",
        title=Title("Current number of processes"),
        mode="synchronous",
    ),
    SectionOptions(
        section="recovery_area",
        title=Title("Recovery area"),
        mode="synchronous",
    ),
    SectionOptions(
        section="recovery_status",
        title=Title("Recovery status"),
        mode="synchronous",
    ),
    SectionOptions(
        section="sessions",
        title=Title("Current number of sessions"),
        mode="synchronous",
    ),
    SectionOptions(
        section="systemparameter",
        title=Title("System parameters"),
        mode="synchronous",
    ),
    SectionOptions(
        section="undostat",
        title=Title("Undo statistics"),
        mode="synchronous",
    ),
    SectionOptions(
        section="iostats",
        title=Title("Performance: IO stats"),
        help_text=Help(
            "WARNING: This section will increase the load of your Checkmk server and "
            "may increase load of your Database. "
            "To see results, you also have to activate 'Create additional service for "
            "I/O stats bytes' or 'Create additional service for I/O stats requests' "
            "in 'Oracle performance discovery'."
        ),
        mode="disabled",
    ),
    SectionOptions(
        section="jobs",
        title=Title("Scheduled jobs"),
        mode="asynchronous",
    ),
    SectionOptions(
        section="resumable",
        title=Title("Resumables"),
        mode="asynchronous",
    ),
    SectionOptions(
        section="rman",
        title=Title("RMAN backups"),
        mode="asynchronous",
    ),
    SectionOptions(
        section="tablespaces",
        title=Title("Tablespaces"),
        mode="asynchronous",
    ),
)

# These sections report the instance state, which must never be cached or switched off:
# stale data would hide an instance that has just gone down.
SYNC_ONLY_SECTIONS: Final = ("instance", "asm_instance")

BY_SECTION: Final = {section.section: section for section in SECTIONS}

# The order the configurable sections are offered in. Every section that is
# configurable at all needs an entry, which _sections asserts by lookup.
SECTION_ORDER: Final[Sequence[str]] = (
    "performance",
    "iostats",
    "processes",
    "sessions",
    "longactivesessions",
    "locks",
    "tablespaces",
    "asm_diskgroup",
    "recovery_area",
    "undostat",
    "rman",
    "recovery_status",
    "dataguard_stats",
    "logswitches",
    "jobs",
    "resumable",
    "systemparameter",
)


def _auth_roles() -> list[SingleChoiceElement]:
    return [
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
    ]


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
                            title=Title("Oracle wallet"),
                            parameter_form=FixedValue(
                                value=None,
                                label=Label("(credentials come from the Oracle wallet)"),
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
                parameter_form=SingleChoice(
                    title=Title("Role"),
                    help_text=Help(
                        "Specifies the database privilege role used when connecting to Oracle."
                    ),
                    elements=_auth_roles(),
                ),
                required=False,
            ),
            "asm_auth": DictElement(
                required=False,
                parameter_form=Dictionary(
                    title=Title("ASM authentication"),
                    help_text=Help(
                        "Separate credentials for accessing ASM. If omitted, the main "
                        "authentication above is reused."
                    ),
                    elements={
                        "username": DictElement(
                            parameter_form=String(
                                title=Title("ASM username"),
                                custom_validate=(validators.LengthInRange(min_value=1),),
                            ),
                            required=True,
                        ),
                        "password": DictElement(
                            parameter_form=Password(
                                title=Title("ASM Password"),
                                custom_validate=(validators.LengthInRange(min_value=1),),
                            ),
                            required=True,
                        ),
                        "role": DictElement(
                            parameter_form=SingleChoice(
                                title=Title("ASM role"),
                                help_text=Help(
                                    "Specifies the database privilege role used when connecting to Oracle."
                                ),
                                elements=_auth_roles(),
                            ),
                            required=False,
                        ),
                    },
                ),
            ),
        },
    )


def _alias_entry() -> String:
    return String(
        title=Title("Alias"),
        help_text=Help(
            "A TNS alias as defined in the <tt>tnsnames.ora</tt> file. "
            "Requires a properly configured <tt>tnsnames.ora</tt> file accessible "
            "via the TNS_ADMIN directory path."
        ),
        custom_validate=(validators.LengthInRange(min_value=1),),
    )


def _sid_entry() -> String:
    return String(
        title=Title("SID"),
        help_text=Help(
            "The Oracle System Identifier (SID) that identifies "
            "a specific database instance on the host. "
            "Use SID-based connections for older Oracle configurations or "
            "when connecting to a database that does not use service names. "
            "If both a service name and SID are specified, "
            "the service name takes precedence."
        ),
        custom_validate=(validators.LengthInRange(min_value=1),),
    )


def _descriptor_entry() -> Dictionary:
    return Dictionary(
        title=Title("Oracle service name"),
        elements={
            "service_name": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("Service Name"),
                    help_text=Help(
                        "The Oracle service name used to connect to the "
                        "database. A service name typically represents a "
                        "database and can map to one or more instances in "
                        "a RAC environment. "
                        "To monitor a Pluggable Database (PDB), specify its "
                        "service name here — each PDB exposes its own service "
                        "name that can be used to connect to and monitor it "
                        "independently."
                    ),
                ),
            ),
            "instance_name": DictElement(
                required=False,
                parameter_form=String(
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
            "sid": DictElement(
                required=False,
                parameter_form=String(
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
        title=Title("Oracle database identification"),
        elements=[
            CascadingSingleChoiceElement(
                name="alias",
                title=Title("Alias"),
                parameter_form=_alias_entry(),
            ),
            CascadingSingleChoiceElement(
                name="descriptor",
                title=Title("Service Name"),
                parameter_form=_descriptor_entry(),
            ),
            CascadingSingleChoiceElement(
                name="sid",
                title=Title("SID"),
                parameter_form=_sid_entry(),
            ),
        ],
    )


def _connection_options() -> Dictionary:
    return Dictionary(
        title=Title("Connection options"),
        elements={
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
                    unit_symbol="s",
                    prefill=DefaultValue(5),
                ),
                required=False,
            ),
        },
    )


def _oracle_file_paths() -> Mapping[str, DictElement[str]]:
    """The two paths the plug-in reads once per run, not once per database."""
    return {
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
            group=_CLIENT_OPTIONS,
        ),
        "oracle_local_registry": DictElement(
            parameter_form=String(
                title=Title("Oracle local registry path"),
                help_text=Help(
                    "Path to the olr.loc file of Oracle Grid Infrastructure, which "
                    "covers both Oracle Clusterware and Oracle Restart. If not "
                    "specified, /etc/oracle/olr.loc and /var/opt/oracle/olr.loc are "
                    "probed in that order. Once the Grid home named in that file is "
                    "found, the plug-in connects to this node by its own name instead "
                    "of localhost, because a listener under Grid Infrastructure binds "
                    "the node address. The Grid home is also used as the last "
                    "candidate for ORACLE_HOME, since Grid Infrastructure stops "
                    "maintaining oratab from version 12.2 on. Set this to a path that "
                    "does not exist to switch the behavior off."
                ),
                custom_validate=(
                    validators.MatchRegex("^/.*", Message("Please enter an absolute path.")),
                ),
            ),
            required=False,
            group=_CLIENT_OPTIONS,
        ),
    }


def _configurable_sections() -> Iterator[SectionOptions]:
    for name in SECTION_ORDER:
        yield BY_SECTION[name]


def _sections() -> Dictionary:
    return DictionaryExtended(
        title=Title("Sections - data to collect"),
        help_text=Help(
            "Which data to collect, and how often. An unchecked section is not queried "
            "at all. A section marked 'async' is collected by a separate agent plug-in "
            "that runs at the cache age configured above, rather than on every agent "
            "run. The instance status is not listed, because it is always collected on "
            "every agent run: stale data would hide an instance that has just gone down."
        ),
        default_checked=[
            section.section for section in _configurable_sections() if section.mode != "disabled"
        ],
        elements={
            section.section: DictElement(
                required=False,
                parameter_form=BooleanChoice(
                    title=section.title,
                    help_text=section.help_text,
                    label=Label("async"),
                    prefill=DefaultValue(section.mode == "asynchronous"),
                ),
            )
            for section in _configurable_sections()
        },
    )


def _discovery() -> Dictionary:
    return Dictionary(
        title=Title("Instance discovery"),
        help_text=Help(
            "Whether the plug-in looks for local Oracle database instances on its own. "
            "It does so unless this is configured otherwise, and only when it runs on the "
            "machine where the instances are running."
        ),
        elements={
            "enabled": DictElement(
                parameter_form=SingleChoice(
                    title=Title("Local instances"),
                    prefill=DefaultValue("enabled"),
                    elements=[
                        SingleChoiceElement(
                            name="enabled",
                            title=Title("Discover local instances"),
                        ),
                        SingleChoiceElement(
                            name="disabled",
                            title=Title("Monitor only the databases listed below"),
                        ),
                    ],
                ),
                required=True,
            ),
            "include": DictElement(
                parameter_form=ListOfStrings(
                    title=Title("Include patterns"),
                    help_text=Help(
                        "Only instances matching one of these patterns are monitored. "
                        "If no pattern is defined, all of them are."
                    ),
                    string_spec=String(),
                    layout=ListOfStringsLayout.horizontal,
                ),
                required=False,
            ),
            "exclude": DictElement(
                parameter_form=ListOfStrings(
                    title=Title("Exclude patterns"),
                    help_text=Help("Instances matching one of these patterns are not monitored."),
                    string_spec=String(),
                    layout=ListOfStringsLayout.horizontal,
                ),
                required=False,
            ),
        },
    )


def _permissions() -> CascadingSingleChoice:
    return CascadingSingleChoice(
        title=Title("Oracle binaries permissions check"),
        help_text=Help(
            "For security reasons the plug-in checks the permissions of the Oracle client "
            "files it is about to load, because loading them as an administrative user means "
            "executing whoever may write them with those privileges. If they can be modified "
            "from outside the Oracle installation, the plug-in stops processing and Oracle "
            "monitoring breaks. "
            "On Windows the client files may only be writable by privileged accounts "
            "(SYSTEM, the local Administrators group, Domain and Enterprise Admins). "
            "On Linux and UNIX the client library, its directory and their parent "
            "directories may only be writable by <tt>root</tt> or by the conventional Oracle "
            "owner, the user <tt>oracle</tt> and the group <tt>oinstall</tt>, so a standard "
            "installation works unchanged. Oracle software kept under any other account or "
            "group has to be allowed explicitly below. "
            "You may <tt>disable</tt> this option if it is the only way to continue "
            "monitoring the Oracle database - typically when the permissions cannot be "
            "corrected and no dedicated account can be used to monitor it. "
            "Even with the check enabled you may allow specific groups and/or users to have "
            "write access to the Oracle client files."
        ),
        prefill=DefaultValue("enabled"),
        elements=[
            CascadingSingleChoiceElement(
                name="enabled",
                title=Title("Enable"),
                parameter_form=Dictionary(
                    elements={
                        "safe_entries": DictElement(
                            required=False,
                            parameter_form=ListOfStrings(
                                title=Title("Safe groups and/or users"),
                                help_text=Help(
                                    "Account names on Windows, user or group names - or "
                                    "numeric IDs - on Linux and UNIX."
                                ),
                                string_spec=String(),
                                layout=ListOfStringsLayout.horizontal,
                            ),
                        ),
                    }
                ),
            ),
            CascadingSingleChoiceElement(
                name="disabled",
                title=Title("Disable"),
                parameter_form=FixedValue(
                    value=None,
                    label=Label("(client file permissions are not checked)"),
                ),
            ),
        ],
    )


def _use_host_client() -> CascadingSingleChoice:
    return CascadingSingleChoice(
        title=Title("Oracle Instant Client usage"),
        prefill=DefaultValue("auto"),
        help_text=Help(
            "Controls which Oracle Instant Client the plug-in uses to connect to databases. "
            "Two sources are available: "
            "the <b>agent-local client</b> — Oracle Instant Client libraries manually installed "
            "alongside the Checkmk agent under "
            "<tt>$MK_LIBDIR/plugins/libexec/mk-oracle-v2/oic/</tt> — "
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
                parameter_form=FixedValue(
                    value=None,
                    label=Label("(host client first, then the agent-local client)"),
                ),
            ),
            CascadingSingleChoiceElement(
                name="never",
                title=Title("Never use host client (only agent-local client)"),
                parameter_form=FixedValue(
                    value=None,
                    label=Label("(agent-local client only)"),
                ),
            ),
            CascadingSingleChoiceElement(
                name="always",
                title=Title("Always use host client (ignore agent-local client)"),
                parameter_form=FixedValue(
                    value=None,
                    label=Label("(host client only)"),
                ),
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
    )


def _monitoring_options() -> Mapping[
    str,
    DictElement[_NamedOption] | DictElement[Sequence[_NamedOption]] | DictElement[bool],
]:
    return {
        "sections": DictElement(
            parameter_form=_sections(),
            required=False,
            group=_MONITORING_OPTIONS,
        ),
        "excluded_sections": DictElement(
            parameter_form=_excluded_sections(),
            required=False,
            group=_MONITORING_OPTIONS,
        ),
        "ignore_db_name": DictElement(
            parameter_form=FixedValue(
                title=Title("Ignore database name"),
                help_text=Help(
                    "If enabled, the instance name will be queried "
                    "from the database instead of the database name."
                ),
                label=Label("Query the instance name from the database"),
                value=False,
            ),
            required=False,
            group=_MONITORING_OPTIONS,
        ),
    }


def _oracle_client_options() -> Mapping[
    str, DictElement[str] | DictElement[_AuthOptions] | DictElement[_NamedOption]
]:
    return {
        "use_host_client": DictElement(
            parameter_form=_use_host_client(),
            required=False,
            group=_CLIENT_OPTIONS,
        ),
        "validate_permissions": DictElement(
            parameter_form=_permissions(),
            required=False,
            group=_CLIENT_OPTIONS,
        ),
        **_oracle_file_paths(),
    }


def _endpoint(
    *, is_main_entry: bool, group: DictGroupExtended | NoGroup = NoGroup()
) -> Mapping[str, DictElement[_AuthOptions] | DictElement[_NamedOption]]:
    return {
        "auth": DictElement(
            parameter_form=_auth_options(is_default_options=is_main_entry),
            required=False,
            group=group,
        ),
        "connection": DictElement(
            parameter_form=_connection_options(),
            required=False,
            group=group,
        ),
    }


def _cache_age(*, title: Title, help_text: Help) -> TimeSpan:
    return TimeSpan(
        title=title,
        help_text=help_text,
        displayed_magnitudes=[TimeMagnitude.MINUTE, TimeMagnitude.SECOND],
        custom_validate=(validators.NumberInRange(min_value=30),),
        prefill=DefaultValue(600.0),
    )


def _cache_ages() -> Mapping[str, DictElement[float]]:
    return {
        "cache_age": DictElement(
            parameter_form=_cache_age(
                title=Title("Cache age for asynchronous built-in sections"),
                help_text=Help(
                    "How old the cached output of the built-in sections marked 'async' "
                    "is allowed to be."
                ),
            ),
            required=False,
            group=_PLUGIN_BEHAVIOR,
        ),
    }


# identical tp the legacy list
def _oracle_sections_to_exclude() -> Sequence[tuple[str, Title]]:
    return [
        ("performance", Title("Performance")),
        ("iostats", Title("Performance: I/O stats")),
        ("processes", Title("Current number of processes")),
        ("sessions", Title("Current number of sessions")),
        ("longactivesessions", Title("Long active sessions")),
        ("logswitches", Title("Logswitches")),
        ("undostat", Title("Undo statistics")),
        ("recovery_area", Title("Recovery area")),
        ("recovery_status", Title("Recovery status")),
        ("dataguard_stats", Title("Data Guard statistics")),
        ("tablespaces", Title("Tablespaces")),
        ("ts_quotas", Title("TS quotas (not used)")),
        ("rman", Title("RMAN backups")),
        ("jobs", Title("Scheduled jobs")),
        ("resumable", Title("Resumables")),
        ("locks", Title("Locks")),
        ("systemparameter", Title("System parameters")),
    ]


def _excluded_sections() -> List[_NamedOption]:
    return List(
        title=Title("Exclude some sections on certain instances"),
        help_text=Help("Define sections to be excluded from monitoring for certain instances"),
        add_element_label=Label("Add exclusion rule"),
        element_template=Dictionary(
            title=Title("Excluded sections"),
            elements={
                "target_id": DictElement(
                    parameter_form=_oracle_id(),
                    required=True,
                ),
                "sections": DictElement(
                    required=False,
                    parameter_form=MultipleChoice(
                        title=Title("Sections to exclude"),
                        elements=[
                            MultipleChoiceElement(
                                name=name,
                                title=title,  # astrein: disable=localization-checker
                            )
                            for name, title in _oracle_sections_to_exclude()
                        ],
                    ),
                ),
            },
        ),
    )


def _instances() -> List[_NamedOption]:
    return List(
        title=Title("Databases to monitor"),
        no_element_label=Label("No databases configured explicitly; see 'Instance discovery'"),
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
                **_endpoint(is_main_entry=False, group=_PER_INSTANCE),
                "piggyback_host": DictElement(
                    group=_PER_INSTANCE_MONITORING,
                    parameter_form=String(
                        title=Title("Monitoring host this database should be mapped to"),
                        help_text=Help(
                            "If you leave this empty then the database will appear on the host "
                            "where the <tt>mk_oracle</tt> plug-in is running. In this case the "
                            "SIDs of all monitored databases must be unique."
                        ),
                        custom_validate=(validators.LengthInRange(min_value=1),),
                    ),
                    required=False,
                ),
            },
        ),
    )


# Never offered by the form, and no migration removes them. CMK-37226 dropped
# max_connections from the form and CMK-37191 dropped max_queries, but a rule
# written before that still carries them.
_KEPT_BUT_NOT_OFFERED: Final = ("max_connections", "max_queries")

# The plug-in reads these two once per run: TNS_ADMIN becomes a process-wide
# environment variable (connection.rs:146), and the Grid home found through
# olr.loc picks the Oracle client (setup.rs:753). A per-database value never
# reached either one.
_ORACLE_FILE_PATHS: Final = ("tns_admin", "oracle_local_registry")

_LIFTED_FROM_MAIN: Final = (
    "auth",
    "connection",
    "cache_age",
    "discovery",
    "sections",
    "excluded_sections",
)


def _oracle_id_to_rev2(oracle_id: object) -> object | None:
    """Return the identification, or None if it names no database."""
    match oracle_id:
        case (("alias" | "sid") as kind, Mapping() as fields):
            return (kind, name) if (name := fields.get(kind)) else None
        case ("descriptor", Mapping() as fields):
            named = ("service_name", "instance_name", "sid")
            return oracle_id if any(fields.get(key) for key in named) else None
        case _:
            return oracle_id


def _entries_to_rev2(entries: object, id_key: str) -> object:
    if not isinstance(entries, list):
        return entries
    converted = []
    for entry in entries:
        if not isinstance(entry, Mapping) or id_key not in entry:
            converted.append(entry)
            continue
        # The bakery dropped an entry that named no database, so a rule could
        # carry one. It has no place in the new shape, where the name is required.
        if (oracle_id := _oracle_id_to_rev2(entry[id_key])) is not None:
            converted.append({**entry, id_key: oracle_id})
    return converted


def _discovery_to_rev2(discovery: Mapping[str, object]) -> Mapping[str, object]:
    return {**discovery, "enabled": "enabled" if discovery.get("enabled") else "disabled"}


def _sections_to_rev2(sections: Mapping[str, object]) -> Mapping[str, object]:
    """Three modes per section become presence plus a flag.

    A section that is not collected is simply absent, which is what the bakery
    made of "disabled" anyway. The instance status is not configurable, so the
    bakery names it rather than the rule.
    """
    return {
        name: mode == "asynchronous"
        for name, mode in sections.items()
        if name not in SYNC_ONLY_SECTIONS and mode != "disabled"
    }


def _options_to_rev2(options: Mapping[str, object]) -> Mapping[str, object]:
    hoisted: dict[str, object] = {
        key: value for key, value in options.items() if key != "oracle_client_library"
    }
    library = options.get("oracle_client_library")
    if isinstance(library, Mapping) and "use_host_client" in library:
        hoisted.setdefault("use_host_client", library["use_host_client"])
    return hoisted


def _to_rev2(value: Mapping[str, object]) -> Mapping[str, object]:
    """Dissolve "main", and give the keys whose shape changed a new name.

    Every step keys off a name that only the old shape has, so running this on a
    value that has already been through it changes nothing. The keys lifted out
    of "main" are converted while they are lifted, for the same reason: at the
    top level their names say nothing about which shape they hold.
    """
    migrated = {key: item for key, item in value.items() if key != "main"}

    if isinstance(main := value.get("main"), Mapping):
        lifted = {key: main[key] for key in _LIFTED_FROM_MAIN if key in main}
        if isinstance(discovery := lifted.get("discovery"), Mapping):
            lifted["discovery"] = _discovery_to_rev2(discovery)
        if isinstance(sections := lifted.get("sections"), Mapping):
            lifted["sections"] = _sections_to_rev2(sections)
        if "excluded_sections" in lifted:
            lifted["excluded_sections"] = _entries_to_rev2(lifted["excluded_sections"], "target_id")
        migrated.update(lifted)

    if "deploy" in migrated:
        deploy = migrated.pop("deploy")
        migrated["deploy_rev2"] = deploy[0] if isinstance(deploy, tuple) else deploy
    if "instances" in migrated:
        migrated["instances_rev2"] = _entries_to_rev2(migrated.pop("instances"), "oracle_id")
    if isinstance(options := migrated.pop("options", None), Mapping):
        migrated.update(_options_to_rev2(options))
    if isinstance(connection := migrated.get("connection"), Mapping):
        lifted = {key: connection[key] for key in _ORACLE_FILE_PATHS if key in connection}
        if lifted:
            migrated["connection"] = {
                key: item for key, item in connection.items() if key not in lifted
            }
            migrated.update({key: item for key, item in lifted.items() if key not in migrated})
    return migrated


# One entry per revision. A new revision appends a step; the existing ones are
# never touched again. Each step keys off the presence of a retired name, so
# running the chain on an already current value changes nothing.
_MIGRATIONS: Final = (_to_rev2,)


def _migrate(value: object) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(f"Invalid rule value: {value!r}")
    migrated: Mapping[str, object] = value
    for step in _MIGRATIONS:
        migrated = step(migrated)
    return migrated


def _agent_config_mk_oracle() -> Dictionary:
    return DictionaryExtended(
        migrate=_migrate,
        # A rule says what it changes, and the bakery merges the rules key by
        # key, so nothing here may be required. A new rule still opens with the
        # two entries that no Oracle configuration works without.
        default_checked=["deploy_rev2", "auth"],
        # The order decides the headings: a group appears where its first
        # element does.
        elements={
            "deploy_rev2": DictElement(
                required=False,
                group=_ACTIVATION,
                parameter_form=SingleChoice(
                    title=Title("Deployment"),
                    prefill=DefaultValue("deploy"),
                    elements=[
                        SingleChoiceElement(
                            name="deploy",
                            title=Title("Deploy the Oracle plug-in"),
                        ),
                        SingleChoiceElement(
                            name="do_not_deploy",
                            title=Title("Do not deploy the Oracle plug-in"),
                        ),
                    ],
                ),
            ),
            "discovery": DictElement(
                parameter_form=_discovery(),
                required=False,
                group=_WHICH_INSTANCES,
            ),
            "instances_rev2": DictElement(
                parameter_form=_instances(),
                required=False,
                group=_WHICH_INSTANCES,
            ),
            **_endpoint(is_main_entry=True, group=_STANDARD_SETTINGS),
            **_monitoring_options(),
            **_oracle_client_options(),
            **_cache_ages(),
        },
        ignored_elements=_KEPT_BUT_NOT_OFFERED,
    )


rule_spec_oracle_bakelet = AgentConfig(
    name="mk_oracle_unified",
    title=Title("Unified Oracle plug-in (beta)"),
    topic=Topic.DATABASES,
    parameter_form=_agent_config_mk_oracle,
    help_text=Help(
        "This will deploy the agent plug-in <tt>mk_oracle</tt> on your target system.<br>"
        "ARM architecture is not supported.<br>"
        "<b>Note:</b> This plug-in cannot be used together with "
        "'Oracle databases (Linux, Solaris, AIX, Windows)'. "
        "Please configure only one of the two."
    ),
)
