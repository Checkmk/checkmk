#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import ast
import io
import re
import socket
import sys
import time
import zipfile
from collections.abc import Callable, Collection, Iterable, Iterator, Mapping
from dataclasses import dataclass
from html import escape as html_escape
from pathlib import Path
from typing import Any, cast, Literal, overload, TypeVar

from pysmi.codegen.pysnmp import PySnmpCodeGen
from pysmi.compiler import MibCompiler
from pysmi.error import PySmiError
from pysmi.parser.smiv1compat import SmiV1CompatParser
from pysmi.reader.callback import CallbackReader
from pysmi.reader.localfile import FileReader
from pysmi.searcher.pyfile import PyFileSearcher
from pysmi.searcher.pypackage import PyPackageSearcher
from pysmi.searcher.stub import StubSearcher
from pysmi.writer.pyfile import PyFileWriter

from livestatus import LocalConnection, MKLivestatusSocketError

from cmk.ccc import store
from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import omd_site, SiteId
from cmk.ccc.version import Edition, edition

import cmk.utils.log
import cmk.utils.paths
import cmk.utils.render
import cmk.utils.translations
from cmk.utils.rulesets.definition import RuleGroup

# It's OK to import centralized config load logic
import cmk.ec.export as ec  # pylint: disable=cmk-module-layer-violation

import cmk.gui.watolib.changes as _changes
from cmk.gui import forms, hooks, log, sites, watolib
from cmk.gui.breadcrumb import Breadcrumb, BreadcrumbItem
from cmk.gui.config import active_config
from cmk.gui.customer import customer_api, SCOPE_GLOBAL
from cmk.gui.exceptions import MKUserError
from cmk.gui.form_specs.generators.host_address import HostAddressValidator
from cmk.gui.form_specs.private import (
    DictionaryExtended,
    SingleChoiceElementExtended,
    SingleChoiceExtended,
)
from cmk.gui.form_specs.vue.visitors.recomposers.unknown_form_spec import (
    recompose_dictionary_spec,
)
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.htmllib.html import html
from cmk.gui.htmllib.type_defs import RequireConfirmation
from cmk.gui.http import request
from cmk.gui.i18n import _, _l
from cmk.gui.logged_in import user
from cmk.gui.page_menu import (
    get_search_expression,
    make_confirmed_form_submit_link,
    make_simple_form_page_menu,
    make_simple_link,
    PageMenu,
    PageMenuDropdown,
    PageMenuEntry,
    PageMenuSearch,
    PageMenuTopic,
)
from cmk.gui.permissions import Permission, PermissionRegistry
from cmk.gui.site_config import enabled_sites
from cmk.gui.table import table_element
from cmk.gui.type_defs import ActionResult, Choices, Icon, PermissionName
from cmk.gui.user_sites import get_event_console_site_choices
from cmk.gui.utils.csrf_token import check_csrf_token
from cmk.gui.utils.flashed_messages import flash
from cmk.gui.utils.html import HTML
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.utils.urls import (
    DocReference,
    make_confirm_delete_link,
    makeuri_contextless,
    makeuri_contextless_rulespec_group,
)
from cmk.gui.valuespec import (
    Age,
    Alternative,
    CascadingDropdown,
    CascadingDropdownChoice,
    Checkbox,
    Dictionary,
    DictionaryEntry,
    DictionaryModel,
    DropdownChoice,
    DualListChoice,
    Filesize,
    FixedValue,
    Foldable,
    ID,
    Integer,
    IPAddress,
    IPNetwork,
    ListChoice,
    ListOf,
    ListOfStrings,
    LogLevelChoice,
    Migrate,
    MigrateNotUpdated,
    Optional,
    RegExp,
    rule_option_elements,
    TextAreaUnicode,
    TextInput,
    Transform,
    Tuple,
    ValueSpec,
)
from cmk.gui.wato import (
    ContactGroupSelection,
    MainModuleTopicEvents,
)
from cmk.gui.wato.pages.global_settings import (
    ABCEditGlobalSettingMode,
    ABCGlobalSettingsMode,
    MatchItemGeneratorSettings,
)
from cmk.gui.watolib.attributes import SNMPCredentials
from cmk.gui.watolib.audit_log import log_audit
from cmk.gui.watolib.config_domain_name import (
    config_domain_registry,
    config_variable_group_registry,
    config_variable_registry,
    ConfigDomainRegistry,
    ConfigVariable,
    ConfigVariableGroup,
    ConfigVariableGroupRegistry,
    ConfigVariableRegistry,
    SampleConfigGenerator,
    SampleConfigGeneratorRegistry,
)
from cmk.gui.watolib.config_domains import ConfigDomainGUI, ConfigDomainOMD
from cmk.gui.watolib.config_sync import (
    ReplicationPath,
    ReplicationPathRegistry,
    ReplicationPathType,
)
from cmk.gui.watolib.config_variable_groups import (
    ConfigVariableGroupNotifications,
    ConfigVariableGroupSiteManagement,
    ConfigVariableGroupUserInterface,
    ConfigVariableGroupWATO,
)
from cmk.gui.watolib.global_settings import load_configuration_settings, save_global_settings
from cmk.gui.watolib.host_attributes import CollectedHostAttributes
from cmk.gui.watolib.hosts_and_folders import (
    make_action_link,
)
from cmk.gui.watolib.main_menu import ABCMainModule, MainModuleRegistry, MainModuleTopic
from cmk.gui.watolib.mode import mode_url, ModeRegistry, redirect, WatoMode
from cmk.gui.watolib.notification_parameter import (
    NotificationParameter,
    NotificationParameterRegistry,
)
from cmk.gui.watolib.rulespec_groups import (
    RulespecGroupHostsMonitoringRulesVarious,
    RulespecGroupMonitoringConfigurationVarious,
)
from cmk.gui.watolib.rulespecs import (
    HostRulespec,
    RulespecGroup,
    RulespecGroupRegistry,
    RulespecRegistry,
    ServiceRulespec,
)
from cmk.gui.watolib.search import (
    ABCMatchItemGenerator,
    MatchItem,
    MatchItemGeneratorRegistry,
    MatchItems,
)
from cmk.gui.watolib.translation import HostnameTranslation
from cmk.gui.watolib.utils import site_neutral_path

import cmk.mkp_tool
from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DictElement,
    String,
)

from ._rulespecs import RulespecLogwatchEC
from .config_domain import ConfigDomainEventConsole, EVENT_CONSOLE
from .defines import syslog_facilities, syslog_priorities
from .helpers import action_choices, eventd_configuration, service_levels
from .livestatus import execute_command
from .permission_section import PERMISSION_SECTION_EVENT_CONSOLE


def register(
    permission_registry: PermissionRegistry,
    sample_config_generator_registry: SampleConfigGeneratorRegistry,
    mode_registry: ModeRegistry,
    main_module_registry: MainModuleRegistry,
    config_domain_registry: ConfigDomainRegistry,
    save_active_config: Callable[[], None],
    config_var_group_registry: ConfigVariableGroupRegistry,
    config_var_registry: ConfigVariableRegistry,
    rulespec_group_registry: RulespecGroupRegistry,
    rulespec_registry: RulespecRegistry,
    match_item_generator_registry: MatchItemGeneratorRegistry,
    notification_parameter_registry: NotificationParameterRegistry,
    replication_path_registry: ReplicationPathRegistry,
) -> None:
    sample_config_generator_registry.register(SampleConfigGeneratorECSampleRulepack)

    mode_registry.register(ModeEventConsoleRulePacks)
    mode_registry.register(ModeEventConsoleRules)
    mode_registry.register(ModeEventConsoleEditRulePack)
    mode_registry.register(ModeEventConsoleEditRule)
    mode_registry.register(ModeEventConsoleStatus)
    mode_registry.register(ModeEventConsoleSettings)
    mode_registry.register(ModeEventConsoleEditGlobalSetting)
    mode_registry.register(ModeEventConsoleMIBs)
    mode_registry.register(ModeEventConsoleUploadMIBs)

    main_module_registry.register(MainModuleEventConsole)
    main_module_registry.register(MainModuleEventConsoleRules)

    config_domain_registry.register(ConfigDomainEventConsole(save_active_config))
    config_var_group_registry.register(ConfigVariableGroupEventConsoleGeneric)
    config_var_group_registry.register(ConfigVariableGroupEventConsoleLogging)
    config_var_group_registry.register(ConfigVariableGroupEventConsoleSNMP)
    config_var_registry.register(ConfigVariableEventConsole)
    config_var_registry.register(ConfigVariableEventConsoleRemoteStatus)
    config_var_registry.register(ConfigVariableEventConsoleReplication)
    config_var_registry.register(ConfigVariableEventConsoleRetentionInterval)
    config_var_registry.register(ConfigVariableEventConsoleHousekeepingInterval)
    config_var_registry.register(ConfigVariableEventConsoleStatisticsInterval)
    config_var_registry.register(ConfigVariableEventConsoleLogMessages)
    config_var_registry.register(ConfigVariableEventConsoleRuleOptimizer)
    config_var_registry.register(ConfigVariableEventConsoleActions)
    config_var_registry.register(ConfigVariableEventConsoleArchiveOrphans)
    config_var_registry.register(ConfigVariableHostnameTranslation)
    config_var_registry.register(ConfigVariableEventConsoleEventLimit)
    config_var_registry.register(ConfigVariableEventConsoleHistoryRotation)
    config_var_registry.register(ConfigVariableEventConsoleHistoryLifetime)
    config_var_registry.register(ConfigVariableEventConsoleSocketQueueLength)
    config_var_registry.register(ConfigVariableEventConsoleEventSocketQueueLength)
    config_var_registry.register(ConfigVariableEventConsoleTranslateSNMPTraps)
    config_var_registry.register(ConfigVariableEventConsoleSNMPCredentials)
    config_var_registry.register(ConfigVariableEventConsoleDebugRules)
    config_var_registry.register(ConfigVariableEventConsoleLogLevel)
    config_var_registry.register(ConfigVariableEventLogRuleHits)
    config_var_registry.register(ConfigVariableEventConsoleConnectTimeout)
    config_var_registry.register(ConfigVariableEventConsolePrettyPrintRules)
    config_var_registry.register(ConfigVariableEventConsoleNotifyContactgroup)
    config_var_registry.register(ConfigVariableEventConsoleNotifyRemoteHost)
    config_var_registry.register(ConfigVariableEventConsoleNotifyFacility)
    config_var_registry.register(ConfigVariableEventConsoleServiceLevels)
    config_var_registry.register(ConfigVariableEventConsoleSqliteHousekeepingInterval)
    config_var_registry.register(ConfigVariableEventConsoleSqliteFreelistSize)

    rulespec_group_registry.register(RulespecGroupEventConsole)
    rulespec_registry.register(ECEventLimitRulespec)
    rulespec_registry.register(ActiveCheckMKEventsRulespec)
    rulespec_registry.register(ExtraHostConfECSLRulespec)
    rulespec_registry.register(ExtraServiceConfECSLRulespec)
    rulespec_registry.register(ExtraHostConfECContact)
    rulespec_registry.register(ExtraServiceConfECContact)
    rulespec_registry.register(RulespecLogwatchEC)

    permission_registry.register(ConfigureECPermission)
    permission_registry.register(ConfigureECRulesPermission)
    permission_registry.register(ActivateECPermission)
    permission_registry.register(SwitchSlaveReplicationPermission)

    match_item_generator_registry.register(MatchItemEventConsole)
    match_item_generator_registry.register(MatchItemEventConsoleSettings)

    notification_parameter_registry.register(
        NotificationParameter(
            ident="mkeventd",
            spec=lambda: recompose_dictionary_spec(form_spec),
            form_spec=form_spec,
        )
    )

    hooks.register_builtin("pre-activate-changes", mkeventd_update_notification_configuration)

    replication_path_registry.register(
        ReplicationPath.make(
            ty=ReplicationPathType.DIR,
            ident="mkeventd",
            site_path=str(ec.rule_pack_dir().relative_to(cmk.utils.paths.omd_root)),
        )
    )

    replication_path_registry.register(
        ReplicationPath.make(
            ty=ReplicationPathType.DIR,
            ident="mkeventd_mkp",
            site_path=str(ec.mkp_rule_pack_dir().relative_to(cmk.utils.paths.omd_root)),
        )
    )


def _compiled_mibs_dir() -> Path:
    return cmk.utils.paths.omd_root / "local/share/check_mk/compiled_mibs"


def mib_upload_dir() -> Path:
    return cmk.utils.paths.local_mib_dir


def mib_dirs() -> list[tuple[Path, str]]:
    # ASN1 MIB source directory candidates. Non existing dirs are ok.
    return [
        (mib_upload_dir(), _("Custom MIBs")),
        (cmk.utils.paths.mib_dir, _("MIBs shipped with Checkmk")),
        (Path("/usr/share/snmp/mibs"), _("System MIBs")),
    ]


def match_event_rule(rule_pack: ec.ECRulePack, rule: ec.Rule, event: ec.Event) -> ec.MatchResult:
    if edition(cmk.utils.paths.omd_root) is Edition.CME:
        rule_customer_id = (
            rule_pack["customer"] if "customer" in rule_pack else rule.get("customer", SCOPE_GLOBAL)
        )
        site_customer_id = customer_api().get_customer_id(active_config.sites[event["site"]])
        if rule_customer_id not in (SCOPE_GLOBAL, site_customer_id):
            return ec.MatchFailure(reason=_("Wrong customer"))

    time_period = ec.TimePeriods(log.logger)
    rule_matcher = ec.RuleMatcher(
        logger=None,
        omd_site_id=omd_site(),
        is_active_time_period=time_period.active,
    )
    rule = rule.copy()
    rule["pack"] = rule_pack["id"]
    ec.compile_rule(rule)
    return rule_matcher.event_rule_matches(rule, event)


# .
#   .--ValueSpecs----------------------------------------------------------.
#   |        __     __    _            ____                                |
#   |        \ \   / /_ _| |_   _  ___/ ___| _ __   ___  ___ ___           |
#   |         \ \ / / _` | | | | |/ _ \___ \| '_ \ / _ \/ __/ __|          |
#   |          \ V / (_| | | |_| |  __/___) | |_) |  __/ (__\__ \          |
#   |           \_/ \__,_|_|\__,_|\___|____/| .__/ \___|\___|___/          |
#   |                                       |_|                            |
#   +----------------------------------------------------------------------+
#   | Declarations of the structure of rules and actions                   |
#   '----------------------------------------------------------------------'

MACROS_AND_VARS = [
    ("ID", _l("Event ID")),
    ("COUNT", _l("Number of occurrences")),
    ("TEXT", _l("Message text")),
    ("FIRST", _l("Time of the first occurrence (time stamp)")),
    ("LAST", _l("Time of the most recent occurrence")),
    ("COMMENT", _l("Event comment")),
    ("SL", _l("Service level")),
    ("HOST", _l("Host name (as sent by syslog)")),
    ("ORIG_HOST", _l("Original host name when host name has been rewritten, empty otherwise")),
    ("CONTACT", _l("Contact information")),
    ("APPLICATION", _l("Syslog tag / Application")),
    ("PID", _l("Process ID of the origin process")),
    ("PRIORITY", _l("Syslog Priority")),
    ("FACILITY", _l("Syslog Facility")),
    ("RULE_ID", _l("ID of the rule")),
    ("STATE", _l("State of the event (0/1/2/3)")),
    ("PHASE", _l("Phase of the event (open in normal situations, closed when cancelling)")),
    ("OWNER", _l("Owner of the event")),
    ("MATCH_GROUPS", _l("Text groups from regular expression match, separated by spaces")),
    ("MATCH_GROUP_1", _l("Text of the first match group from expression match")),
    ("MATCH_GROUP_2", _l("Text of the second match group from expression match")),
    (
        "MATCH_GROUP_3",
        _l("Text of the third match group from expression match (and so on...)"),
    ),
]


def _macros_help() -> HTML:
    _help_list = [(f"${macro_name}$", description) for macro_name, description in MACROS_AND_VARS]

    _help_rows = [
        HTMLWriter.render_tr(HTMLWriter.render_td(key) + HTMLWriter.render_td(str(value)))
        for key, value in _help_list
    ]

    return (
        _("Text-body of the email to send. ")
        + _("The following macros will be substituted by value from the actual event:")
        + HTMLWriter.render_br()
        + HTMLWriter.render_br()
        + HTMLWriter.render_table(HTML.empty().join(_help_rows), class_="help")
    )


def _vars_help() -> HTML:
    _help_list = [(f"CMK_{macro_name}", description) for macro_name, description in MACROS_AND_VARS]

    _help_rows = [
        HTMLWriter.render_tr(HTMLWriter.render_td(key) + HTMLWriter.render_td(str(value)))
        for key, value in _help_list
    ]

    return (
        _("This script will be executed using the BASH shell. ")
        + _("This information is available as environment variables")
        + HTMLWriter.render_br()
        + HTMLWriter.render_br()
        + HTMLWriter.render_table(HTML.empty().join(_help_rows), class_="help")
    )


def ActionList(vs: ValueSpec, **kwargs: Any) -> ListOf:
    def validate_action_list(value: Any, varprefix: str) -> None:
        action_ids = [v["id"] for v in value]
        rule_packs = ec.load_rule_packs()
        for rule_pack in rule_packs:
            for rule in rule_pack["rules"]:
                for action_id in rule.get("actions", []):
                    if action_id not in action_ids + ["@NOTIFY"]:
                        raise MKUserError(
                            varprefix,
                            _(
                                "You are missing the action with the ID <b>%s</b>, "
                                "which is still used in some rules."
                            )
                            % action_id,
                        )

    return ListOf(valuespec=vs, validate=validate_action_list, **kwargs)


class RuleState(CascadingDropdown):
    def __init__(
        self,
        title: str,
        help: str,
        default_value: int,
    ) -> None:
        choices: list[CascadingDropdownChoice] = [
            (0, _("OK")),
            (1, _("WARN")),
            (2, _("CRIT")),
            (3, _("UNKNOWN")),
            (-1, _("(set by syslog)")),
            (
                "text_pattern",
                _("(set by message text)"),
                Dictionary(
                    elements=[
                        (
                            "2",
                            RegExp(
                                title=_("CRIT Pattern"),
                                help=_(
                                    "When the given regular expression (infix search) matches "
                                    "the events state is set to CRITICAL."
                                ),
                                size=64,
                                mode=RegExp.infix,
                            ),
                        ),
                        (
                            "1",
                            RegExp(
                                title=_("WARN Pattern"),
                                help=_(
                                    "When the given regular expression (infix search) matches "
                                    "the events state is set to WARNING."
                                ),
                                size=64,
                                mode=RegExp.infix,
                            ),
                        ),
                        (
                            "0",
                            RegExp(
                                title=_("OK Pattern"),
                                help=_(
                                    "When the given regular expression (infix search) matches "
                                    "the events state is set to OK."
                                ),
                                size=64,
                                mode=RegExp.infix,
                            ),
                        ),
                    ],
                    help=_(
                        "Individual patterns matching the text (which must have been matched by "
                        'the generic "text to match pattern" before) which set the state of the '
                        "generated event depending on the match.<br><br>"
                        "First the CRITICAL pattern is tested, then WARNING and OK at last. "
                        "When none of the patterns matches, the events state is set to UNKNOWN."
                    ),
                ),
            ),
        ]
        CascadingDropdown.__init__(
            self, choices=choices, title=title, help=help, default_value=default_value
        )


def vs_mkeventd_rule_pack(
    fixed_id: str | None = None, fixed_title: str | None = None
) -> Dictionary:
    elements: list[DictionaryEntry] = []
    if fixed_id:
        elements.append(
            (
                "id",
                FixedValue(
                    value=fixed_id,
                    title=_("Rule pack ID"),
                    help=_("The ID of an exported rule pack cannot be modified."),
                ),
            )
        )
    else:
        elements.append(
            (
                "id",
                ID(
                    title=_("Rule pack ID"),
                    help=_("A unique ID of this rule pack."),
                    allow_empty=False,
                    size=12,
                ),
            )
        )

    if fixed_title:
        elements.append(
            (
                "title",
                FixedValue(
                    value=fixed_title,
                    title=_("Title"),
                    help=_("The title of an exported rule pack cannot be modified."),
                ),
            )
        )
    else:
        elements.append(
            (
                "title",
                TextInput(
                    title=_("Title"),
                    help=_("A descriptive title for this rule pack"),
                    allow_empty=False,
                    size=64,
                ),
            ),
        )

    elements.append(
        (
            "disabled",
            Checkbox(
                title=_("Disable"),
                label=_("Currently disable execution of all rules in the pack"),
            ),
        ),
    )

    if edition(cmk.utils.paths.omd_root) is Edition.CME:
        elements += customer_api().customer_choice_element(deflt=SCOPE_GLOBAL)

    return Dictionary(
        title=_("Rule pack properties"),
        render="form",
        elements=elements,
        optional_keys=["customer"],
    )


def vs_mkeventd_rule(customer: str | None = None) -> Dictionary:
    elements = [
        (
            "id",
            ID(
                title=_("Rule ID"),
                help=_(
                    "A unique ID of this rule. Each event will remember the rule "
                    "it was classified with by its rule ID."
                ),
                allow_empty=False,
                size=24,
            ),
        ),
    ] + rule_option_elements()

    if edition(cmk.utils.paths.omd_root) is Edition.CME:
        if customer:
            # Enforced by rule pack
            elements += [
                (
                    "customer",
                    FixedValue(
                        value=customer,
                        title=_("Customer"),
                        totext="{} ({})".format(
                            customer_api().get_customer_name_by_id(customer),
                            _("Set by rule pack"),
                        ),
                    ),
                ),
            ]
        else:
            elements += customer_api().customer_choice_element()

    elements += [
        (
            "drop",
            DropdownChoice(
                title=_("Rule type"),
                choices=[
                    (False, _("Normal operation - process message according to action settings")),
                    (True, _("Do not perform any action, drop this message, stop processing")),
                    (
                        "skip_pack",
                        _("Skip this rule pack, continue rule execution with next rule pack"),
                    ),
                ],
                help=_(
                    "With this option you can implement rules that rule out certain message from the "
                    "procession totally. Either you can totally abort further rule execution, or "
                    "you can skip just the current rule pack and continue with the next one."
                ),
            ),
        ),
        (
            "state",
            RuleState(
                title=_("State"),
                help=_("The monitoring state that this event will trigger."),
                default_value=-1,
            ),
        ),
        (
            "sl",
            Dictionary(
                title=_("Service level"),
                optional_keys=False,
                elements=[
                    (
                        "value",
                        DropdownChoice(
                            title=_("Value"),
                            choices=service_levels,
                            prefix_values=True,
                            help=_("The default/fixed service level to use for this rule."),
                        ),
                    ),
                    (
                        "precedence",
                        DropdownChoice(
                            title=_("Precedence"),
                            choices=[
                                ("message", _("Keep service level from message (if available)")),
                                ("rule", _("Always use service level from rule")),
                            ],
                            help=_(
                                "Here you can specify which service level will be used when "
                                "the incoming message already carries a service level."
                            ),
                            default_value="message",
                        ),
                    ),
                ],
            ),
        ),
        (
            "contact_groups",
            Dictionary(
                title=_("Contact groups"),
                elements=[
                    (
                        "groups",
                        ListOf(
                            valuespec=ContactGroupSelection(),
                            title=_("Contact groups"),
                            movable=False,
                        ),
                    ),
                    (
                        "notify",
                        Checkbox(
                            title=_("Use in notifications"),
                            label=_("Use in notifications"),
                            help=_(
                                "Also use these contact groups in eventually notifications created by "
                                "this rule. Historically this option only affected the visibility in the "
                                "GUI and <i>not</i> notifications. New rules will enable this option "
                                "automatically, existing rules have this disabled by default."
                            ),
                            default_value=True,
                        ),
                    ),
                    (
                        "precedence",
                        DropdownChoice(
                            title=_("Precedence of contact groups"),
                            choices=[
                                ("host", _("Host's contact groups have precedence")),
                                ("rule", _("Contact groups in rule have precedence")),
                            ],
                            help=_(
                                "Here you can specify which contact groups shall have "
                                "precedence when both, the host of an event can be found in the "
                                "monitoring and the event rule has defined contact groups for the event."
                            ),
                            default_value="host",
                        ),
                    ),
                ],
                help=_(
                    "When you expect this rule to receive events from hosts that are <i>not</i> "
                    "known to the monitoring, you can specify contact groups for controlling "
                    "the visibility and eventually triggered notifications here.<br>"
                    "<br><i>Notes:</i><br>"
                    "1. If you activate this option and do not specify any group, then "
                    "users with restricted permissions can never see these events.<br>"
                    "2. If both the host is found in the monitoring <b>and</b> contact groups are "
                    "specified in the rule then usually the host's contact groups have precedence. "
                ),
                optional_keys=[],
            ),
        ),
        (
            "actions",
            ListChoice(
                title=_("Actions"),
                help=_("Actions to automatically perform when this event occurs"),
                choices=action_choices,
            ),
        ),
        (
            "actions_in_downtime",
            DropdownChoice(
                title=_("Do actions"),
                choices=[
                    (True, _("even when the host is in downtime")),
                    (False, _("only when the host is not in downtime")),
                ],
                default_value=True,
                help=_(
                    "With this setting you can prevent actions to be executed when "
                    "the host is in downtime. This setting applies to events that are "
                    "related to an existing monitoring host. Other event actions will "
                    "always be executed."
                ),
            ),
        ),
        (
            "cancel_actions",
            ListChoice(
                title=_("Actions when cancelling"),
                help=_("Actions to automatically perform when an event is being cancelled."),
                choices=action_choices,
            ),
        ),
        (
            "cancel_action_phases",
            DropdownChoice(
                title=_("Do cancelling actions"),
                choices=[
                    ("always", _("Always when an event is being cancelled")),
                    ("open", _("Only when the cancelled event is in phase OPEN")),
                ],
                help=_(
                    "With this setting you can prevent actions to be executed when "
                    "events are being cancelled that are in the phases DELAYED or COUNTING."
                ),
            ),
        ),
        (
            "autodelete",
            Checkbox(
                title=_("Automatic Deletion"),
                label=_("Delete event immediately after the actions"),
                help=_(
                    "Incoming messages might trigger actions (when configured above), "
                    "afterwards only an entry in the event history will be left. There "
                    'will be no "open event" to be handled by the administrators.'
                ),
            ),
        ),
        (
            "event_limit",
            Alternative(
                title=_("Custom event limit"),
                help=_(
                    "Use this option to override the "
                    '<a href="wato.py?mode=mkeventd_edit_configvar&site=&varname=event_limit">'
                    "global rule event limit</a>"
                ),
                elements=[
                    FixedValue(
                        value=None,
                        title=_("Use global rule limit"),
                        totext="",
                    ),
                    vs_ec_rule_limit(),
                ],
            ),
        ),
        (
            "count",
            Dictionary(
                title=_("Count messages in interval"),
                help=_(
                    "With this option you can make the rule being executed not before "
                    "the matching message is seen a couple of times in a defined "
                    "time interval. Also counting activates the aggregation of messages "
                    "that result from the same rule into one event, even if <i>count</i> is "
                    "set to 1."
                ),
                optional_keys=False,
                columns=2,
                elements=[
                    (
                        "count",
                        Integer(
                            title=_("Count until triggered"),
                            help=_(
                                "That many times the message must occur until an event is created"
                            ),
                            minvalue=1,
                        ),
                    ),
                    (
                        "period",
                        Age(
                            title=_("Time period for counting"),
                            help=_(
                                "If in this time range the configured number of time the rule is "
                                "triggered, an event is being created. If the required count is not reached "
                                "then the count is reset to zero."
                            ),
                            default_value=86400,
                        ),
                    ),
                    (
                        "algorithm",
                        DropdownChoice(
                            title=_("Algorithm"),
                            help=_(
                                "Select how the count is computed. The algorithm <i>Interval</i> will count the "
                                "number of messages from the first occurrence and reset this counter as soon as "
                                "the interval is elapsed or the maximum count has reached. The token bucket algorithm "
                                "does not work with intervals but simply decreases the current count by one for "
                                "each partial time interval. Please refer to the online documentation for more details."
                            ),
                            choices=[
                                ("interval", _("Interval")),
                                ("tokenbucket", _("Token Bucket")),
                                ("dynabucket", _("Dynamic Token Bucket")),
                            ],
                            default_value="interval",
                        ),
                    ),
                    (
                        "count_duration",
                        Optional(
                            valuespec=Age(
                                label=_("Count only for"),
                                help=_(
                                    "When the event is in the state <i>open</i> for that time span "
                                    "then no further messages of the same time will be added to the "
                                    "event. It will stay open, but the count does not increase anymore. "
                                    "Any further matching message will create a new event."
                                ),
                            ),
                            label=_("Discontinue counting after time has elapsed"),
                            none_label=_("Bar"),
                        ),
                    ),
                    (
                        "count_ack",
                        Checkbox(
                            label=_("Continue counting when event is <b>acknowledged</b>"),
                            help=_(
                                "Otherwise counting will start from one with a new event for "
                                "the next rule match."
                            ),
                            default_value=False,
                        ),
                    ),
                    (
                        "separate_host",
                        Checkbox(
                            label=_("Force separate events for different <b>hosts</b>"),
                            help=_(
                                "When aggregation is turned on and the rule matches for "
                                "two different hosts then these two events will be kept "
                                "separate if you check this box."
                            ),
                            default_value=True,
                        ),
                    ),
                    (
                        "separate_application",
                        Checkbox(
                            label=_("Force separate events for different <b>applications</b>"),
                            help=_(
                                "When aggregation is turned on and the rule matches for "
                                "two different applications then these two events will be kept "
                                "separate if you check this box."
                            ),
                            default_value=True,
                        ),
                    ),
                    (
                        "separate_match_groups",
                        Checkbox(
                            label=_("Force separate events for different <b>match groups</b>"),
                            help=_(
                                "When you use subgroups in the regular expression of your "
                                "match text then you can have different values for the matching "
                                "groups be reflected in different events."
                            ),
                            default_value=True,
                        ),
                    ),
                ],
            ),
        ),
        (
            "expect",
            Dictionary(
                title=_("Expect regular messages"),
                help=_(
                    "With this option activated you can make the Event Console monitor "
                    "that a certain number of messages are <b>at least</b> seen within "
                    "each regular time interval. Otherwise an event will be created. "
                    "The options <i>week</i>, <i>two days</i> and <i>day</i> refer to "
                    "periodic intervals aligned at 00:00:00 on the 1st of January 1970. "
                    "You can specify a relative offset in hours in order to re-align this "
                    "to any other point of time. In a distributed environment, make "
                    "sure to specify which site should expect the messages in the match "
                    "criteria above, else all sites with config replication will warn if "
                    "messages fail to arrive."
                ),
                optional_keys=False,
                columns=2,
                elements=[
                    (
                        "interval",
                        CascadingDropdown(
                            title=_("Interval"),
                            separator="&nbsp;",
                            choices=[
                                (
                                    7 * 86400,
                                    _("week"),
                                    Integer(
                                        label=_("Timezone offset"),
                                        unit=_("hours"),
                                        default_value=0,
                                        minvalue=-167,
                                        maxvalue=167,
                                    ),
                                ),
                                (
                                    2 * 86400,
                                    _("two days"),
                                    Integer(
                                        label=_("Timezone offset"),
                                        unit=_("hours"),
                                        default_value=0,
                                        minvalue=-47,
                                        maxvalue=47,
                                    ),
                                ),
                                (
                                    86400,
                                    _("day"),
                                    DropdownChoice(
                                        label=_("in timezone"),
                                        choices=[
                                            (-12, _("UTC -12 hours")),
                                            (-11, _("UTC -11 hours")),
                                            (-10, _("UTC -10 hours")),
                                            (-9, _("UTC -9 hours")),
                                            (-8, _("UTC -8 hours")),
                                            (-7, _("UTC -7 hours")),
                                            (-6, _("UTC -6 hours")),
                                            (-5, _("UTC -5 hours")),
                                            (-4, _("UTC -4 hours")),
                                            (-3, _("UTC -3 hours")),
                                            (-2, _("UTC -2 hours")),
                                            (-1, _("UTC -1 hour")),
                                            (0, _("UTC")),
                                            (1, _("UTC +1 hour")),
                                            (2, _("UTC +2 hours")),
                                            (3, _("UTC +3 hours")),
                                            (4, _("UTC +4 hours")),
                                            (5, _("UTC +5 hours")),
                                            (6, _("UTC +8 hours")),
                                            (7, _("UTC +7 hours")),
                                            (8, _("UTC +8 hours")),
                                            (9, _("UTC +9 hours")),
                                            (10, _("UTC +10 hours")),
                                            (11, _("UTC +11 hours")),
                                            (12, _("UTC +12 hours")),
                                        ],
                                        default_value=0,
                                    ),
                                ),
                                (3600, _("hour")),
                                (900, _("15 minutes")),
                                (300, _("5 minutes")),
                                (60, _("minute")),
                                (10, _("10 seconds")),
                            ],
                            default_value=3600,
                        ),
                    ),
                    (
                        "count",
                        Integer(
                            title=_("Number of expected messages"),
                            minvalue=1,
                        ),
                    ),
                    (
                        "merge",
                        MigrateNotUpdated(
                            valuespec=CascadingDropdown(
                                title=_("Merge with open event"),
                                help=_(
                                    "If there already exists an open event because of absent "
                                    "messages according to this rule, you can optionally merge "
                                    "the new incident with the existing event or create a new "
                                    "event for each interval with absent messages."
                                ),
                                choices=[
                                    ("open", _("Merge if there is an open un-acknowledged event")),
                                    (
                                        "acked",
                                        _("Merge even if there is an acknowledged event"),
                                        Checkbox(
                                            title=_("Reset acknowledged state"),
                                            label=_(
                                                'Reset acknowledged events back to "open" on merge'
                                            ),
                                            help=_(
                                                "The state of the event is reset back to "
                                                '"open" in this case. This behavior is based on the '
                                                "assumption that you want to be informed when there is "
                                                "new information. However, there are also use cases where "
                                                "new incoming messages should be counted to the already "
                                                'existing event in the "ack" state and the "ack" '
                                                "state should be kept. To achieve this, the configuration "
                                                'option "Reset acknowledged state" can be disabled below.'
                                            ),
                                        ),
                                    ),
                                    (
                                        "never",
                                        _("Create a new event for each incident - never merge"),
                                    ),
                                ],
                                default_value="open",
                            ),
                            # The "ackend" sub option was introduced with 1.6.0p20
                            migrate=lambda v: ("acked", True) if v == "acked" else v,
                        ),
                    ),
                ],
            ),
        ),
        (
            "delay",
            Age(
                title=_("Delay event creation"),
                help=_(
                    "The creation of an event will be delayed by this time period. This "
                    "does only make sense for events that can be cancelled by a negative "
                    "rule."
                ),
            ),
        ),
        (
            "livetime",
            Tuple(
                title=_("Limit event lifetime"),
                help=_(
                    "If you set a lifetime of an event, then it will automatically be "
                    "deleted after that time if, even if no action has taken by the user. You can "
                    "decide whether to expire open, acknowledged or both types of events. The lifetime "
                    "always starts when the event is entering the open state."
                ),
                elements=[
                    Age(),
                    ListChoice(
                        choices=[
                            ("open", _("Expire events that are in the state <i>open</i>")),
                            ("ack", _("Expire events that are in the state <i>acknowledged</i>")),
                        ],
                        default_value=["open"],
                    ),
                ],
            ),
        ),
        (
            "match",
            RegExp(
                title=_("Text to match"),
                help=_(
                    "The rule only applies when the given regular expression matches "
                    "the message text (infix search)."
                ),
                size=64,
                mode=RegExp.infix,
                case_sensitive=False,
            ),
        ),
        (
            "match_site",
            DualListChoice(
                title=_("Match site"),
                help=_("Apply this rule only on the following sites"),
                choices=get_event_console_site_choices(),
                locked_choices=list(
                    enabled_sites().keys() - dict(get_event_console_site_choices()).keys()
                ),
                locked_choices_text_singular=_("%d locked site"),
                locked_choices_text_plural=_("%d locked sites"),
            ),
        ),
        (
            "match_host",
            RegExp(
                title=_("Match host"),
                help=_(
                    "The rule only applies when the given regular expression matches "
                    "the host name the message originates from. Note: in some cases the "
                    "event might use the IP address instead of the host name."
                ),
                mode=RegExp.complete,
                case_sensitive=False,
            ),
        ),
        (
            "match_ipaddress",
            IPNetwork(
                ip_class=None,
                title=_("Match original source IP address or network"),
                help=_(
                    "The rule only applies when the event is being received from a "
                    "certain IP address. You can specify either a single IP address "
                    "or an IPv4/IPv6 network in the notation X.X.X.X/Bits or X:X:.../Bits for IPv6"
                ),
            ),
        ),
        (
            "match_application",
            RegExp(
                title=_("Match syslog application (tag)"),
                help=_("Regular expression for matching the syslog tag (case insensitive)"),
                size=64,
                mode=RegExp.infix,
                case_sensitive=False,
            ),
        ),
        (
            "match_priority",
            Tuple(
                title=_("Match syslog priority"),
                help=_("Define a range of syslog priorities this rule matches"),
                orientation="horizontal",
                show_titles=False,
                elements=[
                    DropdownChoice(
                        label=_("from:"),
                        choices=syslog_priorities,
                        default_value=4,
                    ),
                    DropdownChoice(
                        label=_(" to:"),
                        choices=syslog_priorities,
                        default_value=0,
                    ),
                ],
            ),
        ),
        (
            "match_facility",
            DropdownChoice(
                title=_("Match syslog facility"),
                help=_(
                    "Make the rule match only if the message has a certain syslog facility. "
                    "Messages not having a facility are classified as <tt>user</tt>."
                ),
                choices=syslog_facilities,
            ),
        ),
        (
            "match_sl",
            Tuple(
                title=_("Match service level"),
                help=_(
                    "This setting is only useful if you've configured service levels for hosts. "
                    "If the event results from forwarded service notifications or logwatch "
                    "messages the service's configured service level is used here. In such cases "
                    "you can make this rule match only certain service levels."
                ),
                orientation="horizontal",
                show_titles=False,
                elements=[
                    DropdownChoice(
                        label=_("from:"),
                        choices=service_levels,
                        prefix_values=True,
                    ),
                    DropdownChoice(
                        label=_(" to:"),
                        choices=service_levels,
                        prefix_values=True,
                    ),
                ],
            ),
        ),
        (
            "match_timeperiod",
            watolib.timeperiods.TimeperiodSelection(
                title=_("Match only during time period"),
                help=_(
                    "Match this rule only during times where the selected time period from the monitoring "
                    "system is active. The Time Period definitions are taken from the monitoring core that "
                    "is running on the same host or OMD site as the event daemon. Please note, that this "
                    "selection only offers time periods that are defined with Setup."
                ),
            ),
        ),
        (
            "match_ok",
            RegExp(
                title=_("Text to cancel event(s)"),
                help=_(
                    "If a matching message appears with this text, then events created "
                    "by this rule will automatically be cancelled if host, application and match groups match. "
                    'If this expression has fewer match groups than "Text to match", '
                    "it will cancel all events where the specified groups match the same number "
                    "of groups in the initial text, starting from the left."
                ),
                size=64,
                mode=RegExp.infix,
                case_sensitive=False,
            ),
        ),
        (
            "cancel_priority",
            Tuple(
                title=_("Syslog priority to cancel event"),
                help=_(
                    "If the priority of the event lies within this range and either no text to cancel "
                    "is specified or that text also matched, then events created with this rule will "
                    "automatically be cancelled (if host, application, facility and match groups match)."
                ),
                orientation="horizontal",
                show_titles=False,
                elements=[
                    DropdownChoice(
                        label=_("from:"),
                        choices=syslog_priorities,
                        default_value=7,
                    ),
                    DropdownChoice(
                        label=_(" to:"),
                        choices=syslog_priorities,
                        default_value=5,
                    ),
                ],
            ),
        ),
        (
            "cancel_application",
            RegExp(
                title=_("Syslog application to cancel event"),
                help=_(
                    "If the application of the message matches this regular expression "
                    "(case insensitive) and either no text to cancel is specified or "
                    "that text also matched, then events created by this rule will "
                    "automatically be cancelled (if host, facility and match groups match)."
                ),
                mode=RegExp.infix,
                case_sensitive=False,
            ),
        ),
        (
            "invert_matching",
            Checkbox(
                title=_("Invert matching"),
                label=_(
                    "Negate match: Execute this rule if the upper conditions are <b>not</b> fulfilled."
                ),
                help=_(
                    "By activating this checkbox the complete combined rule conditions will be inverted. That "
                    "means that this rule with be executed, if at least on of the conditions does <b>not</b> match. "
                    "This can e.g. be used for skipping a rule pack if the message text does not contain <tt>ORA-</tt>. "
                    "Please note: When an inverted rule matches there can never be match groups."
                ),
            ),
        ),
        (
            "set_text",
            TextInput(
                title=_("Rewrite message text"),
                help=_(
                    "Replace the message text with this text. If you have bracketed "
                    "groups in the text to match, then you can use the placeholders "
                    "<tt>\\1</tt>, <tt>\\2</tt>, etc. for inserting the first, second "
                    "etc matching group."
                )
                + _(
                    "The placeholder <tt>\\0</tt> will be replaced by the original text of this field. "
                    "This allows you to add new information at the beginning or at the end. "
                )
                + _(
                    "You can also use the placeholders $MATCH_GROUPS_MESSAGE_1$ for message match groups and "
                    "$MATCH_GROUPS_SYSLOG_APPLICATION_1$</tt> for the syslog application match groups."
                ),
                size=64,
                allow_empty=False,
            ),
        ),
        (
            "set_host",
            TextInput(
                title=_("Rewrite host name"),
                help=_(
                    "Replace the host name with this text. If you have bracketed "
                    "groups in the text to match, then you can use the placeholders "
                    "<tt>\\1</tt>, <tt>\\2</tt>, etc. for inserting the first, second "
                    "etc matching group."
                )
                + _(
                    "The placeholder <tt>\\0</tt> will be replaced by the original text of this field "
                    "to match. Note that as an alternative, you may also use the rule "
                    "Host name translation for Incoming Messages in the Global Settings "
                    "of the EC to accomplish your task."
                )
                + _(
                    "You can also use the placeholders $MATCH_GROUPS_MESSAGE_1$ for message match groups and "
                    "$MATCH_GROUPS_SYSLOG_APPLICATION_1$</tt> for the syslog application match groups."
                ),
                allow_empty=False,
            ),
        ),
        (
            "set_application",
            TextInput(
                title=_("Rewrite application"),
                help=_(
                    "Replace the application (syslog tag) with this text. If you have bracketed "
                    "groups in the text to match, then you can use the placeholders "
                    "<tt>\\1</tt>, <tt>\\2</tt>, etc. for inserting the first, second "
                    "etc matching group."
                )
                + _(
                    "The placeholder <tt>\\0</tt> will be replaced by the original text of this field. "
                    "This allows you to add new information at the beginning or at the end."
                )
                + _(
                    "You can also use the placeholders $MATCH_GROUPS_MESSAGE_1$ for message match groups and "
                    "$MATCH_GROUPS_SYSLOG_APPLICATION_1$</tt> for the syslog application match groups."
                ),
                allow_empty=False,
            ),
        ),
        (
            "set_comment",
            TextInput(
                title=_("Add comment"),
                help=_(
                    "Attach a comment to the event. If you have bracketed "
                    "groups in the text to match, then you can use the placeholders "
                    "<tt>\\1</tt>, <tt>\\2</tt>, etc. for inserting the first, second "
                    "etc. matching group."
                )
                + _(
                    "The placeholder <tt>\\0</tt> will be replaced by the original message text. "
                    "This allows you to add new information at the beginning or at the end."
                ),
                size=64,
                allow_empty=False,
            ),
        ),
        (
            "set_contact",
            TextInput(
                title=_("Add contact information"),
                help=_(
                    "Attach information about a contact person. If you have bracketed "
                    "groups in the text to match, then you can use the placeholders "
                    "<tt>\\1</tt>, <tt>\\2</tt>, etc. for inserting the first, second "
                    "etc. matching group."
                )
                + _(
                    "The placeholder <tt>\\0</tt> will be replaced by the original text of this field. "
                    "This allows you to add new information at the beginning or at the end."
                ),
                size=64,
                allow_empty=False,
            ),
        ),
    ]

    return Dictionary(
        title=_("Rule Properties"),
        elements=elements,
        optional_keys=[
            "delay",
            "livetime",
            "count",
            "expect",
            "match_priority",
            "match_priority",
            "match_facility",
            "match_sl",
            "match_host",
            "match_site",
            "match_ipaddress",
            "match_application",
            "match_timeperiod",
            "set_text",
            "set_host",
            "set_application",
            "set_comment",
            "set_contact",
            "cancel_priority",
            "cancel_application",
            "match_ok",
            "contact_groups",
        ],
        headers=[
            (
                _("Rule Properties"),
                ["id", "description", "comment", "docu_url", "disabled", "customer"],
            ),
            (
                _("Matching Criteria"),
                [
                    "match",
                    "match_site",
                    "match_host",
                    "match_ipaddress",
                    "match_application",
                    "match_priority",
                    "match_facility",
                    "match_sl",
                    "match_ok",
                    "cancel_priority",
                    "cancel_application",
                    "match_timeperiod",
                    "invert_matching",
                ],
            ),
            (
                _("Outcome & Action"),
                [
                    "state",
                    "sl",
                    "contact_groups",
                    "actions",
                    "actions_in_downtime",
                    "cancel_actions",
                    "cancel_action_phases",
                    "drop",
                    "autodelete",
                    "event_limit",
                ],
            ),
            (_("Counting & Timing"), ["count", "expect", "delay", "livetime"]),
            (
                _("Rewriting"),
                ["set_text", "set_host", "set_application", "set_comment", "set_contact"],
            ),
        ],
        render="form",
        form_narrow=True,
    )


# .
#   .--Load & Save---------------------------------------------------------.
#   |       _                    _    ___     ____                         |
#   |      | |    ___   __ _  __| |  ( _ )   / ___|  __ ___   _____        |
#   |      | |   / _ \ / _` |/ _` |  / _ \/\ \___ \ / _` \ \ / / _ \       |
#   |      | |__| (_) | (_| | (_| | | (_>  <  ___) | (_| |\ V /  __/       |
#   |      |_____\___/ \__,_|\__,_|  \___/\/ |____/ \__,_| \_/ \___|       |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Loading and saving of rule packs                                    |
#   '----------------------------------------------------------------------'


def _save_mkeventd_rules(rule_packs: Iterable[ec.ECRulePack]) -> None:
    ec.save_rule_packs(
        rule_packs, pretty_print=active_config.mkeventd_pprint_rules, path=ec.rule_pack_dir()
    )


def _export_mkp_rule_pack(rule_pack: ec.ECRulePack) -> None:
    ec.export_rule_pack(
        rule_pack, pretty_print=active_config.mkeventd_pprint_rules, path=ec.mkp_rule_pack_dir()
    )


class SampleConfigGeneratorECSampleRulepack(SampleConfigGenerator):
    @classmethod
    def ident(cls) -> str:
        return "ec_sample_rule_pack"

    @classmethod
    def sort_index(cls) -> int:
        return 50

    def generate(self) -> None:
        _save_mkeventd_rules([ec.default_rule_pack([])])


# .
#   .--Setup---------------------------------------------------------------.
#   |                     ____       _                                     |
#   |                    / ___|  ___| |_ _   _ _ __                        |
#   |                    \___ \ / _ \ __| | | | '_ \                       |
#   |                     ___) |  __/ |_| |_| | |_) |                      |
#   |                    |____/ \___|\__|\__,_| .__/                       |
#   |                                         |_|                          |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


class ABCEventConsoleMode(WatoMode, abc.ABC):
    def __init__(self) -> None:
        config_domain = config_domain_registry[EVENT_CONSOLE]
        assert isinstance(config_domain, ConfigDomainEventConsole)
        self._config_domain = config_domain
        self._rule_packs = list(ec.load_rule_packs())
        super().__init__()

    def _verify_ec_enabled(self) -> None:
        if not active_config.mkeventd_enabled:
            raise MKUserError(None, _('The Event Console is disabled ("omd config").'))

    def _search_expression(self) -> str | None:
        return get_search_expression()

    def _rule_pack_with_id(self, rule_pack_id: str | None) -> tuple[int, ec.ECRulePack]:
        for nr, entry in enumerate(self._rule_packs):
            if entry["id"] == rule_pack_id:
                return nr, entry
        raise MKUserError(None, _("The requested rule pack does not exist."))

    def _event_from_html_vars(self, varprefix: str) -> ec.Event:
        vs = self._vs_mkeventd_event()
        value = vs.from_html_vars(varprefix)
        vs.validate_value(value, varprefix)
        # cast needed because ValueSpecs don't obey "Parse, don't validate!"
        return cast(ec.Event, value)

    def _show_event_simulator(self) -> ec.Event | None:
        event = user.load_file("simulated_event", {})
        with html.form_context("simulator"):
            self._vs_mkeventd_event().render_input("event", event)
            forms.end()
            html.hidden_fields()
            html.button("_simulate", _("Try out"))
            html.button("_generate", _("Generate event"))
        html.br()

        return (
            self._event_from_html_vars("event")
            if request.var("_simulate") or request.var("_generate")
            else None
        )

    def _event_simulation_action(self) -> bool:
        if not request.var("_simulate") and not request.var("_generate"):
            return False

        event = self._event_from_html_vars("event")
        user.save_file("simulated_event", event)

        if request.var("_simulate"):
            return True

        if not event.get("application"):
            raise MKUserError("event_p_application", _("Please specify an application name"))
        if not event.get("host"):
            raise MKUserError("event_p_host", _("Please specify a host name"))
        rfc = send_event(event)
        flash(
            HTML.with_escaping(_("Test event generated and sent to Event Console."))
            + HTMLWriter.render_br()
            + HTMLWriter.render_pre(rfc)
        )
        return True

    def _add_change(self, action_name: str, text: str) -> None:
        _changes.add_change(
            action_name=action_name,
            text=text,
            user_id=user.id,
            domains=[self._config_domain],
            sites=_get_event_console_sync_sites(),
            use_git=active_config.wato_use_git,
        )

    def _get_rule_pack_to_mkp_map(self) -> dict[str, Any]:
        return (
            {}
            if edition(cmk.utils.paths.omd_root) is Edition.CRE
            else cmk.mkp_tool.id_to_mkp(
                cmk.mkp_tool.Installer(cmk.utils.paths.installed_packages_dir),
                cmk.mkp_tool.all_rule_pack_files(ec.mkp_rule_pack_dir()),
                cmk.mkp_tool.PackagePart.EC_RULE_PACKS,
            )
        )

    def _vs_mkeventd_event(self) -> Dictionary:
        """Valuespec for simulating an event"""
        return Dictionary(
            title=_("Event Simulator"),
            help=_("You can simulate an event here and check out which rules are matching."),
            render="form",
            form_narrow=True,
            optional_keys=False,
            elements=[
                (
                    "text",
                    TextInput(
                        title=_("Message text"),
                        size=30,
                        try_max_width=True,
                        allow_empty=False,
                        default_value=_("Still nothing happened."),
                    ),
                ),
                (
                    "application",
                    TextInput(
                        title=_("Application name"),
                        help=_("The syslog tag"),
                        size=40,
                        default_value=_("Foobar-Daemon"),
                        allow_empty=True,
                    ),
                ),
                (
                    "host",
                    TextInput(
                        title=_("Host lookup element"),
                        help=_("Host name, IP address or host alias the event is relevant for"),
                        size=40,
                        default_value=_("myhost089"),
                        allow_empty=True,
                        regex="^\\S*$",
                        regex_error=_("The host name may not contain spaces."),
                    ),
                ),
                (
                    "ipaddress",
                    IPAddress(
                        ip_class=None,
                        title=_("Event source IPv4/IPv6 address"),
                        help=_("Original IP address the event was received from"),
                        default_value="1.2.3.4",
                    ),
                ),
                (
                    "priority",
                    DropdownChoice(
                        title=_("Syslog priority"),
                        choices=syslog_priorities,
                        default_value=5,
                    ),
                ),
                (
                    "facility",
                    DropdownChoice(
                        title=_("Syslog facility"),
                        choices=syslog_facilities,
                        default_value=1,
                    ),
                ),
                (
                    "sl",
                    DropdownChoice(
                        title=_("Service level"),
                        choices=service_levels,
                        prefix_values=True,
                    ),
                ),
                (
                    "site",
                    DropdownChoice(
                        title=_("Simulate for site"),
                        choices=get_event_console_site_choices,
                    ),
                ),
            ],
        )


def _get_rule_stats_from_ec() -> Mapping[str, int]:
    # Add information about rule hits: If we are running on OMD then we know
    # the path to the state retention file of mkeventd and can read the rule
    # statistics directly from that file.
    rule_stats: dict[str, int] = {}
    for rule_id, count in sites.live().query("GET eventconsolerules\nColumns: rule_id rule_hits\n"):
        rule_stats.setdefault(rule_id, 0)
        rule_stats[rule_id] += count
    return rule_stats


class ModeEventConsoleRulePacks(ABCEventConsoleMode):
    @classmethod
    def name(cls) -> str:
        return "mkeventd_rule_packs"

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return ["mkeventd.edit"]

    def title(self) -> str:
        return _("Event Console rule packs")

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        menu = PageMenu(
            dropdowns=[
                PageMenuDropdown(
                    name="rule_packs",
                    title=_("Rule packs"),
                    topics=list(self._page_menu_topics_rules()),
                ),
                PageMenuDropdown(
                    name="event_console",
                    title=_("Event Console"),
                    topics=list(self._page_menu_topics_mkeventd()),
                ),
            ],
            breadcrumb=breadcrumb,
            inpage_search=PageMenuSearch(),
        )
        menu.add_doc_reference(_("The Event Console"), DocReference.EVENTCONSOLE)

        return menu

    def _page_menu_topics_rules(self) -> Iterator[PageMenuTopic]:
        if not user.may("mkeventd.edit"):
            return

        yield PageMenuTopic(
            title=_("Add rule pack"),
            entries=[
                PageMenuEntry(
                    title=_("Add rule pack"),
                    icon_name="new",
                    item=make_simple_link(
                        makeuri_contextless(
                            request,
                            [
                                ("mode", "mkeventd_edit_rule_pack"),
                            ],
                        )
                    ),
                    is_shortcut=True,
                    is_suggested=True,
                ),
            ],
        )

    def _page_menu_topics_mkeventd(self) -> Iterator[PageMenuTopic]:
        if not user.may("mkeventd.edit"):
            return

        yield PageMenuTopic(
            title=_("Local Event Console"),
            entries=[
                PageMenuEntry(
                    title=_("Reset counters"),
                    icon_name="reload_cmk",
                    item=make_simple_link(
                        make_confirm_delete_link(
                            url=make_action_link(
                                [("mode", "mkeventd_rule_packs"), ("_reset_counters", "1")]
                            ),
                            title=_("Reset all rule hit counters to zero"),
                            message=_("This affects all rule packs."),
                            confirm_button=_("Reset"),
                        )
                    ),
                ),
                _page_menu_entry_status(),
            ],
        )

        yield PageMenuTopic(
            title=_("Setup"),
            entries=[
                _page_menu_entry_settings(is_suggested=True),
                _page_menu_entry_rulesets(),
                _page_menu_entry_snmp_mibs(),
            ],
        )

    def action(self) -> ActionResult:
        if not transactions.check_transaction():
            return redirect(self.mode_url())

        if self._event_simulation_action():
            return None

        # Deletion of rule packs
        if request.has_var("_delete"):
            nr = request.get_integer_input_mandatory("_delete")
            rule_pack = self._rule_packs[nr]
            self._add_change(
                action_name="delete-rule-pack",
                text=_("Deleted rule pack %s") % rule_pack["id"],
            )
            del self._rule_packs[nr]
            _save_mkeventd_rules(self._rule_packs)

        # Reset all rule hit counters
        elif request.has_var("_reset_counters"):
            for site in _get_event_console_sync_sites():
                execute_command("RESETCOUNTERS", site=site)
            self._add_change(
                action_name="counter-reset",
                text=_("Reset all rule hit counters to zero"),
            )

        # Copy rules from master
        elif request.has_var("_copy_rules"):
            self._copy_rules_from_master()
            self._add_change(
                action_name="copy-rules-from-master",
                text=_("Copied the event rules from the central site into the local configuration"),
            )
            flash(_("Copied rules from central site"))
            return redirect(self.mode_url())

        # Move rule packs
        elif request.has_var("_move"):
            from_pos = request.get_integer_input_mandatory("_move")
            to_pos = request.get_integer_input_mandatory("_index")
            rule_pack = self._rule_packs[from_pos]
            del self._rule_packs[from_pos]  # make to_pos now match!
            self._rule_packs[to_pos:to_pos] = [rule_pack]
            _save_mkeventd_rules(self._rule_packs)
            self._add_change(
                action_name="move-rule-pack",
                text=_("Changed position of rule pack %s") % rule_pack["id"],
            )

        # Export rule pack
        elif request.has_var("_export"):
            nr = request.get_integer_input_mandatory("_export")
            try:
                rule_pack = self._rule_packs[nr]
            except KeyError:
                raise MKUserError("_export", _("The requested rule pack does not exist"))

            _export_mkp_rule_pack(rule_pack)
            self._rule_packs[nr] = ec.MkpRulePackProxy(rule_pack["id"])
            _save_mkeventd_rules(self._rule_packs)
            self._add_change(
                action_name="export-rule-pack",
                text=_("Made rule pack %s available for MKP export") % rule_pack["id"],
            )

        # Make rule pack non-exportable
        elif request.has_var("_dissolve"):
            nr = request.get_integer_input_mandatory("_dissolve")
            try:
                rp = self._rule_packs[nr]
            except KeyError:
                raise MKUserError("_dissolve", _("The requested rule pack does not exist"))
            if not isinstance(rp, ec.MkpRulePackProxy):
                raise MKUserError("_dissolve", _("rule pack was not exported"))
            self._rule_packs[nr] = rp.get_rule_pack_spec()
            _save_mkeventd_rules(self._rule_packs)
            ec.remove_exported_rule_pack(self._rule_packs[nr], ec.mkp_rule_pack_dir())
            self._add_change(
                action_name="dissolve-rule-pack",
                text=_("Removed rule_pack %s from MKP export") % self._rule_packs[nr]["id"],
            )

        # Reset to rule pack provided via MKP
        elif request.has_var("_reset"):
            nr = request.get_integer_input_mandatory("_reset")
            try:
                rp = ec.MkpRulePackProxy(self._rule_packs[nr]["id"])
                self._rule_packs[nr] = rp
            except KeyError:
                raise MKUserError("_reset", _("The requested rule pack does not exist"))
            _save_mkeventd_rules(self._rule_packs)
            self._add_change(
                action_name="reset-rule-pack",
                text=_("Reset the rules of rule pack %s to the ones provided via MKP") % rp.id_,
            )

        # Synchronize modified rule pack with MKP
        elif request.has_var("_synchronize"):
            nr = request.get_integer_input_mandatory("_synchronize")
            _export_mkp_rule_pack(self._rule_packs[nr])
            try:
                rp = ec.MkpRulePackProxy(self._rule_packs[nr]["id"])
                self._rule_packs[nr] = rp
            except KeyError:
                raise MKUserError("_synchronize", _("The requested rule pack does not exist"))
            _save_mkeventd_rules(self._rule_packs)
            self._add_change(
                action_name="synchronize-rule-pack",
                text=_("Synchronized MKP with the modified rule pack %s") % rp.id_,
            )

        # Update data structure after actions
        self._rule_packs = list(ec.load_rule_packs())
        return redirect(self.mode_url())

    def _copy_rules_from_master(self) -> None:
        answer = query_ec_directly(b"REPLICATE 0")
        if "rules" not in answer:
            raise MKGeneralException(_("Cannot get rules from local event daemon."))
        rule_packs = answer["rules"]
        _save_mkeventd_rules(rule_packs)

    def page(self) -> None:
        self._verify_ec_enabled()
        rep_mode = replication_mode()
        if rep_mode in ["sync", "takeover"]:
            copy_url = make_confirm_delete_link(
                url=make_action_link([("mode", "mkeventd_rule_packs"), ("_copy_rules", "1")]),
                title=_("Copy all event rules from the central site"),
                message=_("This will replace your local configuration"),
                confirm_button=_("Copy"),
            )
            html.show_warning(
                _(
                    "WARNING: This Event Console is currently running as a remote replication"
                    ". The rules edited here will not be used. Instead a copy of the rules of the "
                    "central site are being used in the case of a takeover. The same holds for the event "
                    "actions in the global settings."
                )
                + html.render_br()
                + html.render_br()
                + _(
                    "If you want you can copy the ruleset of "
                    "the central site into your local configuration: "
                )
                + html.render_icon_button(copy_url, _("Copy rules from central site"), "clone")
            )

        elif rep_mode == "stopped":
            html.show_error(_("The Event Console is currently not running."))

        search_expression = self._search_expression()
        if search_expression:
            found_packs = self._filter_mkeventd_rule_packs(search_expression, self._rule_packs)
            title = _("Found rule packs")
        else:
            found_packs = {}
            title = _("Rule packs")

        # Simulator
        event = self._show_event_simulator()
        if not self._rule_packs:
            html.show_message(
                _(
                    "You have not created any rule packs yet. The Event Console is useless unless "
                    "you have activated <i>Force message archiving</i> in the global settings."
                )
            )
        elif search_expression and not found_packs:
            html.show_message(_("Found no rule packs."))
            return

        id_to_mkp = self._get_rule_pack_to_mkp_map()

        have_match = False

        rule_stats = _get_rule_stats_from_ec()
        rule_pack_hits: dict[str, int] = {}
        for rp in ec.load_rule_packs():
            pack_hits = 0
            for rule in rp["rules"]:
                pack_hits += rule_stats.get(rule["id"], 0)
            rule_pack_hits[rp["id"]] = pack_hits

        with table_element(css="ruleset", limit=None, sortable=False, title=title) as table:
            for nr, rule_pack in enumerate(self._rule_packs):
                id_ = rule_pack["id"]
                type_ = ec.RulePackType.type_of(rule_pack, id_to_mkp)

                table.row(css=["matches_search"] if id_ in found_packs else [])
                table.cell("#", css=["narrow nowrap"])
                html.write_text_permissive(nr)
                table.cell(_("Actions"), css=["buttons"])

                edit_url = makeuri_contextless(
                    request,
                    [("mode", "mkeventd_edit_rule_pack"), ("edit", nr)],
                )
                html.icon_button(edit_url, _("Edit properties of this rule pack"), "edit")

                # Cloning does not work until we have unique IDs
                # clone_url  = makeuri_contextless(request, [("mode", "mkeventd_edit_rule_pack"), ("clone", nr)])
                # html.icon_button(clone_url, _("Create a copy of this rule pack"), "clone")

                drag_url = make_action_link([("mode", "mkeventd_rule_packs"), ("_move", nr)])
                html.element_dragger_url("tr", base_url=drag_url)

                if type_ == ec.RulePackType.internal:
                    delete_url = make_confirm_delete_link(
                        url=make_action_link([("mode", "mkeventd_rule_packs"), ("_delete", nr)]),
                        title=_("Delete rule pack #%d") % nr,
                        suffix=rule_pack["title"],
                        message=_("ID: %s") % id_
                        + "<br>"
                        + _("Used rules: %d") % len(rule_pack["rules"]),
                    )
                    html.icon_button(delete_url, _("Delete this rule pack"), "delete")
                else:
                    html.disabled_icon_button("trans")  # Invisible dummy button for icon spacing

                rules_url_vars = [("mode", "mkeventd_rules"), ("rule_pack", id_)]
                if found_packs.get(id_):
                    rules_url_vars.append(("search", search_expression))
                rules_url = makeuri_contextless(request, rules_url_vars)
                html.icon_button(rules_url, _("Edit the rules in this pack"), "rules")

                if edition(cmk.utils.paths.omd_root) is not Edition.CRE:
                    # Icons for mkp export (CEE/CME only)
                    if type_ == ec.RulePackType.internal:
                        export_url = make_action_link(
                            [("mode", "mkeventd_rule_packs"), ("_export", nr)]
                        )
                        html.icon_button(
                            export_url,
                            _("Make this rule pack available in the Extension Packages module"),
                            {
                                "icon": "mkps",
                                "emblem": "add",
                            },
                        )
                    elif type_ == ec.RulePackType.exported:
                        dissolve_url = make_action_link(
                            [("mode", "mkeventd_rule_packs"), ("_dissolve", nr)]
                        )
                        html.icon_button(
                            dissolve_url,
                            _("Remove this rule pack from the Extension Packages module"),
                            {
                                "icon": "mkps",
                                "emblem": "disable",
                            },
                        )
                    elif type_ == ec.RulePackType.modified_mkp:
                        reset_url = make_action_link(
                            [("mode", "mkeventd_rule_packs"), ("_reset", nr)]
                        )
                        html.icon_button(
                            reset_url,
                            _("Reset rule pack to the MKP version"),
                            {
                                "icon": "mkps",
                                "emblem": "disable",
                            },
                        )
                        sync_url = make_action_link(
                            [("mode", "mkeventd_rule_packs"), ("_synchronize", nr)]
                        )
                        html.icon_button(
                            sync_url,
                            _("Synchronize MKP with modified version"),
                            {
                                "icon": "mkps",
                                "emblem": "refresh",
                            },
                        )

                    table.cell(_("State"), css=["buttons"])
                    if type_ == ec.RulePackType.exported:
                        html.icon(
                            "mkps",
                            _("This rule pack can be packaged with the Extension Packages module."),
                        )
                    elif type_ == ec.RulePackType.unmodified_mkp:
                        html.icon(
                            "mkps", _("This rule pack is provided via the MKP %s.") % id_to_mkp[id_]
                        )
                    elif type_ == ec.RulePackType.modified_mkp:
                        html.icon(
                            {
                                "icon": "mkps",
                                "emblem": "warning",
                            },
                            _(
                                "This rule pack is modified. Originally it was provided via the MKP %s."
                            )
                            % id_to_mkp[id_],
                        )

                if rule_pack["disabled"]:
                    html.icon(
                        "disabled",
                        _(
                            "This rule pack is currently disabled. None of its rules will be applied."
                        ),
                    )

                # Simulation of all rules in this pack
                elif event:
                    matches = 0
                    cancelling_matches = 0
                    skips = 0

                    for rule in rule_pack["rules"]:
                        result = match_event_rule(rule_pack, rule, event)
                        if isinstance(result, ec.MatchSuccess):
                            cancelling, groups = result.cancelling, result.match_groups

                            if not cancelling and rule.get("drop") == "skip_pack":
                                matches += 1
                                skips = 1
                                break

                            if cancelling and matches == 0:
                                cancelling_matches += 1

                            matches += 1

                    if matches == 0:
                        msg = _("None of the rules in this pack matches")
                        icon = "hyphen"
                    else:
                        msg = _("Number of matching rules in this pack: %d") % matches
                        if skips:
                            msg += _(", the first match skips this rule pack")
                            icon = "hyphen"
                        else:
                            if cancelling:
                                msg += _(", first match is a cancelling match")
                            if groups:
                                msg += _(", match groups of decisive match: %s") % ",".join(
                                    [g or _("&lt;None&gt;") for g in groups]
                                )
                            if have_match:
                                msg += _(
                                    ", but it is overruled by a match in a previous rule pack."
                                )
                                icon = "checkmark_plus"
                            else:
                                icon = "checkmark"
                                have_match = True
                    html.icon(icon, msg)

                table.cell(_("ID"), id_)
                table.cell(_("Title"), rule_pack["title"])

                if edition(cmk.utils.paths.omd_root) is Edition.CME:
                    table.cell(_("Customer"))
                    if "customer" in rule_pack:
                        html.write_text_permissive(customer_api().get_customer_name(rule_pack))

                table.cell(
                    _("Rules"),
                    HTMLWriter.render_a("%d" % len(rule_pack["rules"]), href=rules_url),
                    css=["number"],
                )

                table.cell(_("Hits"), str(rule_pack_hits[rule_pack["id"]]), css=["number"])

    def _filter_mkeventd_rule_packs(
        self, search_expression: str, rule_packs: Iterable[ec.ECRulePack]
    ) -> dict[str, list[ec.Rule]]:
        found_packs: dict[str, list[ec.Rule]] = {}
        for rule_pack_ in rule_packs:
            rule_pack = cast(ec.ECRulePackSpec, rule_pack_)
            if (
                search_expression in rule_pack["id"].lower()
                or search_expression in rule_pack["title"].lower()
            ):
                found_packs.setdefault(rule_pack["id"], [])
            for rule in rule_pack.get("rules", []):
                match = rule.get("match", "")
                if not isinstance(match, str):  # TODO: Remove when we have CompiledRule
                    raise ValueError(f"attribute match of rule {rule['id']} already compiled")
                if any(
                    search_expression in searchable_rule_item.lower()
                    for searchable_rule_item in (rule["id"], rule.get("description", ""), match)
                ):
                    found_rules = found_packs.setdefault(rule_pack["id"], [])
                    found_rules.append(rule)
        return found_packs


T = TypeVar("T")


def _deref(x: T | Callable[[], T]) -> T:
    return x() if callable(x) else x


class ModeEventConsoleRules(ABCEventConsoleMode):
    @classmethod
    def name(cls) -> str:
        return "mkeventd_rules"

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return ["mkeventd.edit"]

    @classmethod
    def parent_mode(cls) -> type[WatoMode] | None:
        return ModeEventConsoleRulePacks

    # pylint does not understand this overloading
    @overload
    @classmethod
    def mode_url(cls, *, rule_pack: str) -> str: ...

    @overload
    @classmethod
    def mode_url(cls, **kwargs: str) -> str: ...

    @classmethod
    def mode_url(cls, **kwargs: str) -> str:
        return super().mode_url(**kwargs)

    def _breadcrumb_url(self) -> str:
        return self.mode_url(rule_pack=self._rule_pack_id)

    def _from_vars(self) -> None:
        self._rule_pack_id = request.get_ascii_input_mandatory("rule_pack")
        self._rule_pack_nr, self._rule_pack = self._rule_pack_with_id(self._rule_pack_id)

    def title(self) -> str:
        return _("Rule pack %s") % self._rule_pack["title"]

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        menu = PageMenu(
            dropdowns=[
                PageMenuDropdown(
                    name="rules",
                    title=_("Rules"),
                    topics=list(self._page_menu_topics_rules()),
                ),
                PageMenuDropdown(
                    name="related",
                    title=_("Related"),
                    topics=[
                        PageMenuTopic(
                            title=_("Setup"),
                            entries=list(_page_menu_entries_related_ec(self.name())),
                        ),
                    ],
                ),
            ],
            breadcrumb=breadcrumb,
            inpage_search=PageMenuSearch(),
        )

        return menu

    def _page_menu_topics_rules(self) -> Iterator[PageMenuTopic]:
        if not user.may("mkeventd.edit"):
            return

        yield PageMenuTopic(
            title=_("Add rule"),
            entries=[
                PageMenuEntry(
                    title=_("Add rule"),
                    icon_name="new",
                    item=make_simple_link(
                        makeuri_contextless(
                            request,
                            [("mode", "mkeventd_edit_rule"), ("rule_pack", self._rule_pack_id)],
                        )
                    ),
                    is_shortcut=True,
                    is_suggested=True,
                ),
            ],
        )

        yield PageMenuTopic(
            title=_("Rule pack"),
            entries=[
                PageMenuEntry(
                    title=_("Edit properties"),
                    icon_name="edit",
                    item=make_simple_link(
                        makeuri_contextless(
                            request,
                            [("mode", "mkeventd_edit_rule_pack"), ("edit", self._rule_pack_nr)],
                        )
                    ),
                ),
            ],
        )

    def action(self) -> ActionResult:
        check_csrf_token()

        if not transactions.check_transaction():
            return redirect(self.mode_url(rule_pack=self._rule_pack_id))

        id_to_mkp = self._get_rule_pack_to_mkp_map()
        type_ = ec.RulePackType.type_of(self._rule_pack, id_to_mkp)

        if request.var("_move_to"):
            for move_nr, rule in enumerate(self._rule_pack["rules"]):
                move_var = "_move_to_%s" % rule["id"]
                if request.var(move_var):
                    other_pack_nr, other_pack = self._rule_pack_with_id(request.var(move_var))

                    other_type_ = ec.RulePackType.type_of(other_pack, id_to_mkp)
                    if other_type_ == ec.RulePackType.unmodified_mkp:
                        ec.override_rule_pack_proxy(other_pack_nr, self._rule_packs)

                    if type_ == ec.RulePackType.unmodified_mkp:
                        ec.override_rule_pack_proxy(self._rule_pack_nr, self._rule_packs)

                    self._rule_packs[other_pack_nr]["rules"] = [rule] + list(
                        self._rule_packs[other_pack_nr]["rules"]
                    )

                    rules = list(self._rule_packs[self._rule_pack_nr]["rules"])
                    del rules[move_nr]
                    self._rule_packs[self._rule_pack_nr]["rules"] = rules

                    if other_type_ == ec.RulePackType.exported:
                        _export_mkp_rule_pack(other_pack)
                    if type_ == ec.RulePackType.exported:
                        _export_mkp_rule_pack(self._rule_pack)
                    _save_mkeventd_rules(self._rule_packs)

                    self._add_change(
                        action_name="move-rule-to-pack",
                        text=_("Moved rule %s to pack %s") % (rule["id"], other_pack["id"]),
                    )
                    flash(_("Moved rule %s to pack %s") % (rule["id"], other_pack["title"]))
                    return None

        if self._event_simulation_action():
            return None

        if request.has_var("_delete"):
            nr = request.get_integer_input_mandatory("_delete")
            if type_ == ec.RulePackType.unmodified_mkp:
                ec.override_rule_pack_proxy(self._rule_pack_nr, self._rule_packs)
                rules = list(self._rule_packs[self._rule_pack_nr]["rules"])
            else:
                rules = list(self._rule_pack["rules"])

            self._add_change(
                action_name="delete-rule",
                text=_("Deleted rule %s") % rules[nr]["id"],
            )
            del rules[nr]

            self._rule_pack["rules"] = rules

            if type_ == ec.RulePackType.exported:
                _export_mkp_rule_pack(self._rule_pack)
            _save_mkeventd_rules(self._rule_packs)
            return redirect(self.mode_url(rule_pack=self._rule_pack_id))

        if request.has_var("_move"):
            from_pos = request.get_integer_input_mandatory("_move")
            to_pos = request.get_integer_input_mandatory("_index")

            if type_ == ec.RulePackType.unmodified_mkp:
                ec.override_rule_pack_proxy(self._rule_pack_nr, self._rule_packs)
                rules = list(self._rule_packs[self._rule_pack_nr]["rules"])
            else:
                rules = list(self._rule_pack["rules"])

            rule = rules[from_pos]
            del rules[from_pos]  # make to_pos now match!
            rules[to_pos:to_pos] = [rule]

            self._rule_pack["rules"] = rules

            if type_ == ec.RulePackType.exported:
                _export_mkp_rule_pack(self._rule_pack)
            _save_mkeventd_rules(self._rule_packs)

            self._add_change(
                action_name="move-rule",
                text=_("Changed position of rule %s") % rule["id"],
            )
        return redirect(self.mode_url(rule_pack=self._rule_pack_id))

    def page(self) -> None:
        self._verify_ec_enabled()
        search_expression = self._search_expression()

        found_rules: list[ec.Rule]
        if search_expression:
            found_rules = self._filter_mkeventd_rules(search_expression, self._rule_pack)
        else:
            found_rules = []

        rules = self._rule_pack["rules"]

        # Simulator
        event = self._show_event_simulator()
        if not rules:
            html.show_message(_("This package does not yet contain any rules."))
            return
        if search_expression and not found_rules:
            html.show_message(_("No rules found."))
            return

        if len(self._rule_packs) > 1:
            with html.form_context("move_to", method="POST"):
                self._show_table(event, found_rules, rules)
                html.hidden_field("_move_to", "yes")
                html.hidden_fields()
        else:
            self._show_table(event, found_rules, rules)

    def _show_table(
        self, event: ec.Event | None, found_rules: list[ec.Rule], rules: Collection[ec.Rule]
    ) -> None:
        # TODO: Rethink the typing of syslog_facilites/syslog_priorities.
        priorities = _deref(syslog_priorities)
        facilities = dict(_deref(syslog_facilities))

        # Show content of the rule pack
        with table_element(title=_("Rules"), css="ruleset", limit=None, sortable=False) as table:
            have_match = False
            hits = _get_rule_stats_from_ec()
            for nr, rule in enumerate(rules):
                table.row(css=["matches_search"] if rule in found_rules else [])
                delete_url = make_confirm_delete_link(
                    url=make_action_link(
                        [
                            ("mode", "mkeventd_rules"),
                            ("rule_pack", self._rule_pack_id),
                            ("_delete", nr),
                        ]
                    ),
                    title=_("Delete rule #%d") % nr,
                    message=_("ID: %s") % rule["id"],
                    suffix=rule.get("description", ""),
                )
                drag_url = make_action_link(
                    [("mode", "mkeventd_rules"), ("rule_pack", self._rule_pack_id), ("_move", nr)]
                )
                edit_url = _rule_edit_url(self._rule_pack_id, nr)
                clone_url = makeuri_contextless(
                    request,
                    [
                        ("mode", "mkeventd_edit_rule"),
                        ("rule_pack", self._rule_pack_id),
                        ("clone", nr),
                    ],
                )

                table.cell("#", css=["narrow nowrap"])
                html.write_text_permissive(nr)
                table.cell(_("Actions"), css=["buttons"])
                html.icon_button(edit_url, _("Edit this rule"), "edit")
                html.icon_button(clone_url, _("Create a copy of this rule"), "clone")
                html.element_dragger_url("tr", base_url=drag_url)
                html.icon_button(delete_url, _("Delete this rule"), "delete")

                table.cell("", css=["buttons"])
                if rule.get("disabled"):
                    html.icon(
                        "disabled", _("This rule is currently disabled and will not be applied")
                    )
                elif event:
                    event["host"] = cmk.utils.translations.translate_hostname(
                        eventd_configuration()["hostname_translation"], event["host"]
                    )
                    result = match_event_rule(self._rule_pack, rule, event)
                    if not isinstance(result, ec.MatchSuccess):
                        html.icon("hyphen", _("Rule does not match: %s") % result.reason)
                    else:
                        cancelling, groups = result.cancelling, result.match_groups
                        if have_match:
                            msg = _("This rule matches, but is overruled by a previous match.")
                            icon = "checkmark_plus"
                        else:
                            if cancelling:
                                msg = _("This rule does a cancelling match.")
                            else:
                                msg = _("This rule matches.")
                            icon = "checkmark"
                            have_match = True
                        if groups:
                            msg += _(" Match groups: %s") % ",".join(
                                [g or _("&lt;None&gt;") for g in groups]
                            )
                        html.icon(icon, msg)

                if rule.get("invert_matching"):
                    html.icon("inverted", _("Matching is inverted in this rule"))

                if rule.get("contact_groups") is not None:
                    html.icon(
                        "contactgroups",
                        _("This rule attaches contact group(s) to the events: %s")
                        % (", ".join(rule["contact_groups"]["groups"]) or _("(none)")),
                    )

                table.cell(_("ID"), HTMLWriter.render_a(rule["id"], edit_url))

                if edition(cmk.utils.paths.omd_root) is Edition.CME:
                    table.cell(_("Customer"))
                    if "customer" in self._rule_pack:
                        html.write_text_permissive(
                            "{} ({})".format(
                                customer_api().get_customer_name(self._rule_pack),
                                _("Set by rule pack"),
                            )
                        )
                    else:
                        html.write_text_permissive(customer_api().get_customer_name(rule))

                if rule.get("drop"):
                    table.cell(_("State"), css=["state statep nowrap"])
                    if rule["drop"] == "skip_pack":
                        html.write_text_permissive(_("SKIP PACK"))
                    else:
                        html.write_text_permissive(_("DROP"))
                else:
                    if isinstance(rule["state"], tuple):
                        stateval: Literal["text_pattern", 0, 1, 2, 3, -1] = rule["state"][0]
                    else:
                        stateval = rule["state"]
                    txt = {
                        0: _("OK"),
                        1: _("WARN"),
                        2: _("CRIT"),
                        3: _("UNKNOWN"),
                        -1: _("(syslog)"),
                        "text_pattern": _("(set by message text)"),
                    }[stateval]
                    table.cell(
                        _("State"),
                        HTMLWriter.render_span(txt, class_="state_rounded_fill"),
                        css=["state state%s" % stateval],
                    )

                # Syslog priority
                if "match_priority" in rule:
                    prio_from, prio_to = rule["match_priority"]
                    if prio_from == prio_to:
                        prio_text = priorities[prio_from][1]
                    else:
                        prio_text = priorities[prio_from][1][:2] + ".." + priorities[prio_to][1][:2]
                else:
                    prio_text = ""
                table.cell(_("Priority"), prio_text)

                # Syslog Facility
                table.cell(_("Facility"))
                if "match_facility" in rule:
                    facnr = rule["match_facility"]
                    html.write_text_permissive(facilities[facnr])

                table.cell(
                    _("Service level"),
                    dict(service_levels()).get(rule["sl"]["value"], rule["sl"]["value"]),
                )

                rh = hits.get(rule["id"], 0)
                table.cell(_("Hits"), str(rh) if hits else "", css=["number"])

                # Text to match
                match = rule.get("match")
                # ECRuleSpec the match type is wrong for the UI. In the config we only have str.
                # during EC runtime we may have a pattern in that field.
                assert not isinstance(match, re.Pattern)
                table.cell(_("Text to match"), match)

                # Description
                table.cell(_("Description"))
                url = rule.get("docu_url")
                if url:
                    html.icon_button(
                        url, _("Context information about this rule"), "url", target="_blank"
                    )
                    html.nbsp()
                html.write_text_permissive(rule.get("description", ""))

                # Move rule to other pack
                if len(self._rule_packs) > 1:
                    table.cell(_("Move to pack..."))
                    choices: Choices = [("", "")]
                    choices += [
                        (pack["id"], pack["title"])
                        for pack in self._rule_packs
                        if pack is not self._rule_pack
                    ]
                    html.dropdown("_move_to_%s" % rule["id"], choices, onchange="move_to.submit();")

    def _filter_mkeventd_rules(
        self, search_expression: str, rule_pack: ec.ECRulePack
    ) -> list[ec.Rule]:
        return [
            rule
            for rule in rule_pack.get("rules", [])
            if (
                search_expression in rule["id"].lower()
                or search_expression in rule.get("description", "").lower()
                or search_expression in _get_match(rule).lower()
            )
        ]


# TODO: Remove when we have CompiledRule
def _get_match(rule: ec.Rule) -> str:
    value = rule.get("match", "")
    if not isinstance(value, str):  # TODO: Remove when we have CompiledRule
        raise ValueError(f"attribute match of rule {rule['id']} already compiled")
    return value


def _add_change_for_sites(
    *,
    action_name: str,
    text: str,
    rule_or_rulepack: DictionaryModel | ec.ECRulePackSpec,
    config_domain: ConfigDomainEventConsole,
) -> None:
    """If CME, add the changes only for the customer's sites if customer is configured"""
    customer_id: str | None = rule_or_rulepack.get("customer")
    if edition(cmk.utils.paths.omd_root) is Edition.CME and customer_id is not None:
        sites_ = list(customer_api().get_sites_of_customer(customer_id).keys())
    else:
        sites_ = _get_event_console_sync_sites()

    _changes.add_change(
        action_name=action_name,
        text=text,
        user_id=user.id,
        domains=[config_domain],
        sites=sites_,
        use_git=active_config.wato_use_git,
    )


class ModeEventConsoleEditRulePack(ABCEventConsoleMode):
    @classmethod
    def name(cls) -> str:
        return "mkeventd_edit_rule_pack"

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return ["mkeventd.edit"]

    @classmethod
    def parent_mode(cls) -> type[WatoMode] | None:
        return ModeEventConsoleRulePacks

    def _from_vars(self) -> None:
        self._edit_nr = request.get_integer_input_mandatory("edit", -1)  # missing -> new rule pack
        self._new = self._edit_nr < 0

        if self._new:
            self._rule_pack: ec.ECRulePack = ec.default_rule_pack(rules=[])
        else:
            try:
                self._rule_pack = self._rule_packs[self._edit_nr]
            except IndexError:
                raise MKUserError("edit", _("The rule pack you are trying to edit does not exist."))

        id_to_mkp = self._get_rule_pack_to_mkp_map()
        self._type = ec.RulePackType.type_of(self._rule_pack, id_to_mkp)

    def title(self) -> str:
        if self._new:
            return _("Add rule pack")
        return _("Edit rule pack %s") % self._rule_packs[self._edit_nr]["id"]

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        menu = make_simple_form_page_menu(
            _("Rule pack"), breadcrumb, form_name="rule_pack", button_name="_save"
        )
        menu.dropdowns.insert(
            1,
            PageMenuDropdown(
                name="related",
                title=_("Related"),
                topics=[
                    PageMenuTopic(
                        title=_("Setup"),
                        entries=list(_page_menu_entries_related_ec(self.name())),
                    ),
                ],
            ),
        )
        return menu

    def action(self) -> ActionResult:
        if not transactions.check_transaction():
            return redirect(mode_url("mkeventd_rule_packs"))

        existing_rules = [] if self._new else self._rule_pack["rules"]

        vs = self._valuespec()
        rule_pack_dict = vs.from_html_vars("rule_pack")
        vs.validate_value(rule_pack_dict, "rule_pack")
        if edition(cmk.utils.paths.omd_root) is Edition.CME and "customer" in rule_pack_dict:
            self._rule_pack = ec.ECRulePackSpec(
                id=rule_pack_dict["id"],
                title=rule_pack_dict["title"],
                disabled=rule_pack_dict["disabled"],
                rules=existing_rules,
                customer=rule_pack_dict["customer"],
            )
        else:
            self._rule_pack = ec.ECRulePackSpec(
                id=rule_pack_dict["id"],
                title=rule_pack_dict["title"],
                disabled=rule_pack_dict["disabled"],
                rules=existing_rules,
            )

        new_id = self._rule_pack["id"]

        # Make sure that ID is unique
        for nr, other_rule_pack in enumerate(self._rule_packs):
            if self._new or nr != self._edit_nr:
                if other_rule_pack["id"] == new_id:
                    raise MKUserError(
                        "rule_pack_p_id", _("A rule pack with this ID already exists.")
                    )

        if self._new:
            self._rule_packs.insert(0, self._rule_pack)
        elif isinstance(rp := self._rule_packs[self._edit_nr], ec.MkpRulePackProxy):
            rp.rule_pack = self._rule_pack
            _export_mkp_rule_pack(self._rule_pack)
        elif self._type in (ec.RulePackType.internal, ec.RulePackType.modified_mkp):
            self._rule_packs[self._edit_nr] = self._rule_pack
        else:
            self._rule_packs[self._edit_nr] = self._rule_pack

        _save_mkeventd_rules(self._rule_packs)

        if self._new:
            _add_change_for_sites(
                action_name="new-rule-pack",
                text=_("Created new rule pack with id %s") % self._rule_pack["id"],
                rule_or_rulepack=self._rule_pack,
                config_domain=self._config_domain,
            )
        else:
            _add_change_for_sites(
                action_name="edit-rule-pack",
                text=_("Modified rule pack %s") % self._rule_pack["id"],
                rule_or_rulepack=self._rule_pack,
                config_domain=self._config_domain,
            )
        return redirect(mode_url("mkeventd_rule_packs"))

    def page(self) -> None:
        self._verify_ec_enabled()
        with html.form_context("rule_pack"):
            vs = self._valuespec()
            vs.render_input("rule_pack", dict(self._rule_pack))
            vs.set_focus("rule_pack")
            html.hidden_fields()

    def _valuespec(self) -> Dictionary:
        if self._type == ec.RulePackType.internal:
            return vs_mkeventd_rule_pack()
        return vs_mkeventd_rule_pack(
            fixed_id=self._rule_pack["id"], fixed_title=self._rule_pack["title"]
        )


class ModeEventConsoleEditRule(ABCEventConsoleMode):
    @classmethod
    def name(cls) -> str:
        return "mkeventd_edit_rule"

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return ["mkeventd.edit"]

    @classmethod
    def parent_mode(cls) -> type[WatoMode] | None:
        return ModeEventConsoleRules

    def _from_vars(self) -> None:
        if request.has_var("rule_pack"):
            self._rule_pack_nr, self._rule_pack = self._rule_pack_with_id(request.var("rule_pack"))

        else:
            # In links from multisite views the rule pack is not known.
            # We just know the rule id and need to find the pack ourselves.
            rule_id = request.get_ascii_input_mandatory("rule_id")

            rule_pack = None
            for nr, pack in enumerate(self._rule_packs):
                for rnr, rule in enumerate(pack["rules"]):
                    if rule_id == rule["id"]:
                        self._rule_pack_nr, rule_pack = nr, pack
                        request.set_var("edit", str(rnr))
                        request.set_var("rule_pack", pack["id"])
                        break

            if not rule_pack:
                raise MKUserError("rule_id", _("The rule you are trying to edit does not exist."))
            self._rule_pack = rule_pack

        self._edit_nr = request.get_integer_input_mandatory("edit", -1)  # missing -> new rule
        self._clone_nr = request.get_integer_input_mandatory(
            "clone", -1
        )  # Only needed in 'new' mode
        self._new = self._edit_nr < 0

        if self._new:
            self._rule = ec.Rule({})
            if self._clone_nr >= 0:
                self._rule.update(list(self._rule_pack["rules"])[self._clone_nr])
        else:
            try:
                self._rule = list(self._rule_pack["rules"])[self._edit_nr]
            except IndexError:
                raise MKUserError("edit", _("The rule you are trying to edit does not exist."))

    def title(self) -> str:
        if self._new:
            return _("Add rule")
        return _("Edit rule %s") % list(self._rule_pack["rules"])[self._edit_nr]["id"]

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        menu = make_simple_form_page_menu(
            _("Rule"), breadcrumb, form_name="rule", button_name="_save"
        )
        menu.dropdowns.insert(
            1,
            PageMenuDropdown(
                name="related",
                title=_("Related"),
                topics=[
                    PageMenuTopic(
                        title=_("Setup"),
                        entries=list(_page_menu_entries_related_ec(self.name())),
                    ),
                ],
            ),
        )
        return menu

    def action(self) -> ActionResult:
        if not transactions.check_transaction():
            return redirect(mode_url("mkeventd_rules", rule_pack=self._rule_pack["id"]))

        if not self._new:
            old_id = self._rule["id"]
        vs = self._valuespec()
        rule = vs.from_html_vars("rule")
        vs.validate_value(dict(rule), "rule")
        if not self._new and old_id != rule["id"]:
            raise MKUserError(
                "rule_p_id", _("It is not allowed to change the ID of an existing rule.")
            )
        if self._new:
            for pack in self._rule_packs:
                for r in pack["rules"]:
                    if r["id"] == rule["id"]:
                        raise MKUserError(
                            "rule_p_id",
                            _("A rule with this ID already exists in rule pack <b>%s</b>.")
                            % pack["title"],
                        )

        try:
            num_groups = re.compile(rule["match"]).groups
        except Exception:
            raise MKUserError("rule_p_match", _("Invalid regular expression"))
        if num_groups > 9:
            raise MKUserError(
                "rule_p_match",
                _(
                    "You matching text has too many regular expression subgroups. "
                    "Only nine are allowed."
                ),
            )

        if "count" in rule and "expect" in rule:
            raise MKUserError(
                "rule_p_expect_USE",
                _("You cannot use counting and expecting at the same time in the same rule."),
            )

        if "expect" in rule and "delay" in rule:
            raise MKUserError(
                "rule_p_expect_USE",
                _("You cannot use expecting and delay at the same time in the same rule, sorry."),
            )

        # Make sure that number of group replacements do not exceed number
        # of groups in regex of match
        num_repl = 9
        while num_repl > num_groups:
            repl = "\\%d" % num_repl
            for name, value in rule.items():
                if name.startswith("set_") and isinstance(value, str):
                    if repl in value:
                        raise MKUserError(
                            "rule_p_" + name,
                            _(
                                "You are using the replacement reference <tt>\\%d</tt>, "
                                "but your match text has only %d subgroups."
                            )
                            % (num_repl, num_groups),
                        )
            num_repl -= 1

        if edition(cmk.utils.paths.omd_root) is Edition.CME and "customer" in self._rule_pack:
            try:
                del rule["customer"]
            except KeyError:
                pass

        id_to_mkp = self._get_rule_pack_to_mkp_map()
        type_ = ec.RulePackType.type_of(self._rule_pack, id_to_mkp)
        if type_ == ec.RulePackType.unmodified_mkp:
            ec.override_rule_pack_proxy(self._rule_pack_nr, self._rule_packs)
            rules = list(self._rule_packs[self._rule_pack_nr]["rules"])
        else:
            rules = list(self._rule_pack["rules"])

        if self._new and self._clone_nr >= 0:
            rules[self._clone_nr : self._clone_nr] = [rule]
        elif self._new:
            rules[0:0] = [rule]
        else:
            rules[self._edit_nr] = rule

        self._rule_pack["rules"] = rules

        if type_ == ec.RulePackType.exported:
            _export_mkp_rule_pack(self._rule_pack)
        _save_mkeventd_rules(self._rule_packs)

        if self._new:
            _add_change_for_sites(
                action_name="new-rule",
                text=("Created new event correlation rule with id %s") % rule["id"],
                rule_or_rulepack=rule,
                config_domain=self._config_domain,
            )
        else:
            _add_change_for_sites(
                action_name="edit-rule",
                text=("Modified event correlation rule %s") % rule["id"],
                rule_or_rulepack=rule,
                config_domain=self._config_domain,
            )
            # Reset hit counters of this rule
            execute_command("RESETCOUNTERS", [rule["id"]], omd_site())
        return redirect(mode_url("mkeventd_rules", rule_pack=self._rule_pack["id"]))

    def page(self) -> None:
        self._verify_ec_enabled()
        with html.form_context("rule"):
            vs = self._valuespec()
            vs.render_input("rule", dict(self._rule))
            vs.set_focus("rule")
            html.hidden_fields()

    def _valuespec(self) -> Dictionary:
        return vs_mkeventd_rule(self._rule_pack.get("customer"))


class ModeEventConsoleStatus(ABCEventConsoleMode):
    @classmethod
    def name(cls) -> str:
        return "mkeventd_status"

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return []

    @classmethod
    def parent_mode(cls) -> type[WatoMode] | None:
        return ModeEventConsoleRulePacks

    def title(self) -> str:
        return _("Local server status")

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        return PageMenu(
            dropdowns=[
                PageMenuDropdown(
                    name="related",
                    title=_("Related"),
                    topics=[
                        PageMenuTopic(
                            title=_("Setup"),
                            entries=list(_page_menu_entries_related_ec(self.name())),
                        ),
                    ],
                ),
            ],
            breadcrumb=breadcrumb,
        )

    def action(self) -> ActionResult:
        if not user.may("mkeventd.switchmode"):
            return None

        if request.has_var("_switch_sync"):
            new_mode = "sync"
        else:
            new_mode = "takeover"
        execute_command("SWITCHMODE", [new_mode], omd_site())
        log_audit(
            action="mkeventd-switchmode",
            message="Switched replication slave mode to %s" % new_mode,
            user_id=user.id,
            use_git=active_config.wato_use_git,
        )
        flash(_("Switched to %s mode") % new_mode)
        return None

    def page(self) -> None:
        self._verify_ec_enabled()

        warning = _("The Event Console Daemon is currently not running. ")
        warning += _(
            "Please make sure that you have activated it with <tt>omd config set MKEVENTD on</tt> "
            "before starting this site."
        )

        if not daemon_running():
            html.show_warning(warning)
            return

        status = get_local_ec_status()
        if not status:
            html.show_warning(warning)
            return

        repl_mode = status["status_replication_slavemode"]
        html.h3(_("Current status of local Event Console"))
        html.open_ul()
        html.li(_("Event Daemon is running."))
        html.open_li()
        html.write_text_permissive("%s: " % _("Current replication mode"))
        html.open_b()
        html.write_text_permissive(
            {
                "sync": _("synchronize"),
                "takeover": _("Takeover!"),
            }.get(repl_mode, _("master / standalone"))
        )
        html.close_b()
        html.close_li()
        if repl_mode in ["sync", "takeover"]:
            html.open_li()
            html.write_text_permissive(
                _("Status of last synchronization: <b>%s</b>")
                % (status["status_replication_success"] and _("Success") or _("Failed!"))
            )
            html.close_li()
            last_sync = status["status_replication_last_sync"]
            if last_sync:
                html.li(_("Last successful sync %d seconds ago.") % (time.time() - last_sync))
            else:
                html.li(_("No successful synchronization so far."))

        html.close_ul()

        if user.may("mkeventd.switchmode"):
            with html.form_context(
                "switch",
                require_confirmation=RequireConfirmation(
                    html=_("Do you really want to switch the event daemon mode?")
                ),
            ):
                if repl_mode == "sync":
                    html.button("_switch_takeover", _("Switch to Takeover mode!"))
                elif repl_mode == "takeover":
                    html.button("_switch_sync", _("Switch back to sync mode!"))
                html.hidden_fields()


class ModeEventConsoleSettings(ABCEventConsoleMode, ABCGlobalSettingsMode):
    @classmethod
    def name(cls) -> str:
        return "mkeventd_config"

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return ["mkeventd.config"]

    @classmethod
    def parent_mode(cls) -> type[WatoMode] | None:
        return ModeEventConsoleRulePacks

    def __init__(self) -> None:
        super().__init__()

        self._default_values = self._config_domain.default_globals()
        self._current_settings = dict(load_configuration_settings())

    @staticmethod
    def _get_groups(show_all: bool) -> Iterable[ConfigVariableGroup]:
        return [
            g
            for g in sorted(
                config_variable_group_registry.values(), key=lambda grp: grp.sort_index()
            )
            if g
            in (
                ConfigVariableGroupEventConsoleGeneric,
                ConfigVariableGroupEventConsoleLogging,
                ConfigVariableGroupEventConsoleSNMP,
            )
        ]

    def title(self) -> str:
        if self._search:
            return html_escape(_("Event Console configuration matching '%s'") % self._search)
        return _("Event Console configuration")

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        menu = PageMenu(
            dropdowns=[
                PageMenuDropdown(
                    name="related",
                    title=_("Related"),
                    topics=[
                        PageMenuTopic(
                            title=_("Setup"),
                            entries=list(_page_menu_entries_related_ec(self.name())),
                        ),
                    ],
                ),
            ],
            breadcrumb=breadcrumb,
            inpage_search=PageMenuSearch(),
        )

        return menu

    # TODO: Consolidate with ModeEditGlobals.action()
    def action(self) -> ActionResult:
        varname = request.var("_varname")
        action = request.var("_action")
        if not varname:
            return None

        try:
            config_variable = config_variable_registry[varname]
        except KeyError:
            raise MKUserError("_varname", _("The requested global setting does not exist."))

        def_value = config_variable.valuespec().default_value()

        if not transactions.check_transaction():
            return None

        if varname in self._current_settings:
            self._current_settings[varname] = not self._current_settings[varname]
        else:
            self._current_settings[varname] = not def_value
        msg = _("Changed Configuration variable %s to %s.") % (
            varname,
            self._current_settings[varname] and _("on") or _("off"),
        )

        save_global_settings(self._current_settings)

        self._add_change(
            action_name="edit-configvar",
            text=msg,
        )

        if action == "_reset":
            flash(msg)
        return redirect(mode_url("mkeventd_config"))

    @property
    def edit_mode_name(self) -> str:
        return "mkeventd_edit_configvar"

    def page(self) -> None:
        self._verify_ec_enabled()
        self._show_configuration_variables()


ConfigVariableGroupEventConsoleGeneric = ConfigVariableGroup(
    title=_l("Event Console: Generic"),
    sort_index=18,
)


ConfigVariableGroupEventConsoleLogging = ConfigVariableGroup(
    title=_l("Event Console: Logging & diagnose"),
    sort_index=19,
)


ConfigVariableGroupEventConsoleSNMP = ConfigVariableGroup(
    title=_l("Event Console: SNMP traps"),
    sort_index=20,
)


class ModeEventConsoleEditGlobalSetting(ABCEditGlobalSettingMode):
    @classmethod
    def name(cls) -> str:
        return "mkeventd_edit_configvar"

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return ["mkeventd.config"]

    @classmethod
    def parent_mode(cls) -> type[WatoMode] | None:
        return ModeEventConsoleSettings

    def __init__(self) -> None:
        super().__init__()
        self._need_restart = None

    def title(self) -> str:
        return _("Event Console configuration")

    def _affected_sites(self) -> list[SiteId]:
        return _get_event_console_sync_sites()

    def _back_url(self) -> str:
        return ModeEventConsoleSettings.mode_url()


def _get_event_console_sync_sites() -> list[SiteId]:
    """Returns a list of site ids which gets the Event Console configuration replicated"""
    return [s[0] for s in get_event_console_site_choices()]


@dataclass
class MIBInfo:
    size: int
    name: str
    organization: str


class ModeEventConsoleMIBs(ABCEventConsoleMode):
    @classmethod
    def name(cls) -> str:
        return "mkeventd_mibs"

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return ["mkeventd.config"]

    @classmethod
    def parent_mode(cls) -> type[WatoMode] | None:
        return ModeEventConsoleRulePacks

    def title(self) -> str:
        return _("SNMP MIBs for trap translation")

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        return PageMenu(
            dropdowns=[
                PageMenuDropdown(
                    name="mibs",
                    title=_("MIBs"),
                    topics=[
                        PageMenuTopic(
                            title=_("Add MIBs"),
                            entries=[
                                PageMenuEntry(
                                    title=_("Add one or multiple MIBs"),
                                    icon_name="new",
                                    item=make_simple_link(
                                        makeuri_contextless(
                                            request,
                                            [("mode", "mkeventd_upload_mibs")],
                                        )
                                    ),
                                    is_shortcut=True,
                                    is_suggested=True,
                                ),
                            ],
                        ),
                        PageMenuTopic(
                            title=_("On selected MIBs"),
                            entries=[
                                PageMenuEntry(
                                    title=_("Delete MIBs"),
                                    shortcut_title=_("Delete selected MIBs"),
                                    icon_name="delete",
                                    item=make_confirmed_form_submit_link(
                                        form_name="bulk_delete_form",
                                        button_name="_bulk_delete_custom_mibs",
                                        title=_("Delete selected MIBs"),
                                    ),
                                    is_shortcut=True,
                                    is_suggested=True,
                                ),
                            ],
                        ),
                    ],
                ),
                PageMenuDropdown(
                    name="related",
                    title=_("Related"),
                    topics=[
                        PageMenuTopic(
                            title=_("Setup"),
                            entries=list(_page_menu_entries_related_ec(self.name())),
                        ),
                    ],
                ),
            ],
            breadcrumb=breadcrumb,
        )

    def action(self) -> ActionResult:
        check_csrf_token()

        if not transactions.check_transaction():
            return redirect(self.mode_url())

        if filename := request.var("_delete"):
            if info := self._load_snmp_mibs(mib_upload_dir()).get(filename):
                self._delete_mib(filename, info.name)
        elif request.var("_bulk_delete_custom_mibs"):
            self._bulk_delete_custom_mibs_after_confirm()

        return redirect(self.mode_url())

    def _bulk_delete_custom_mibs_after_confirm(self) -> None:
        custom_mibs = self._load_snmp_mibs(mib_upload_dir())
        selected_custom_mibs: list[str] = []
        for varname, _value in request.itervars(prefix="_c_mib_"):
            if html.get_checkbox(varname):
                filename = varname.split("_c_mib_")[-1]
                if filename in custom_mibs:
                    selected_custom_mibs.append(filename)

        for filename in selected_custom_mibs:
            self._delete_mib(filename, custom_mibs[filename].name)

    def _delete_mib(self, filename: str, mib_name: str) -> None:
        self._add_change(
            action_name="delete-mib",
            text=_("Deleted MIB %s") % filename,
        )
        pyc_suffix = f".cpython-{sys.version_info.major}{sys.version_info.minor}.pyc"
        for path in {
            _compiled_mibs_dir() / p
            for f in (Path(filename), Path(mib_name))
            for p in (
                f.with_suffix(".py"),
                ("__pycache__" / f).with_suffix(pyc_suffix),
            )
        } | {mib_upload_dir() / filename}:
            path.unlink(missing_ok=True)

    def page(self) -> None:
        self._verify_ec_enabled()
        for mib_path, title in mib_dirs():
            is_custom_dir = mib_path == mib_upload_dir()
            if is_custom_dir:
                with html.form_context("bulk_delete_form", method="POST"):
                    self._show_mib_table(mib_path, title)
                    html.hidden_fields()
                    html.end_form()
            else:
                self._show_mib_table(mib_path, title)

    def _show_mib_table(self, path: Path, title: str) -> None:
        is_custom_dir = path == mib_upload_dir()

        with table_element("mibs_%s" % path, title, searchable=False) as table:
            for filename, mib in sorted(self._load_snmp_mibs(path).items()):
                table.row()

                if is_custom_dir:
                    table.cell(
                        html.render_input(
                            "_toggle_group",
                            type_="button",
                            class_="checkgroup",
                            onclick="cmk.selection.toggle_all_rows();",
                            value="X",
                        )
                    )
                    html.checkbox("_c_mib_%s" % filename, deflt=False)

                table.cell(_("Actions"), css=["buttons"])
                if is_custom_dir:
                    delete_url = make_confirm_delete_link(
                        url=make_action_link([("mode", "mkeventd_mibs"), ("_delete", filename)]),
                        title=_("Delete MIB file"),
                        message=_("Filename: %s") % str(filename),
                        suffix=mib.name,
                    )
                    html.icon_button(delete_url, _("Delete this MIB"), "delete")

                table.cell(_("Filename"), filename)
                table.cell(_("MIB"), mib.name)
                table.cell(_("Organization"), mib.organization)
                table.cell(_("Size"), cmk.utils.render.fmt_bytes(mib.size), css=["number"])

    def _load_snmp_mibs(self, directory: Path) -> Mapping[str, MIBInfo]:
        return {
            path.name: self._parse_snmp_mib_header(path)
            for path in directory.glob("*")
            if not path.is_dir() and not path.name.startswith(".")
        }

    def _parse_snmp_mib_header(self, path: Path) -> MIBInfo:
        # read up to first "OBJECT IDENTIFIER" declaration
        head = ""
        with path.open() as f:
            for line in f:
                if line.startswith("--"):
                    continue
                if "OBJECT IDENTIFIER" in line:
                    break  # seems the header is finished
                head += line
        # now try to extract some relevant information from the header
        return MIBInfo(
            size=path.stat().st_size,
            organization=(
                matches.group(1)
                if (matches := re.search('ORGANIZATION[^"]+"([^"]+)"', head, re.M))
                else ""
            ),
            name=(
                matches.group(1)
                if (matches := re.search(r"^\s*([A-Z0-9][A-Z0-9-]+)\s", head, re.I | re.M))
                else ""
            ),
        )


class ModeEventConsoleUploadMIBs(ABCEventConsoleMode):
    @classmethod
    def name(cls) -> str:
        return "mkeventd_upload_mibs"

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return ["mkeventd.config"]

    @classmethod
    def parent_mode(cls) -> type[WatoMode] | None:
        return ModeEventConsoleMIBs

    def title(self) -> str:
        return _("Upload SNMP MIBs")

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        menu = make_simple_form_page_menu(
            _("MIBs"),
            breadcrumb,
            form_name="upload_form",
            button_name="_save",
            save_title=_("Upload"),
        )
        menu.dropdowns.insert(
            1,
            PageMenuDropdown(
                name="related",
                title=_("Related"),
                topics=[
                    PageMenuTopic(
                        title=_("Setup"),
                        entries=list(_page_menu_entries_related_ec(self.name())),
                    ),
                ],
            ),
        )
        return menu

    def action(self) -> ActionResult:
        check_csrf_token()

        if not request.uploaded_file("_upload_mib"):
            return None
        filename, mimetype, content = request.uploaded_file("_upload_mib")
        if filename:
            try:
                flash(self._upload_mib(filename, mimetype, content, debug=active_config.debug))
                return None
            except Exception as e:
                if active_config.debug:
                    raise
                raise MKUserError("_upload_mib", "%s" % e)
        return None

    def _upload_mib(self, filename: str, mimetype: str, content: bytes, *, debug: bool) -> str:
        self._validate_mib_file_name(filename)

        if self._is_zipfile(io.BytesIO(content)):
            msg = self._process_uploaded_zip_file(filename, content, debug=debug)
        else:
            if (
                mimetype == "application/tar"
                or filename.lower().endswith(".gz")
                or filename.lower().endswith(".tgz")
            ):
                raise Exception(_("Sorry, uploading TAR/GZ files is not yet implemented."))

            msg = self._process_uploaded_mib_file(filename, content, debug=debug)

        return msg

    # Used zipfile.is_zipfile(io.BytesIO(content)) before, but this only
    # possible with python 2.7. zipfile is only supporting checking of files by
    # their path.
    def _is_zipfile(self, fo: io.BytesIO) -> bool:
        try:
            with zipfile.ZipFile(fo) as _opened_file:
                pass
            return True
        except zipfile.BadZipfile:
            return False

    def _process_uploaded_zip_file(self, filename: str, content: bytes, *, debug: bool) -> str:
        with zipfile.ZipFile(io.BytesIO(content)) as zip_obj:
            messages = []
            success, fail = 0, 0
            for entry in zip_obj.infolist():
                mib_file_name = entry.filename
                try:
                    if mib_file_name[-1] == "/":
                        continue  # silently skip directories
                    self._validate_mib_file_name(mib_file_name)
                    with zip_obj.open(mib_file_name) as mib_obj:
                        messages.append(
                            self._process_uploaded_mib_file(
                                mib_file_name, mib_obj.read(), debug=debug
                            )
                        )
                    success += 1
                except Exception as e:
                    messages.append(_("Skipped %s: %s") % (mib_file_name, e))
                    fail += 1

        return "<br>\n".join(
            messages
        ) + "<br><br>\nProcessed %d MIB files, skipped %d MIB files" % (success, fail)

    def _process_uploaded_mib_file(self, filename: str, content: bytes, *, debug: bool) -> str:
        if "." in filename:
            mibname = filename.split(".")[0]
        else:
            mibname = filename

        msg = self._validate_and_compile_mib(mibname.upper(), content, debug=debug)
        mib_upload_dir().mkdir(parents=True, exist_ok=True)
        with (mib_upload_dir() / filename).open("wb") as f:
            f.write(content)
        self._add_change(
            action_name="uploaded-mib",
            text=_("MIB %s: %s") % (filename, msg),
        )
        return msg

    def _validate_mib_file_name(self, filename: str) -> None:
        if filename.startswith(".") or "/" in filename:
            raise Exception(_("Invalid filename"))

    def _validate_and_compile_mib(self, mibname: str, content_bytes: bytes, *, debug: bool) -> str:
        compiled_mibs_dir = _compiled_mibs_dir()
        compiled_mibs_dir.mkdir(mode=0o770, exist_ok=True)

        # This object manages the compilation of the uploaded SNMP mib
        # but also resolving dependencies and compiling dependents
        compiler = MibCompiler(
            SmiV1CompatParser(), PySnmpCodeGen(), PyFileWriter(compiled_mibs_dir)
        )

        # FIXME: This is a temporary local fix that should be removed once
        # handling of file contents uses a uniformly encoded representation
        try:
            content = content_bytes.decode("utf-8")
        except UnicodeDecodeError:
            content = content_bytes.decode("latin-1")

        # Provides the just uploaded MIB module
        compiler.addSources(CallbackReader(lambda m, c: m == mibname and c or "", content))

        # Directories containing ASN1 MIB files which may be used for
        # dependency resolution
        compiler.addSources(*[FileReader(str(path)) for path, _title in mib_dirs()])

        # check for already compiled MIBs
        compiler.addSearchers(PyFileSearcher(compiled_mibs_dir))

        # and also check PySNMP shipped compiled MIBs
        compiler.addSearchers(*[PyPackageSearcher(x) for x in PySnmpCodeGen.defaultMibPackages])

        # never recompile MIBs with MACROs
        compiler.addSearchers(StubSearcher(*PySnmpCodeGen.baseMibs))

        try:
            if not content or content.isspace():
                raise Exception(_("The file is empty"))

            results = compiler.compile(mibname, ignoreErrors=True, genTexts=True)

            errors = []
            for name, state_obj in sorted(results.items()):
                if mibname == name and state_obj == "failed":
                    raise Exception(_("Failed to compile your module: %s") % state_obj.error)

                if state_obj == "missing":
                    errors.append(_("%s - Dependency missing") % name)
                elif state_obj == "failed":
                    errors.append(_("%s - Failed to compile (%s)") % (name, state_obj.error))

            msg = _("MIB file %s uploaded.") % mibname
            if errors:
                msg += "<br>" + _("But there were errors:") + "<br>"
                msg += "<br>\n".join(errors)
            return msg

        except PySmiError as e:
            if debug:
                raise e
            raise Exception(_("Failed to process your MIB file (%s): %s") % (mibname, e))

    def page(self) -> None:
        self._verify_ec_enabled()
        html.h3(_("Upload MIB file"))
        html.write_text_permissive(
            _(
                "Use this form to upload MIB files for translating incoming SNMP traps. "
                "You can upload single MIB files with the extension <tt>.mib</tt> or "
                "<tt>.txt</tt>, but you can also upload multiple MIB files at once by "
                "packing them into a <tt>.zip</tt> file. Only files in the root directory "
                "of the zip file will be processed.<br><br>"
            )
        )

        with html.form_context("upload_form", method="POST"):
            forms.header(_("Upload MIB file"))

            forms.section(_("Select file"), is_required=True)
            html.upload_file("_upload_mib")
            forms.end()

            html.hidden_fields()


def _page_menu_entries_related_ec(mode_name: str) -> Iterator[PageMenuEntry]:
    if mode_name != "mkeventd_rule_packs":
        yield PageMenuEntry(
            title=_("Rule packs"),
            icon_name="event_console",
            item=make_simple_link(
                makeuri_contextless(
                    request,
                    [("mode", "mkeventd_rule_packs")],
                )
            ),
        )

    if user.may("mkeventd.config") and user.may("wato.rulesets"):
        yield _page_menu_entry_rulesets()

    if mode_name != "mkeventd_status":
        yield _page_menu_entry_status()

    if mode_name != "mkeventd_config" and user.may("mkeventd.config"):
        yield _page_menu_entry_settings(is_suggested=False)

    if mode_name != "mkeventd_mibs":
        yield _page_menu_entry_snmp_mibs()


def _page_menu_entry_rulesets() -> PageMenuEntry:
    return PageMenuEntry(
        title=_("Rules"),
        icon_name="rulesets",
        item=make_simple_link(
            makeuri_contextless(request, [("mode", "rulesets"), ("group", "eventconsole")])
        ),
    )


def _page_menu_entry_status() -> PageMenuEntry:
    return PageMenuEntry(
        title=_("Status"),
        icon_name="event console_status",
        item=make_simple_link(makeuri_contextless(request, [("mode", "mkeventd_status")])),
    )


def _page_menu_entry_settings(is_suggested: bool) -> PageMenuEntry:
    return PageMenuEntry(
        title=_("Settings"),
        icon_name="configuration",
        is_shortcut=is_suggested,
        is_suggested=is_suggested,
        item=make_simple_link(makeuri_contextless(request, [("mode", "mkeventd_config")])),
    )


def _page_menu_entry_snmp_mibs() -> PageMenuEntry:
    return PageMenuEntry(
        title=_("SNMP MIBs"),
        icon_name="snmpmib",
        item=make_simple_link(makeuri_contextless(request, [("mode", "mkeventd_mibs")])),
    )


def _rule_edit_url(rule_pack_id: str, rule_nr: int) -> str:
    return makeuri_contextless(
        request,
        [
            ("mode", "mkeventd_edit_rule"),
            ("rule_pack", rule_pack_id),
            ("edit", rule_nr),
        ],
        filename="wato.py",
    )


# .
#   .--Permissions---------------------------------------------------------.
#   |        ____                     _         _                          |
#   |       |  _ \ ___ _ __ _ __ ___ (_)___ ___(_) ___  _ __  ___          |
#   |       | |_) / _ \ '__| '_ ` _ \| / __/ __| |/ _ \| '_ \/ __|         |
#   |       |  __/  __/ |  | | | | | | \__ \__ \ | (_) | | | \__ \         |
#   |       |_|   \___|_|  |_| |_| |_|_|___/___/_|\___/|_| |_|___/         |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Declaration of Event Console specific permissions for Multisite      |
#   '----------------------------------------------------------------------'

ConfigureECPermission = Permission(
    section=PERMISSION_SECTION_EVENT_CONSOLE,
    name="config",
    title=_l("Configuration of Event Console"),
    description=_l("This permission allows to configure the global settings of the event console."),
    defaults=["admin"],
)


ConfigureECRulesPermission = Permission(
    section=PERMISSION_SECTION_EVENT_CONSOLE,
    name="edit",
    title=_l("Configuration of event rules"),
    description=_l(
        "This permission allows the creation, modification and deletion of event correlation rules."
    ),
    defaults=["admin"],
)


ActivateECPermission = Permission(
    section=PERMISSION_SECTION_EVENT_CONSOLE,
    name="activate",
    title=_l("Activate changes for event console"),
    description=_l(
        "Activation of changes for the event console (rule modification, "
        "global settings) is done separately from the monitoring configuration "
        "and needs this permission."
    ),
    defaults=["admin"],
)

SwitchSlaveReplicationPermission = Permission(
    section=PERMISSION_SECTION_EVENT_CONSOLE,
    name="switchmode",
    title=_l("Switch slave replication mode"),
    description=_l(
        "This permission is only useful if the Event Console is "
        "setup as a replication slave. It allows a manual switch "
        "between sync and takeover mode."
    ),
    defaults=["admin"],
)


class MainModuleEventConsole(ABCMainModule):
    @property
    def mode_or_url(self) -> str:
        return "mkeventd_rule_packs"

    @property
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicEvents

    @property
    def title(self) -> str:
        return _("Event Console")

    @property
    def icon(self) -> Icon:
        return "event_console"

    @property
    def permission(self) -> None | str:
        return "mkeventd.edit"

    @property
    def description(self) -> str:
        return _("Manage event classification and correlation rules for the Event Console")

    @property
    def sort_index(self) -> int:
        return 20

    @property
    def enabled(self) -> bool:
        return active_config.mkeventd_enabled

    @property
    def is_show_more(self) -> bool:
        return True


# .
#   .--Settings & Rules----------------------------------------------------.
#   | ____       _   _   _                       ____        _             |
#   |/ ___|  ___| |_| |_(_)_ __   __ _ ___   _  |  _ \ _   _| | ___  ___   |
#   |\___ \ / _ \ __| __| | '_ \ / _` / __|_| |_| |_) | | | | |/ _ \/ __|  |
#   | ___) |  __/ |_| |_| | | | | (_| \__ \_   _|  _ <| |_| | |  __/\__ \  |
#   ||____/ \___|\__|\__|_|_| |_|\__, |___/ |_| |_| \_\\__,_|_|\___||___/  |
#   |                            |___/                                     |
#   +----------------------------------------------------------------------+
#   | Declarations for global settings of EC parameters and of a rule for  |
#   | active checks that query the EC status of a host.                    |
#   '----------------------------------------------------------------------'


ConfigVariableEventConsole = ConfigVariable(
    group=ConfigVariableGroupSiteManagement,
    domain=ConfigDomainOMD,
    ident="site_mkeventd",
    valuespec=lambda: Optional(
        valuespec=ListChoice(
            choices=[
                ("SNMPTRAP", _("Receive SNMP traps (UDP/162)")),
                ("SYSLOG", _("Receive Syslog messages (UDP/514)")),
                ("SYSLOG_TCP", _("Receive Syslog messages (TCP/514)")),
            ],
            title=_("Listen for incoming messages via"),
            empty_text=_("Locally enabled"),
        ),
        title=_("Event Console"),
        help=_(
            "This option enables the Event Console - The event processing and "
            "classification daemon of Checkmk. You can also configure whether "
            "or not the Event Console shal listen for incoming SNMP traps or "
            "syslog messages. Please note that only a single Checkmk site per "
            "Checkmk server can listen for such messages."
        ),
        label=_("Event Console enabled"),
        none_label=_("Event Console disabled"),
        indent=False,
    ),
)

ConfigVariableEventConsoleRemoteStatus = ConfigVariable(
    group=ConfigVariableGroupEventConsoleGeneric,
    domain=ConfigDomainEventConsole,
    ident="remote_status",
    valuespec=lambda: Optional(
        valuespec=Tuple(
            elements=[
                Integer(
                    title=_("Port number:"),
                    help=_(
                        "If you are running the Event Console as a non-root (such as in an OMD site) "
                        "please choose port number greater than 1024."
                    ),
                    minvalue=1,
                    maxvalue=65535,
                    default_value=6558,
                ),
                Checkbox(
                    title=_("Security"),
                    label=_("allow execution of commands and actions via TCP"),
                    help=_(
                        "Without this option the access is limited to querying the current "
                        "and historic event status."
                    ),
                    default_value=False,
                    true_label=_("allow commands"),
                    false_label=_("no commands"),
                ),
                Optional(
                    valuespec=ListOfStrings(
                        help=_(
                            "The access to the event status via TCP will only be allowed from "
                            "this source IP addresses or an IPv4/IPv6 network "
                            "in the notation X.X.X.X/Bits or X:X:.../Bits for IPv6"
                        ),
                        valuespec=IPNetwork(ip_class=None, size="max"),
                        orientation="horizontal",
                        allow_empty=False,
                    ),
                    label=_("Restrict access to the following source IPv4/IPv6 addresses/networks"),
                    none_label=_("access unrestricted"),
                ),
            ],
        ),
        title=_("Access to event status via TCP"),
        help=_(
            'In Multisite setups if you want <a href="%s">event status checks</a> for hosts that '
            "live on a remote site you need to activate remote access to the event status socket "
            "via TCP. This allows to query the current event status via TCP. If you do not restrict "
            "this to queries also event actions are possible from remote. This feature is not used "
            "by the event status checks nor by Multisite so we propose not allowing commands via TCP."
        )
        % "wato.py?mode=edit_ruleset&varname=active_checks%3Amkevents",
        none_label=_("no access via TCP"),
    ),
)

ConfigVariableEventConsoleReplication = ConfigVariable(
    group=ConfigVariableGroupEventConsoleGeneric,
    domain=ConfigDomainEventConsole,
    ident="replication",
    valuespec=lambda: Optional(
        valuespec=Dictionary(
            optional_keys=["takeover", "fallback", "disabled", "logging"],
            elements=[
                (
                    "master",
                    Tuple(
                        title=_("Master Event Console"),
                        help=_(
                            "Specify the host name or IP address of the master Event Console that "
                            "you want to replicate from. The port number must be the same as set "
                            "in the master in <i>Access to event status via TCP</i>."
                        ),
                        elements=[
                            TextInput(
                                title=_("Host name/IP address of Master Event Console:"),
                                allow_empty=False,
                            ),
                            Integer(
                                title=_("TCP Port number of status socket:"),
                                minvalue=1,
                                maxvalue=65535,
                                default_value=6558,
                            ),
                        ],
                    ),
                ),
                (
                    "interval",
                    Integer(
                        title=_("Replication interval"),
                        help=_("The replication will be triggered each this number of seconds"),
                        label=_("Do a replication every"),
                        unit=_("sec"),
                        minvalue=1,
                        default_value=10,
                    ),
                ),
                (
                    "connect_timeout",
                    Integer(
                        title=_("Connect timeout"),
                        help=_("TCP connect timeout for connecting to the master"),
                        label=_("Try bringing up TCP connection for"),
                        unit=_("sec"),
                        minvalue=1,
                        default_value=10,
                    ),
                ),
                (
                    "takeover",
                    Integer(
                        title=_("Automatic takeover"),
                        help=_(
                            "If you enable this option then the remote site will automatically "
                            "takeover and enable event processing if the central site is for "
                            "the configured number of seconds unreachable."
                        ),
                        label=_("Takeover after a master downtime of"),
                        unit=_("sec"),
                        minvalue=1,
                        default_value=30,
                    ),
                ),
                (
                    "fallback",
                    Integer(
                        title=_("Automatic fallback"),
                        help=_(
                            "If you enable this option then the slave will automatically "
                            "fallback from takeover mode to slavemode if the master is "
                            "reachable again within the selected number of seconds since "
                            "the previous unreachability (not since the takeover)"
                        ),
                        label=_("Fallback if central comes back within"),
                        unit=_("sec"),
                        minvalue=1,
                        default_value=60,
                    ),
                ),
                (
                    "disabled",
                    FixedValue(
                        value=True,
                        totext=_("Replication is disabled"),
                        title=_("Currently disable replication"),
                        help=_(
                            "This allows you to disable the replication without losing "
                            "your settings. If you check this box, then no replication "
                            "will be done and the Event Console will act as its own master."
                        ),
                    ),
                ),
                (
                    "logging",
                    FixedValue(
                        value=True,
                        title=_("Log replication events"),
                        totext=_("logging is enabled"),
                        help=_(
                            "Enabling this option will create detailed log entries for all "
                            "replication activities of the remote site. If disabled only problems "
                            "will be logged."
                        ),
                    ),
                ),
            ],
        ),
        title=_("Enable replication from a master"),
    ),
)

ConfigVariableEventConsoleRetentionInterval = ConfigVariable(
    group=ConfigVariableGroupEventConsoleGeneric,
    domain=ConfigDomainEventConsole,
    ident="retention_interval",
    valuespec=lambda: Age(
        title=_("State retention interval"),
        help=_(
            "In this interval the event daemon will save its state "
            "to disk, so that you won't lose your current event "
            "state in case of a crash."
        ),
    ),
)

ConfigVariableEventConsoleHousekeepingInterval = ConfigVariable(
    group=ConfigVariableGroupEventConsoleGeneric,
    domain=ConfigDomainEventConsole,
    ident="housekeeping_interval",
    valuespec=lambda: Age(
        title=_("Housekeeping interval"),
        help=_(
            "From time to time the eventd checks for messages that are expected to "
            "be seen on a regular base, for events that time out and yet for "
            "count periods that elapse. Here you can specify the regular interval "
            "for that job."
        ),
    ),
)

ConfigVariableEventConsoleSqliteHousekeepingInterval = ConfigVariable(
    group=ConfigVariableGroupEventConsoleGeneric,
    domain=ConfigDomainEventConsole,
    ident="sqlite_housekeeping_interval",
    valuespec=lambda: Age(
        title=_("Event Console housekeeping interval"),
        help=_(
            "From time to time the Event Console history requires maintenance. "
            "For example, it needs to clean up old data, optimize the storage and "
            "defragment the data. Here you can specify the regular interval "
            "for that job."
        ),
    ),
)

ConfigVariableEventConsoleSqliteFreelistSize = ConfigVariable(
    group=ConfigVariableGroupEventConsoleGeneric,
    domain=ConfigDomainEventConsole,
    ident="sqlite_freelist_size",
    valuespec=lambda: Filesize(
        title=_("Event Console history fragmentation limit size"),
        help=_(
            "Event Console History can become fragmented over time. So if the total "
            "size of deleted entries reaches this number the Event Console history will be cleaned up."
        ),
        minvalue=1 * 1024 * 1024,
        maxvalue=100 * 1024 * 1024,
    ),
)

ConfigVariableEventConsoleStatisticsInterval = ConfigVariable(
    group=ConfigVariableGroupEventConsoleGeneric,
    domain=ConfigDomainEventConsole,
    ident="statistics_interval",
    valuespec=lambda: Age(
        title=_("Statistics interval"),
        help=_(
            "The event daemon keeps statistics about the rate of messages, events "
            "rule hits, and other stuff. These values are updated in the interval "
            "configured here and are available in the sidebar snap-in <i>Event Console "
            "performance</i>"
        ),
    ),
)

ConfigVariableEventConsoleLogMessages = ConfigVariable(
    group=ConfigVariableGroupEventConsoleGeneric,
    domain=ConfigDomainEventConsole,
    ident="log_messages",
    valuespec=lambda: Checkbox(
        title=_("Syslog-like message logging"),
        label=_("Log all messages into syslog-like logfiles"),
        help=_(
            "When this option is enabled, then <b>every</b> incoming message is being "
            "logged into the directory <tt>messages</tt> in the Event Consoles state "
            "directory. The logfile rotation is analog to that of the history logfiles. "
            "Please note that if you have lots of incoming messages then these "
            "files can get very large."
        ),
    ),
)

ConfigVariableEventConsoleRuleOptimizer = ConfigVariable(
    group=ConfigVariableGroupEventConsoleGeneric,
    domain=ConfigDomainEventConsole,
    ident="rule_optimizer",
    valuespec=lambda: Checkbox(
        title=_("Optimize rule execution"),
        label=_("enable optimized rule execution"),
        help=_("This option turns on a faster algorithm for matching events to rules. "),
    ),
)

ConfigVariableEventConsoleActions = ConfigVariable(
    group=ConfigVariableGroupEventConsoleGeneric,
    domain=ConfigDomainEventConsole,
    ident="actions",
    valuespec=lambda: ActionList(
        Foldable(
            valuespec=Dictionary(
                title=_("Action"),
                optional_keys=False,
                elements=[
                    (
                        "id",
                        ID(
                            title=_("Action ID"),
                            help=_(
                                "A unique ID of this action that is used as an internal "
                                "reference in the configuration. Changing the ID is not "
                                "possible if still rules refer to this ID."
                            ),
                            allow_empty=False,
                            size=12,
                        ),
                    ),
                    (
                        "title",
                        TextInput(
                            title=_("Title"),
                            help=_("A descriptive title of this action."),
                            allow_empty=False,
                            size=64,
                        ),
                    ),
                    (
                        "disabled",
                        Checkbox(
                            title=_("Disable"),
                            label=_("Currently disable execution of this action"),
                        ),
                    ),
                    (
                        "hidden",
                        Checkbox(
                            title=_("Hide from Status GUI"),
                            label=_("Do not offer this action as a command on open events"),
                            help=_(
                                "If you enabled this option, then this action will not "
                                "be available as an interactive user command. It is usable "
                                "as an ad-hoc action when a rule fires, nevertheless."
                            ),
                        ),
                    ),
                    (
                        "action",
                        CascadingDropdown(
                            title=_("Type of Action"),
                            help=_("Choose the type of action to perform"),
                            choices=[
                                (
                                    "email",
                                    _("Send email"),
                                    Dictionary(
                                        optional_keys=False,
                                        elements=[
                                            (
                                                "to",
                                                TextInput(
                                                    title=_("Recipient email address"),
                                                    allow_empty=False,
                                                ),
                                            ),
                                            (
                                                "subject",
                                                TextInput(
                                                    title=_("Subject"),
                                                    allow_empty=False,
                                                    size=64,
                                                ),
                                            ),
                                            (
                                                "body",
                                                TextAreaUnicode(
                                                    title=_("Body"),
                                                    help=_macros_help,
                                                    cols=64,
                                                    rows=10,
                                                ),
                                            ),
                                        ],
                                    ),
                                ),
                                (
                                    "script",
                                    _("Execute Shell Script"),
                                    Dictionary(
                                        optional_keys=False,
                                        elements=[
                                            (
                                                "script",
                                                TextAreaUnicode(
                                                    title=_("Script body"),
                                                    help=_vars_help,
                                                    cols=64,
                                                    rows=10,
                                                ),
                                            ),
                                        ],
                                    ),
                                ),
                            ],
                        ),
                    ),
                ],
            ),
            title_function=lambda value: not value["id"]
            and _("New Action")
            or (value["id"] + " - " + value["title"]),
        ),
        title=_("Actions (emails & scripts)"),
        help=_(
            "Configure that possible actions that can be performed when a "
            "rule triggers and also manually by a user."
        ),
        totext=_("%d actions"),
        add_label=_("Add new action"),
    ),
    # TODO: Why? Can we drop this?
    allow_reset=False,
)

ConfigVariableEventConsoleArchiveOrphans = ConfigVariable(
    group=ConfigVariableGroupEventConsoleGeneric,
    domain=ConfigDomainEventConsole,
    ident="archive_orphans",
    valuespec=lambda: Checkbox(
        title=_("Force message archiving"),
        label=_("Archive messages that do not match any rule"),
        help=_(
            "When this option is enabled then messages that do not match "
            "a rule will be archived into the event history anyway (Messages "
            "that do match a rule will be archived always, as long as they are not "
            "explicitly dropped are being aggregated by counting.)"
        ),
    ),
)

ConfigVariableHostnameTranslation = ConfigVariable(
    group=ConfigVariableGroupEventConsoleGeneric,
    domain=ConfigDomainEventConsole,
    ident="hostname_translation",
    valuespec=lambda: HostnameTranslation(
        title=_("Host name translation for incoming messages"),
        help=_(
            "When the Event Console receives a message than the host name "
            "that is contained in that message will be translated using "
            "this configuration. This can be used for unifying host names "
            "from message with those of actively monitored hosts. Note: this translation "
            "is happening before any rule is being applied."
        ),
    ),
)


def vs_ec_event_limit_actions(notify_txt: str) -> DropdownChoice:
    return DropdownChoice(
        title=_("Action"),
        help=_("Choose the action the Event Console should trigger once the limit is reached."),
        choices=[
            ("stop", _("Stop creating new events")),
            ("stop_overflow", _("Stop creating new events, create overflow event")),
            (
                "stop_overflow_notify",
                "{}, {}".format(_("Stop creating new events, create overflow event"), notify_txt),
            ),
            ("delete_oldest", _("Delete oldest event, create new event")),
        ],
        default_value="stop_overflow_notify",
    )


def vs_ec_rule_limit() -> Dictionary:
    return Dictionary(
        title=_("Rule limit"),
        help=_(
            "You can limit the number of current events created by a single "
            "rule here. This is meant to "
            "prevent you from too generous rules creating a lot of events.<br>"
            "Once the limit is reached, the Event Console will stop the rule "
            "creating new current events until the number of current "
            "events has been reduced to be below this limit. In the "
            "moment the limit is reached, the Event Console will notify "
            "the configured contacts of the rule or create a notification "
            "with empty contact information."
        ),
        elements=[
            (
                "limit",
                Integer(
                    title=_("Limit"),
                    minvalue=1,
                    default_value=1000,
                    unit=_("current events"),
                ),
            ),
            ("action", vs_ec_event_limit_actions("notify contacts in rule or fallback contacts")),
        ],
        optional_keys=[],
    )


def vs_ec_host_limit(title: str) -> Dictionary:
    return Dictionary(
        title=title,
        help=_(
            "You can limit the number of current events created by a single "
            "host here. This is meant to "
            "prevent you from message storms created by one device.<br>"
            "Once the limit is reached, the Event Console will block "
            "all future incoming messages sent by this host until the "
            "number of current "
            "events has been reduced to be below this limit. In the "
            "moment the limit is reached, the Event Console will notify "
            "the configured contacts of the host."
        ),
        elements=[
            (
                "limit",
                Integer(
                    title=_("Limit"),
                    minvalue=1,
                    default_value=1000,
                    unit=_("current events"),
                ),
            ),
            ("action", vs_ec_event_limit_actions("notify contacts of the host")),
        ],
        optional_keys=[],
    )


ConfigVariableEventConsoleEventLimit = ConfigVariable(
    group=ConfigVariableGroupEventConsoleGeneric,
    domain=ConfigDomainEventConsole,
    ident="event_limit",
    valuespec=lambda: Dictionary(
        title=_("Limit amount of current events"),
        help=_(
            "This option helps you to protect the Event Console from resource "
            "problems which may occur in case of too many current events at the "
            "same time."
        ),
        elements=[
            ("by_host", vs_ec_host_limit(title=_("Host limit"))),
            ("by_rule", vs_ec_rule_limit()),
            (
                "overall",
                Dictionary(
                    title=_("Overall current events"),
                    help=_(
                        "To protect you against a continuously growing list of current "
                        "events created by different hosts or rules, you can configure "
                        "this overall limit of current events. All currently current events "
                        "are counted and once the limit is reached, no further events "
                        "will be currented which means that new incoming messages will be "
                        "dropped. In the moment the limit is reached, the Event Console "
                        "will create a notification with empty contact information."
                    ),
                    elements=[
                        (
                            "limit",
                            Integer(
                                title=_("Limit"),
                                minvalue=1,
                                default_value=10000,
                                unit=_("current events"),
                            ),
                        ),
                        ("action", vs_ec_event_limit_actions("notify all fallback contacts")),
                    ],
                    optional_keys=[],
                ),
            ),
        ],
        optional_keys=[],
    ),
)

ConfigVariableEventConsoleHistoryRotation = ConfigVariable(
    group=ConfigVariableGroupEventConsoleGeneric,
    domain=ConfigDomainEventConsole,
    ident="history_rotation",
    valuespec=lambda: DropdownChoice(
        title=_("Event history logfile rotation"),
        help=_("Specify at which time period a new file for the event history will be created."),
        choices=[("daily", _("daily")), ("weekly", _("weekly"))],
    ),
)

ConfigVariableEventConsoleHistoryLifetime = ConfigVariable(
    group=ConfigVariableGroupEventConsoleGeneric,
    domain=ConfigDomainEventConsole,
    ident="history_lifetime",
    valuespec=lambda: Integer(
        title=_("Event history lifetime"),
        help=_("After this number of days old logfile of event history will be deleted."),
        unit=_("days"),
        minvalue=1,
    ),
)

ConfigVariableEventConsoleSocketQueueLength = ConfigVariable(
    group=ConfigVariableGroupEventConsoleGeneric,
    domain=ConfigDomainEventConsole,
    ident="socket_queue_len",
    valuespec=lambda: Integer(
        title=_("Max. number of pending connections to the status socket"),
        help=_(
            "When the Multisite GUI or the active check check_mkevents connects "
            "to the socket of the event daemon in order to retrieve information "
            "about current and historic events then its connection request might "
            "be queued before being processed. This setting defines the number of unaccepted "
            "connections to be queued before refusing new connections."
        ),
        minvalue=1,
        label="max.",
        unit=_("pending connections"),
    ),
)

ConfigVariableEventConsoleEventSocketQueueLength = ConfigVariable(
    group=ConfigVariableGroupEventConsoleGeneric,
    domain=ConfigDomainEventConsole,
    ident="eventsocket_queue_len",
    valuespec=lambda: Integer(
        title=_("Max. number of pending connections to the event socket"),
        help=_(
            "The event socket is an alternative way for sending events "
            "to the Event Console. It is used by the Checkmk logwatch check "
            "when forwarding log messages to the Event Console. "
            "This setting defines the number of unaccepted "
            "connections to be queued before refusing new connections."
        ),
        minvalue=1,
        label="max.",
        unit=_("pending connections"),
    ),
)

ConfigVariableEventConsoleTranslateSNMPTraps = ConfigVariable(
    group=ConfigVariableGroupEventConsoleSNMP,
    domain=ConfigDomainEventConsole,
    ident="translate_snmptraps",
    valuespec=lambda: CascadingDropdown(
        title=_("Translate SNMP traps"),
        help=_(
            "When this option is enabled all available SNMP MIB files will be used "
            "to translate the incoming SNMP traps. Information which can not be "
            "translated, e.g. because a MIB is missing, are written untouched to "
            "the event message."
        ),
        choices=[
            (False, _("Do not translate SNMP traps")),
            (
                True,
                _("Translate SNMP traps using the available MIBs"),
                Dictionary(
                    elements=[
                        (
                            "add_description",
                            FixedValue(
                                value=True,
                                title=_("Add OID descriptions"),
                                totext=_("Append descriptions of OIDs to message texts"),
                            ),
                        ),
                    ],
                ),
            ),
        ],
    ),
)

ConfigVariableEventConsoleSNMPCredentials = ConfigVariable(
    group=ConfigVariableGroupEventConsoleSNMP,
    domain=ConfigDomainEventConsole,
    ident="snmp_credentials",
    valuespec=lambda: ListOf(
        valuespec=Dictionary(
            elements=[
                (
                    "description",
                    TextInput(
                        title=_("Description"),
                    ),
                ),
                ("credentials", SNMPCredentials(for_ec=True)),
                (
                    "engine_ids",
                    ListOfStrings(
                        valuespec=TextInput(
                            size=24,
                            minlen=2,
                            allow_empty=False,
                            regex="^[A-Fa-f0-9]*$",
                            regex_error=_(
                                "The engine IDs have to be configured as hex strings "
                                "like <tt>8000000001020304</tt>."
                            ),
                        ),
                        title=_("Engine IDs (only needed for SNMPv3)"),
                        help=_(
                            "Each SNMPv3 device has it's own engine ID. This is normally "
                            "automatically generated, but can also be configured manually "
                            "for some devices. As the engine ID is used for the encryption "
                            "of SNMPv3 traps sent by the devices, Checkmk needs to know "
                            "the engine ID to be able to decrypt the SNMP traps.<br>"
                            "The engine IDs have to be configured as hex strings like "
                            "<tt>8000000001020304</tt>."
                        ),
                        allow_empty=False,
                    ),
                ),
            ],
            # NOTE: For SNMPv3, this should not be empty, otherwise users will be confused...
            optional_keys=["engine_ids"],
        ),
        title=_("Credentials for processing SNMP traps"),
        help=_(
            "When you want to process SNMP traps with the Event Console it is "
            "necessary to configure the credentials to decrypt the incoming traps."
        ),
        text_if_empty=_("SNMP traps not configured"),
    ),
)

ConfigVariableEventConsoleDebugRules = ConfigVariable(
    group=ConfigVariableGroupEventConsoleLogging,
    domain=ConfigDomainEventConsole,
    ident="debug_rules",
    valuespec=lambda: Checkbox(
        title=_("Debug rule execution"),
        label=_("enable extensive rule logging"),
        help=_(
            "This option turns on logging the execution of rules. For each message received "
            "the execution details of each rule are logged. This creates an immense "
            "volume of logging and should never be used in productive operation."
        ),
        default_value=False,
    ),
)

ConfigVariableEventConsoleLogLevel = ConfigVariable(
    group=ConfigVariableGroupEventConsoleLogging,
    domain=ConfigDomainEventConsole,
    ident="log_level",
    valuespec=lambda: Dictionary(
        title=_("Log level"),
        help=_(
            "You can configure the Event Console to log more details about it's actions. "
            "These information are logged into the file <tt>%s</tt>"
        )
        % site_neutral_path(cmk.utils.paths.log_dir / "mkeventd.log"),
        elements=_ec_log_level_elements(),
        optional_keys=[],
    ),
)


def _ec_log_level_elements() -> list[tuple[str, DropdownChoice]]:
    elements = []

    for component, title, help_txt in [
        (
            "cmk.mkeventd",
            _("General messages"),
            _("Log level for all log messages that are not in one of the categories below"),
        ),
        (
            "cmk.mkeventd.EventServer",
            _("Processing of incoming events"),
            _("Log level for the processing of all incoming events"),
        ),
        (
            "cmk.mkeventd.EventStatus",
            _("Event database"),
            _("Log level for managing already created events"),
        ),
        (
            "cmk.mkeventd.StatusServer",
            _("Status queries"),
            _("Log level for handling of incoming queries to the status socket"),
        ),
        (
            "cmk.mkeventd.lock",
            _("Locking"),
            _(
                "Log level for the locking mechanics. Setting this to debug will enable "
                "log entries for each lock/unlock action."
            ),
        ),
        (
            "cmk.mkeventd.EventServer.snmp",
            _("SNMP trap processing"),
            _(
                "Log level for the SNMP trap processing mechanics. Setting this to debug will enable "
                "detailed log entries for each received SNMP trap."
            ),
        ),
    ]:
        elements.append(
            (
                component,
                LogLevelChoice(
                    title=title,
                    help=help_txt,
                ),
            )
        )
    return elements


ConfigVariableEventLogRuleHits = ConfigVariable(
    group=ConfigVariableGroupEventConsoleLogging,
    domain=ConfigDomainEventConsole,
    ident="log_rulehits",
    valuespec=lambda: Checkbox(
        title=_("Log rule hits"),
        label=_("Log hits for rules in log of Event Console"),
        help=_(
            "If you enable this option then every time an event matches a rule "
            "(by normal hit, cancelling, counting or dropping) a log entry will be written "
            "into the log file of the Event Console. Please be aware that this might lead to "
            "a large number of log entries. "
        ),
    ),
)

# TODO: Isn't this variable deprecated since 1.5? Investigate and drop/mark as deprecated
ConfigVariableEventConsoleConnectTimeout = ConfigVariable(
    group=ConfigVariableGroupUserInterface,
    domain=ConfigDomainGUI,
    ident="mkeventd_connect_timeout",
    valuespec=lambda: Integer(
        title=_("Connect timeout to status socket of Event Console"),
        help=_(
            "When the Multisite GUI connects the socket of the event daemon "
            "in order to retrieve information about current and historic events "
            "then this timeout will be applied."
        ),
        minvalue=1,
        maxvalue=120,
        unit="sec",
    ),
)

ConfigVariableEventConsolePrettyPrintRules = ConfigVariable(
    group=ConfigVariableGroupWATO,
    domain=ConfigDomainGUI,
    ident="mkeventd_pprint_rules",
    valuespec=lambda: Checkbox(
        title=_("Pretty-Print rules in config file of Event Console"),
        label=_("enable pretty-printing of rules"),
        help=_(
            "When the Setup module of the Event Console saves rules to the file "
            "<tt>mkeventd.d/wato/rules.mk</tt> it usually prints the Python "
            "representation of the rules-list into one single line by using the "
            "native Python code generator. Enabling this option switches to <tt>pprint</tt>, "
            "which nicely indents everything. While this is a bit slower for large "
            "rulesets it makes debugging and manual editing simpler."
        ),
    ),
)

ConfigVariableEventConsoleNotifyContactgroup = ConfigVariable(
    group=ConfigVariableGroupNotifications,
    domain=ConfigDomainGUI,
    ident="mkeventd_notify_contactgroup",
    valuespec=lambda: ContactGroupSelection(
        title=_("Send notifications to Event Console"),
        no_selection=_("(don't send notifications to Event Console)"),
        label=_("send notifications of contactgroup:"),
        help=_(
            "If you select a contact group here, then all notifications of "
            "hosts and services in that contact group will be sent to the "
            "event console. <b>Note</b>: you still need to create a rule "
            "matching those messages in order to have events created. <b>Note (2)</b>: "
            "If you are using the Checkmk Micro Core then this setting is deprecated. "
            "Please use the notification plug-in <i>Forward Notification to Event Console</i> instead."
        ),
    ),
    need_restart=True,
)

ConfigVariableEventConsoleNotifyRemoteHost = ConfigVariable(
    group=ConfigVariableGroupNotifications,
    domain=ConfigDomainGUI,
    ident="mkeventd_notify_remotehost",
    valuespec=lambda: Optional(
        valuespec=TextInput(
            title=_("Host running Event Console"),
        ),
        title=_("Send notifications to remote Event Console"),
        help=_(
            "This will send the notification to a Checkmk Event Console on a remote host "
            "by using syslog. <b>Note</b>: this setting will only be applied if no Event "
            "Console is running locally in this site! That way you can use the same global "
            "settings on your central and decentralized system and makes distributed Setup "
            "easier. Please also make sure that <b>Send notifications to Event Console</b> "
            "is enabled."
        ),
        label=_("Send to remote Event Console via syslog"),
        none_label=_("Do not send to remote host"),
    ),
    need_restart=True,
)


ConfigVariableEventConsoleNotifyFacility = ConfigVariable(
    group=ConfigVariableGroupNotifications,
    domain=ConfigDomainGUI,
    ident="mkeventd_notify_facility",
    valuespec=lambda: DropdownChoice(
        title=_("Syslog facility for Event Console notifications"),
        help=_(
            "When sending notifications from the monitoring system to the event console "
            "the following syslog facility will be set for these messages. Choosing "
            "a unique facility makes creation of rules easier."
        ),
        choices=syslog_facilities,
    ),
    need_restart=True,
)

ConfigVariableEventConsoleServiceLevels = ConfigVariable(
    group=ConfigVariableGroupNotifications,
    domain=ConfigDomainGUI,
    ident="mkeventd_service_levels",
    valuespec=lambda: ListOf(
        valuespec=Tuple(
            elements=[
                Integer(
                    title=_("internal ID"),
                    minvalue=0,
                    maxvalue=100,
                ),
                TextInput(
                    title=_("Name / Description"),
                    allow_empty=False,
                ),
            ],
            orientation="horizontal",
        ),
        title=_("Service levels"),
        help=_(
            "Here you can configure the list of possible service levels for hosts, services and "
            "events. A service level can be assigned to a host or service by configuration. "
            "The event console can configure each created event to have a specific service level. "
            "Internally the level is represented as an integer number. Note: a higher number represents "
            "a higher service level. This is important when filtering views "
            "by the service level.<p>You can also attach service levels to hosts "
            "and services in the monitoring. These levels will then be sent to the "
            "Event Console when you forward notifications to it and will override the "
            "setting of the matching rule."
        ),
        allow_empty=False,
    ),
    need_restart=False,
)


class MainModuleEventConsoleRules(ABCMainModule):
    @property
    def enabled(self) -> bool:
        return False

    @property
    def mode_or_url(self) -> str:
        return makeuri_contextless_rulespec_group(request, "eventconsole")

    @property
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicEvents

    @property
    def title(self) -> str:
        return _("Event Console rules")

    @property
    def icon(self) -> Icon:
        return {"icon": "event_console", "emblem": "settings"}

    @property
    def permission(self) -> None | str:
        return "rulesets"

    @property
    def description(self) -> str:
        return _("Host and service rules related to the Event Console")

    @property
    def sort_index(self) -> int:
        return 40

    @property
    def is_show_more(self) -> bool:
        return True

    @classmethod
    def additional_breadcrumb_items(cls) -> Iterable[BreadcrumbItem]:
        yield BreadcrumbItem(
            title="Event Console rule packs",
            url=makeuri_contextless(
                request,
                [("mode", "mkeventd_rule_packs")],
                filename="wato.py",
            ),
        )


class RulespecGroupEventConsole(RulespecGroup):
    @property
    def name(self) -> str:
        return "eventconsole"

    @property
    def title(self) -> str:
        return _("Event Console rules")

    @property
    def help(self) -> str:
        return _("Host and service rules related to the Event Console")


def _valuespec_extra_host_conf__ec_event_limit() -> Transform:
    return Transform(
        valuespec=vs_ec_host_limit(title=_("Host event limit")),
        to_valuespec=lambda x: dict([("limit", int(x.split(":")[0])), ("action", x.split(":")[1])]),
        from_valuespec=lambda x: "%d:%s" % (x["limit"], x["action"]),
    )


ECEventLimitRulespec = HostRulespec(
    group=RulespecGroupEventConsole,
    name=RuleGroup.ExtraHostConf("_ec_event_limit"),
    valuespec=_valuespec_extra_host_conf__ec_event_limit,
)


def _valuespec_active_checks_mkevents() -> Dictionary:
    return Dictionary(
        title=_("Check event state in Event Console"),
        help=_(
            "This check is part of the Checkmk Event Console and monitors "
            "whether there are any open events for a particular host. "
            "The overall state of the service generated by the check reflects "
            "the most critical status of any open event for that host."
        ),
        elements=[
            (
                "hostspec",
                Alternative(
                    title=_("Host specification"),
                    elements=[
                        ListChoice(
                            title=_("Match the hosts with..."),
                            choices=[
                                ("$HOSTNAME$", _("Host name")),
                                ("$HOSTADDRESS$", _("IP address")),
                                ("$HOSTALIAS$", _("Alias")),
                            ],
                        ),
                        TextInput(allow_empty=False, title="Specify host explicitly"),
                    ],
                    default_value=["$HOSTNAME$", "$HOSTADDRESS$"],
                    help=_(
                        "When querying the event status, you can match events to a particular host "
                        "using the host name, the IP address, or the host alias. This is due to the "
                        "fact that various event sources (e.g. syslog, snmptrapd) may refer to the "
                        "same host using different specification methods. Alternatively, you can "
                        "specify an explicit host for which to show events."
                    ),
                ),
            ),
            (
                "item",
                TextInput(
                    title=_("Item (used in service name)"),
                    help=_(
                        "If you enter an item name here, this will be used as "
                        'part of the service name after the prefix "Events ". '
                        "The prefix plus the configured item must result in a unique "
                        "service name per host. If you leave this empty either the "
                        'string provided in "Application" is used as item or the service '
                        'gets no item when the "Application" field is also not configured.'
                    ),
                    allow_empty=False,
                ),
            ),
            (
                "application",
                RegExp(
                    title=_("Application (regular expression)"),
                    help=_(
                        "If you enter an application name here then only "
                        "events for that application name are counted. You enter "
                        "a regular expression here that must match a <b>part</b> "
                        "of the application name. Use anchors <tt>^</tt> and <tt>$</tt> "
                        "if you need a complete match."
                    ),
                    allow_empty=False,
                    mode=RegExp.infix,
                    case_sensitive=False,
                ),
            ),
            (
                "ignore_acknowledged",
                FixedValue(
                    value=True,
                    title=_("Ignore acknowledged events"),
                    help=_(
                        "If you check this box then only open events are honored when "
                        "determining the event state. Acknowledged events are displayed "
                        "(i.e. their count) but not taken into account."
                    ),
                    totext=_("acknowledged events will not be honored"),
                ),
            ),
            (
                "remote",
                Alternative(
                    title=_("Access to the Event Console"),
                    elements=[
                        FixedValue(
                            value=None,
                            title=_("Connect to the local Event Console"),
                            totext=_("local connect"),
                        ),
                        Tuple(
                            elements=[
                                TextInput(
                                    title=_("Host name/IP address of Event Console:"),
                                    allow_empty=False,
                                ),
                                Integer(
                                    title=_("TCP Port number:"),
                                    minvalue=1,
                                    maxvalue=65535,
                                    default_value=6558,
                                ),
                            ],
                            title=_("Access via TCP"),
                            help=_(
                                "In a distributed setup where the Event Console is not running in the same "
                                "site as the host is monitored you need to access the remote Event Console "
                                "via TCP. Please make sure that this is activated in the global settings of "
                                "the event console. The default port number is 6558."
                            ),
                        ),
                        TextInput(
                            title=_("Access via UNIX socket"),
                            allow_empty=False,
                            size=64,
                        ),
                    ],
                    default_value=None,
                ),
            ),
            (
                "show_last_log",
                DropdownChoice(
                    title=_("Show last log message"),
                    help=_(
                        "Display the last log message that lead to the worst state (i.e., the "
                        "current state of the service) and choose the display location. "
                        "Please note that log messages may contain sensitive information, "
                        "so displaying them on a service can lead to a security risk."
                    ),
                    choices=[
                        ("summary", _("In service summary")),
                        ("details", _("In service details")),
                        ("no", _("Don't show")),
                    ],
                    default_value="details",
                ),
            ),
        ],
        optional_keys=["application", "remote", "ignore_acknowledged", "item"],
        ignored_keys=["less_verbose"],  # is deprecated
    )


ActiveCheckMKEventsRulespec = HostRulespec(
    group=RulespecGroupEventConsole,
    match_type="all",
    name=RuleGroup.ActiveChecks("mkevents"),
    valuespec=lambda: Migrate(
        valuespec=_valuespec_active_checks_mkevents(),
        migrate=lambda value: {"show_last_log": "summary"} | value,
    ),
)


def _sl_help() -> str:
    return (
        _(
            "A service level is a number that describes the business impact of a host or "
            "service. This level can be used in rules for notifications, as a filter in "
            "views or as a criteria in rules for the Event Console. A higher service level "
            "is assumed to be more business critical. This ruleset allows to assign service "
            "levels to hosts and/or services. Note: if you assign a service level to "
            "a host with the ruleset <i>Service level of hosts</i>, then this level is "
            "inherited to all services that do <b>not</b> have explicitly assigned a service "
            "with the ruleset <i>Service level of services</i>. Assigning no service level "
            "is equal to defining a level of 0.<br><br>The list of available service "
            "levels is configured via a <a href='%s'>global option.</a>"
        )
        % "wato.py?varname=mkeventd_service_levels&mode=edit_configvar"
    )


def _valuespec_extra_host_conf__ec_sl() -> DropdownChoice:
    return DropdownChoice(
        title=_("Service level of hosts"),
        help=_sl_help(),
        choices=service_levels,
    )


ExtraHostConfECSLRulespec = HostRulespec(
    group=RulespecGroupHostsMonitoringRulesVarious,
    name=RuleGroup.ExtraHostConf("_ec_sl"),
    valuespec=_valuespec_extra_host_conf__ec_sl,
)


def _valuespec_extra_service_conf__ec_sl() -> DropdownChoice:
    return DropdownChoice(
        title=_("Service level of services"),
        help=_sl_help()
        + _(
            " Note: if no service level is configured for a service "
            "then that of the host will be used instead (if configured)."
        ),
        choices=service_levels,
    )


ExtraServiceConfECSLRulespec = ServiceRulespec(
    group=RulespecGroupMonitoringConfigurationVarious,
    item_type="service",
    name=RuleGroup.ExtraServiceConf("_ec_sl"),
    valuespec=_valuespec_extra_service_conf__ec_sl,
)


def _vs_contact(title: str) -> TextInput:
    return TextInput(
        title=title,
        help=_(
            "This rule set is useful if you send your monitoring notifications "
            "into the Event Console. The contact information that is set by this rule "
            "will be put into the resulting event in the Event Console. "
            "This does not transport contact objects or contact groups, but is a free "
            "comment field."
        )
        + _(
            " Note: if no contact information is configured for a service "
            "then that of the host will be used instead (if configured)."
        ),
        size=80,
        regex=r"^[^;'$|]*$",
        regex_error=_(
            "The contact information must not contain one of the characters "
            "<tt>;</tt> <tt>'</tt> <tt>|</tt> or <tt>$</tt>"
        ),
    )


def _valuespec_extra_host_conf__ec_contact() -> TextInput:
    return _vs_contact(_("Host contact information"))


ExtraHostConfECContact = HostRulespec(
    group=RulespecGroupEventConsole,
    name=RuleGroup.ExtraHostConf("_ec_contact"),
    valuespec=_valuespec_extra_host_conf__ec_contact,
)


def _valuespec_extra_service_conf__ec_contact() -> TextInput:
    return _vs_contact(title=_("Service contact information"))


ExtraServiceConfECContact = ServiceRulespec(
    group=RulespecGroupEventConsole,
    item_type="service",
    name=RuleGroup.ExtraServiceConf("_ec_contact"),
    valuespec=_valuespec_extra_service_conf__ec_contact,
)


# .
#   .--Notifications-------------------------------------------------------.
#   |       _   _       _   _  __ _           _   _                        |
#   |      | \ | | ___ | |_(_)/ _(_) ___ __ _| |_(_) ___  _ __  ___        |
#   |      |  \| |/ _ \| __| | |_| |/ __/ _` | __| |/ _ \| '_ \/ __|       |
#   |      | |\  | (_) | |_| |  _| | (_| (_| | |_| | (_) | | | \__ \       |
#   |      |_| \_|\___/ \__|_|_| |_|\___\__,_|\__|_|\___/|_| |_|___/       |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Stuff for sending monitoring notifications into the event console.   |
#   '----------------------------------------------------------------------'
def mkeventd_update_notification_configuration(
    hosts: Mapping[HostName, CollectedHostAttributes],
) -> None:
    contactgroup = active_config.mkeventd_notify_contactgroup
    remote_console = active_config.mkeventd_notify_remotehost

    if not remote_console:
        remote_console = ""

    path = cmk.utils.paths.nagios_conf_dir / "mkeventd_notifications.cfg"
    if not contactgroup and path.exists():
        path.unlink()
    elif contactgroup:
        store.save_text_to_file(
            path,
            """# Created by Checkmk Event Console
# This configuration will send notifications about hosts and
# services in the contact group '%(group)s' to the Event Console.

define contact {
    contact_name                   mkeventd
    alias                          "Notifications for Checkmk Event Console"
    contactgroups                  %(group)s
    host_notification_commands     mkeventd-notify-host
    service_notification_commands  mkeventd-notify-service
    host_notification_options      d,u,r
    service_notification_options   c,w,u,r
    host_notification_period       24X7
    service_notification_period    24X7
    email                          none
}

define command {
    command_name                   mkeventd-notify-host
    command_line                   mkevent -n %(facility)s '%(remote)s' $HOSTSTATEID$ '$HOSTNAME$' '' '$HOSTOUTPUT$' '$_HOSTEC_SL$' '$_HOSTEC_CONTACT$'
}

define command {
    command_name                   mkeventd-notify-service
    command_line                   mkevent -n %(facility)s '%(remote)s' $SERVICESTATEID$ '$HOSTNAME$' '$SERVICEDESC$' '$SERVICEOUTPUT$' '$_SERVICEEC_SL$' '$_SERVICEEC_CONTACT$' '$_HOSTEC_SL$' '$_HOSTEC_CONTACT$'
}
"""
            % {
                "group": contactgroup,
                "facility": active_config.mkeventd_notify_facility,
                "remote": remote_console,
            },
        )


#   .--Setup search--------------------------------------------------------.
#   |     ____       _                                         _           |
#   |    / ___|  ___| |_ _   _ _ __    ___  ___  __ _ _ __ ___| |__        |
#   |    \___ \ / _ \ __| | | | '_ \  / __|/ _ \/ _` | '__/ __| '_ \       |
#   |     ___) |  __/ |_| |_| | |_) | \__ \  __/ (_| | | | (__| | | |      |
#   |    |____/ \___|\__|\__,_| .__/  |___/\___|\__,_|_|  \___|_| |_|      |
#   |                         |_|                                          |
#   +----------------------------------------------------------------------+
#   | Searching of EC in setup search                                      |
#   '----------------------------------------------------------------------'
# .


class MatchItemGeneratorECRulePacksAndRules(ABCMatchItemGenerator):
    def __init__(
        self,
        name: str,
        rule_pack_loader: Callable[[], Iterable[ec.ECRulePack]],
    ) -> None:
        super().__init__(name)
        self._rule_pack_loader = rule_pack_loader

    def generate_match_items(self) -> MatchItems:
        for rule_pack in self._iter_rulepacks():
            rule_pack_title = rule_pack["title"]
            rule_pack_id = rule_pack["id"]
            yield MatchItem(
                title=f"{rule_pack_id} ({rule_pack_title})",
                topic=_("Event Console rule packs"),
                url=ModeEventConsoleRules.mode_url(rule_pack=rule_pack["id"]),
                match_texts=[rule_pack_title, rule_pack_id],
            )
            yield from (
                self._rule_to_match_item(rule, _rule_edit_url(rule_pack_id, nr))
                for nr, rule in enumerate(rule_pack["rules"])
            )

    def _iter_rulepacks(self) -> Iterable[ec.ECRulePackSpec]:
        yield from (
            opt_rule_pack
            for opt_rule_pack in (
                self._rule_pack_from_rule_pack_or_mkp(rule_pack_or_mkp)
                for rule_pack_or_mkp in self._rule_pack_loader()
            )
            if opt_rule_pack
        )

    def _rule_pack_from_rule_pack_or_mkp(
        self, rule_pack_or_mkp: ec.ECRulePack
    ) -> ec.ECRulePackSpec | None:
        if isinstance(rule_pack_or_mkp, ec.MkpRulePackProxy):
            return self._unpack_mkp_rule_pack(rule_pack_or_mkp.rule_pack)
        return rule_pack_or_mkp

    def _unpack_mkp_rule_pack(
        self, mkp_rule_pack: ec.ECRulePack | None
    ) -> ec.ECRulePackSpec | None:
        if isinstance(mkp_rule_pack, ec.MkpRulePackProxy):
            return self._unpack_mkp_rule_pack(mkp_rule_pack.rule_pack)
        return mkp_rule_pack

    @staticmethod
    def _rule_to_match_item(rule: ec.Rule, url: str) -> MatchItem:
        id_ = rule["id"]
        description = rule.get("description")
        return MatchItem(
            title=id_ + ((description and f" ({description})") or ""),
            topic=_("Event Console rules"),
            url=url,
            match_texts=[id_] + [value for value in [description, rule.get("comment")] if value],
        )

    @staticmethod
    def is_affected_by_change(change_action_name: str) -> bool:
        # rule packs: new-rule-pack, edit-rule-pack, ...
        # rules within rule packs: new-rule, edit-rule, ...
        return "rule" in change_action_name

    @property
    def is_localization_dependent(self) -> bool:
        return False


MatchItemEventConsole = MatchItemGeneratorECRulePacksAndRules(
    "event_console",
    ec.load_rule_packs,
)
MatchItemEventConsoleSettings = MatchItemGeneratorSettings(
    "event_console_settings",
    _("Event Console settings"),
    ModeEventConsoleSettings,
)


def _socket_path() -> Path:
    return cmk.utils.paths.omd_root / "tmp/run/mkeventd/status"


def daemon_running() -> bool:
    return _socket_path().exists()


def send_event(event: ec.Event) -> str:
    syslog_message_str = repr(
        ec.SyslogMessage(
            facility=event["facility"],
            severity=event["priority"],
            timestamp=time.time(),
            host_name=event["host"],
            application=event["application"],
            text=event["text"],
            ip_address=event["ipaddress"],
            service_level=event["sl"],
        )
    )

    execute_command("CREATE", [syslog_message_str], site=event["site"])

    return syslog_message_str


def get_local_ec_status() -> dict[str, Any] | None:
    response = LocalConnection().query("GET eventconsolestatus")
    if len(response) == 1:
        return None  # In case the EC is not running, there may be some
    return dict(zip(response[0], response[1]))


def replication_mode() -> str:
    try:
        status = get_local_ec_status()
        if not status:
            return "stopped"
        return status["status_replication_slavemode"]
    except MKLivestatusSocketError:
        return "stopped"


# Only use this for master/slave replication. For status queries use livestatus
def query_ec_directly(query: bytes) -> dict[str, Any]:
    response_text = b""
    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(active_config.mkeventd_connect_timeout)
        sock.connect(str(_socket_path()))
        sock.sendall(query)
        sock.shutdown(socket.SHUT_WR)

        while True:
            chunk = sock.recv(8192)
            response_text += chunk
            if not chunk:
                break

        return ast.literal_eval(response_text.decode())
    except SyntaxError:
        raise MKGeneralException(
            _("Invalid response from event daemon: <pre>%s</pre>") % response_text
        )

    except Exception as e:
        raise MKGeneralException(
            _("Cannot connect to event daemon via %s: %s") % (_socket_path(), e)
        )


def form_spec() -> DictionaryExtended:
    # TODO register CSE specific version
    return DictionaryExtended(
        title=Title("Forward to EC parameters"),
        elements={
            "facility": DictElement(
                parameter_form=SingleChoiceExtended(
                    title=Title("Syslog facility to use"),
                    help_text=Help(
                        "The notifications will be converted into syslog messages with "
                        "the facility that you choose here. In the Event Console you can "
                        "later create a rule matching this facility."
                    ),
                    elements=[
                        SingleChoiceElementExtended(
                            title=Title("%s") % title,
                            name=ident,
                        )
                        for ident, title in syslog_facilities
                    ],
                ),
            ),
            "remote": DictElement(
                parameter_form=String(
                    title=Title("IP address of remote Event Console"),
                    help_text=Help(
                        "If you set this parameter then the notifications will be sent via "
                        "syslog/UDP (port 514) to a remote Event Console or syslog server."
                    ),
                    custom_validate=[
                        HostAddressValidator(
                            allow_host_name=False,
                            allow_empty=False,
                        )
                    ],
                )
            ),
        },
    )
