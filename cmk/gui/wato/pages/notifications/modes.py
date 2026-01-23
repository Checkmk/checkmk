#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Modes for managing notification configuration"""

# mypy: disable-error-code="comparison-overlap"

# mypy: disable-error-code="redundant-expr"
# mypy: disable-error-code="unreachable"

# mypy: disable-error-code="possibly-undefined"
# mypy: disable-error-code="type-arg"

import abc
import enum
import json
import re
import time
from collections.abc import Collection, Generator, Iterator, Mapping, Sequence
from copy import deepcopy
from dataclasses import asdict
from datetime import datetime, timedelta
from typing import Any, cast, Literal, NamedTuple, NotRequired, overload, TypedDict

from livestatus import LivestatusResponse, SiteConfiguration, SiteConfigurations

import cmk.gui.view_utils
import cmk.gui.watolib.audit_log as _audit_log
import cmk.gui.watolib.changes as _changes
from cmk.ccc import store
from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.site import SiteId
from cmk.ccc.user import UserId
from cmk.ccc.version import Edition, edition
from cmk.gui import forms, permissions, sites, userdb
from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.config import active_config, Config
from cmk.gui.default_name import unique_clone_increment_suggestion
from cmk.gui.exceptions import MKUserError
from cmk.gui.form_specs import (
    DEFAULT_VALUE,
    parse_data_from_field_id,
    RawDiskData,
    RawFrontendData,
    render_form_spec,
)
from cmk.gui.form_specs.unstable.legacy_converter import (
    TransformDataForLegacyFormatOrRecomposeFunction,
)
from cmk.gui.htmllib.foldable_container import foldable_container
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.htmllib.html import html
from cmk.gui.http import Request, request
from cmk.gui.i18n import _, ungettext
from cmk.gui.logged_in import user
from cmk.gui.main_menu import main_menu_registry
from cmk.gui.main_menu_types import MainMenu
from cmk.gui.mkeventd import syslog_facilities, syslog_priorities
from cmk.gui.page_menu import (
    make_display_options_dropdown,
    make_simple_form_page_menu,
    make_simple_link,
    PageMenu,
    PageMenuDropdown,
    PageMenuEntry,
    PageMenuEntryCEEOnly,
    PageMenuSearch,
    PageMenuTopic,
)
from cmk.gui.quick_setup.v0_unstable._registry import quick_setup_registry
from cmk.gui.search import (
    ABCMatchItemGenerator,
    MatchItem,
    MatchItemGeneratorRegistry,
    MatchItems,
)
from cmk.gui.site_config import (
    distributed_setup_remote_sites,
    has_distributed_setup_remote_sites,
    site_is_local,
)
from cmk.gui.table import Table, table_element
from cmk.gui.type_defs import (
    ActionResult,
    HTTPVariables,
    IconNames,
    PermissionName,
    StaticIcon,
    Users,
)
from cmk.gui.user_async_replication import user_profile_async_replication_dialog
from cmk.gui.userdb import get_user_attributes, UserAttribute
from cmk.gui.utils.autocompleter_config import ContextAutocompleterConfig
from cmk.gui.utils.csrf_token import check_csrf_token
from cmk.gui.utils.flashed_messages import flash
from cmk.gui.utils.html import HTML
from cmk.gui.utils.notifications import (
    get_disabled_notifications_infos,
    get_failed_notification_count,
    get_total_sent_notifications,
    OPTIMIZE_NOTIFICATIONS_ENTRIES,
    SUPPORT_NOTIFICATIONS_ENTRIES,
)
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.utils.rule_specs.legacy_converter import convert_to_legacy_valuespec
from cmk.gui.utils.time import timezone_utc_offset_str
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.utils.urls import (
    DocReference,
    make_confirm_delete_link,
    makeactionuri,
    makeuri,
    makeuri_contextless,
)
from cmk.gui.utils.user_errors import user_errors
from cmk.gui.valuespec import (
    Age,
    Alternative,
    CascadingDropdown,
    CascadingDropdownChoiceValue,
    Checkbox,
    DatePicker,
    Dictionary,
    DictionaryEntry,
    DropdownChoice,
    EmailAddress,
    FixedValue,
    Foldable,
    HostState,
    ID,
    Integer,
    ListChoice,
    ListOf,
    ListOfStrings,
    MigrateNotUpdated,
    MonitoredHostname,
    MonitoredServiceDescription,
    MonitoringState,
    RegExp,
    rule_option_elements,
    TextInput,
    TimePicker,
    Tuple,
    UUID,
    ValueSpec,
)
from cmk.gui.wato._group_selection import ContactGroupSelection
from cmk.gui.wato.pages.events import ABCEventsMode
from cmk.gui.wato.pages.user_profile.page_menu import page_menu_dropdown_user_related
from cmk.gui.wato.pages.users import ModeEditUser
from cmk.gui.watolib.automation_commands import AutomationCommand, AutomationCommandRegistry
from cmk.gui.watolib.automations import (
    do_remote_automation,
    make_automation_config,
)
from cmk.gui.watolib.check_mk_automations import (
    notification_analyse,
    notification_get_bulks,
    notification_replay,
    notification_test,
)
from cmk.gui.watolib.global_settings import load_configuration_settings
from cmk.gui.watolib.hosts_and_folders import folder_preserving_link, make_action_link
from cmk.gui.watolib.mode import mode_url, ModeRegistry, redirect, WatoMode
from cmk.gui.watolib.notification_parameter import notification_parameter_registry
from cmk.gui.watolib.notifications import (
    load_user_notification_rules,
    NotificationParameterConfigFile,
    NotificationRuleConfigFile,
)
from cmk.gui.watolib.rulesets import AllRulesets
from cmk.gui.watolib.sample_config import (
    get_default_notification_rule,
    new_notification_parameter_id,
    new_notification_rule_id,
)
from cmk.gui.watolib.timeperiods import TimeperiodSelection
from cmk.gui.watolib.user_scripts import load_notification_scripts
from cmk.gui.watolib.users import notification_script_choices
from cmk.rulesets.v1.rule_specs import NotificationParameters
from cmk.shared_typing.notifications import (
    NotificationCoreStats,
    NotificationCoreStatsI18n,
    NotificationFallbackWarning,
    NotificationFallbackWarningI18n,
    NotificationParametersOverview,
    Notifications,
    NotificationStats,
    NotificationStatsI18n,
    Rule,
    RuleSection,
    RuleTopic,
)
from cmk.utils import paths
from cmk.utils.automation_config import LocalAutomationConfig
from cmk.utils.labels import Labels
from cmk.utils.notify import NotificationContext
from cmk.utils.notify_types import (
    EventRule,
    get_rules_related_to_parameter,
    is_always_bulk,
    NotificationParameterGeneralInfos,
    NotificationParameterID,
    NotificationParameterItem,
    NotificationParameterSpec,
    NotificationParameterSpecs,
    NotificationPluginNameStr,
    NotifyAnalysisInfo,
    NotifyPluginInfo,
)
from cmk.utils.statename import host_state_name, service_state_name


def register(
    mode_registry: ModeRegistry,
    match_item_generator_registry: MatchItemGeneratorRegistry,
    automation_command_registry: AutomationCommandRegistry,
) -> None:
    mode_registry.register(ModeNotifications)
    mode_registry.register(ModeAnalyzeNotifications)
    mode_registry.register(ModeTestNotifications)
    mode_registry.register(ModeUserNotifications)
    mode_registry.register(ModePersonalUserNotifications)
    mode_registry.register(ModeEditNotificationRule)
    mode_registry.register(ModeEditUserNotificationRule)
    mode_registry.register(ModeEditPersonalNotificationRule)
    mode_registry.register(ModeNotificationParametersOverview)
    mode_registry.register(ModeEditNotificationRuleQuickSetup)

    mode_registry.register(ModeNotificationParameters)
    mode_registry.register(ModeEditNotificationParameter)

    match_item_generator_registry.register(
        MatchItemGeneratorNotificationParameter("notification_parameter")
    )
    automation_command_registry.register(AutomationNotificationTest)


class NotificationRuleLinks(NamedTuple):
    delete: str
    edit: str
    drag: str
    clone: str


class ABCNotificationsMode(ABCEventsMode[EventRule]):
    def __init__(self) -> None:
        super().__init__()

        # Make sure that all dynamic permissions are available
        permissions.load_dynamic_permissions()

    @classmethod
    def _rule_match_conditions(
        cls,
        sites: SiteConfigurations,
        service_levels: Sequence[tuple[int, str]],
    ) -> list[DictionaryEntry | tuple[str, ListChoice]]:
        return (
            cls._generic_rule_match_conditions(sites, service_levels)
            + cls._event_rule_match_conditions(flavour="notify")
            + cls._notification_rule_match_conditions()
        )

    @classmethod
    def _notification_rule_match_conditions(cls) -> list[DictionaryEntry]:
        return [
            (
                "match_escalation",
                Tuple(
                    title=_("Restrict to notification number"),
                    orientation="float",
                    elements=[
                        Integer(
                            help=_(
                                "Let through notifications counting from this number. "
                                "The first notification always has the number 1."
                            ),
                            default_value=1,
                            minvalue=1,
                            maxvalue=999999,
                        ),
                        Integer(
                            label=_("to"),
                            help=_("Let through notifications counting upto this number"),
                            default_value=999999,
                            minvalue=1,
                            maxvalue=999999,
                        ),
                    ],
                ),
            ),
            (
                "match_escalation_throttle",
                Tuple(
                    title=_("Throttle periodic notifications"),
                    help=_(
                        "This match option allows you to throttle periodic notifications after "
                        "a certain number of notifications have been created by the monitoring "
                        "core. If you for example select 10 as the beginning and 5 as the rate "
                        "then you will receive the notification 1 through 10 and then 15, 20, "
                        "25... and so on. Note that recovery notifications are not affected by throttling."
                    ),
                    orientation="float",
                    elements=[
                        Integer(
                            label=_("beginning from notification number"),
                            default_value=10,
                            minvalue=1,
                        ),
                        Integer(
                            label=_("send only every"),
                            default_value=5,
                            unit=_("th notification"),
                            minvalue=1,
                        ),
                    ],
                ),
            ),
            (
                "match_notification_comment",
                RegExp(
                    title=_("Match notification comment"),
                    help=_(
                        "This match only makes sense for custom notifications. When a user creates "
                        "a custom notification then he/she can enter a comment. This comment is shipped "
                        "in the notification context variable <tt>NOTIFICATIONCOMMENT</tt>. Here you can "
                        "make a condition of that comment. It is a regular expression matching the beginning "
                        "of the comment."
                    ),
                    size=60,
                    mode=RegExp.prefix,
                ),
            ),
        ] + cls._match_event_console_elements()

    @classmethod
    def _match_event_console_elements(cls) -> list[DictionaryEntry]:
        if edition(paths.omd_root) is Edition.CLOUD:  # disabled in CSE
            return []

        def migrate_ec_rule_id_match(val: list[TextInput] | TextInput) -> list[TextInput]:
            if isinstance(val, list):
                return val
            return [val]

        return [
            (
                "match_ec",
                Alternative(
                    title=_("Event Console alerts"),
                    help=_(
                        "The Event Console can have events create notifications in Checkmk. "
                        "These notifications will be processed by the rule based notification "
                        "system of Checkmk. This matching option helps you distinguishing "
                        "and also gives you access to special event fields."
                    ),
                    elements=[
                        FixedValue(
                            value=False,
                            title=_("Do not match Event Console alerts"),
                            totext="",
                        ),
                        Dictionary(
                            title=_("Match only Event Console alerts"),
                            elements=[
                                (
                                    "match_rule_id",
                                    MigrateNotUpdated(
                                        valuespec=ListOf(
                                            valuespec=ID(
                                                title=_("Match event rule"),
                                                label=_("Rule ID:"),
                                                size=12,
                                                allow_empty=False,
                                            ),
                                            add_label=_("Add Rule ID"),
                                            title=_("Rule IDs"),
                                        ),
                                        migrate=migrate_ec_rule_id_match,
                                    ),
                                ),
                                (
                                    "match_priority",
                                    Tuple(
                                        title=_("Match syslog priority"),
                                        help=_(
                                            "Define a range of syslog priorities this rule matches"
                                        ),
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
                                            "Make the rule match only if the event has a certain syslog facility. "
                                            "Messages not having a facility are classified as <tt>user</tt>."
                                        ),
                                        choices=syslog_facilities,
                                    ),
                                ),
                                (
                                    "match_comment",
                                    RegExp(
                                        title=_("Match event comment"),
                                        help=_(
                                            "This is a regular expression for matching the event's comment."
                                        ),
                                        mode=RegExp.prefix,
                                    ),
                                ),
                            ],
                        ),
                    ],
                ),
            )
        ]

    def _render_notification_rules(
        self,
        rules: list[EventRule],
        config: Config,
        userid: str = "",
        show_title: bool = False,
        show_buttons: bool = True,
        analyse: NotifyAnalysisInfo | None = None,
        start_nr: int = 0,
        profilemode: bool = False,
    ) -> None:
        if not rules:
            html.show_message(_("You have not created any rules yet."))
            return

        vs_match_conditions = Dictionary(
            elements=self._rule_match_conditions(
                config.sites,
                config.mkeventd_service_levels,
            )
        )

        all_users = userdb.load_users()
        title = self._table_title(show_title, profilemode, userid)
        with table_element(title=title, limit=None, sortable=False) as table:
            if analyse:
                analyse_rules, _analyse_plugins = analyse

            # have_match = False
            for nr, rule in enumerate(rules):
                table.row()

                # Analyse
                if analyse:
                    table.cell(css=["buttons"])
                    what, _anarule, reason = analyse_rules[nr + start_nr]
                    if what == "match":
                        html.static_icon(
                            StaticIcon(IconNames.checkmark), title=_("This rule matches")
                        )
                    elif what == "miss":
                        html.static_icon(
                            StaticIcon(IconNames.hyphen),
                            title=_("This rule does not match: %s") % reason,
                        )

                table.cell("#", css=["narrow nowrap"])

                if show_buttons and self._actions_allowed(rule):
                    html.write_text_permissive(nr)
                    table.cell(_("Actions"), css=["buttons"])
                    links = self._rule_links(rule, nr, profilemode, userid)
                    html.icon_button(
                        links.edit, _("Edit this notification rule"), StaticIcon(IconNames.edit)
                    )
                    html.icon_button(
                        links.clone,
                        _("Create a copy of this notification rule"),
                        StaticIcon(IconNames.clone),
                    )
                    html.icon_button(
                        links.delete,
                        _("Delete this notification rule"),
                        StaticIcon(IconNames.delete),
                    )
                    html.element_dragger_url("tr", base_url=links.drag)
                else:
                    table.cell("", css=["buttons"])
                    for _x in range(4):
                        html.empty_icon_button()

                table.cell("", css=["narrow"])
                if rule.get("disabled"):
                    html.static_icon(
                        StaticIcon(IconNames.cross),
                        title=_("This rule is currently disabled and will not be applied"),
                    )
                else:
                    html.empty_icon_button()

                notify_plugin_name, notify_method = rule["notify_plugin"]

                parameter_url = makeuri_contextless(
                    request,
                    [
                        ("mode", "notification_parameters"),
                        ("method", notify_plugin_name),
                    ],
                    filename="wato.py",
                )
                table.cell(
                    _("Method"),
                    HTMLWriter.render_a(
                        self._method_name(notify_plugin_name),
                        parameter_url,
                        target="_blank",
                        title=_("Go to parameters of this method"),
                    ),
                    css=["narrow nowrap"],
                )

                table.cell(_("Effect"), css=["narrow"])
                if notify_method is None:
                    html.static_icon(
                        StaticIcon(IconNames.cancel_notifications),
                        title=_("Cancel notifications for this plug-in type"),
                    )
                else:
                    html.static_icon(
                        StaticIcon(IconNames.notifications, emblem="enable"),
                        title=_("Create a notification"),
                    )

                table.cell(_("Bulk"), css=["narrow"])
                if "bulk" in rule or "bulk_period" in rule:
                    html.static_icon(
                        StaticIcon(IconNames.bulk),
                        title=_("This rule configures bulk notifications."),
                    )

                table.cell(_("Description"))
                url = rule.get("docu_url")
                if url:
                    html.icon_button(
                        url,
                        _("Context information about this rule"),
                        StaticIcon(IconNames.url),
                        target="_blank",
                    )
                    html.write_text_permissive("&nbsp;")
                html.write_text_permissive(rule["description"])
                table.cell(_("Contacts"))

                infos = self._rule_infos(rule, all_users)
                if not infos:
                    html.i(_("(no one)"))
                else:
                    html.open_ul()
                    for line in infos:
                        html.li(line)
                    html.close_ul()

                table.cell(_("Conditions"), css=["rule_conditions"])
                num_conditions = len([key for key in rule if key.startswith("match_")])
                if num_conditions:
                    title = _("%d conditions") % num_conditions
                    with foldable_container(
                        treename="rule_%s_%d" % (userid, nr),
                        id_=str(nr),
                        isopen=False,
                        title=title,
                        indent=False,
                    ):
                        html.write_text_permissive(
                            vs_match_conditions.value_to_html(cast(dict[str, object], rule))
                        )
                else:
                    html.i(_("(no conditions)"))

    def _method_name(self, notify_plugin_name: NotificationPluginNameStr) -> str:
        try:
            return [
                entry[1]
                for entry in notification_script_choices()
                if entry[0] == notify_plugin_name
            ][0]
        except IndexError:
            return _("Plain email")

    def _add_change(
        self, *, action_name: str, text: str, use_git: bool, site_configs: SiteConfigurations
    ) -> None:
        _changes.add_change(
            action_name=action_name,
            text=text,
            user_id=user.id,
            need_restart=False,
            use_git=use_git,
        )

    def _vs_notification_bulkby(self) -> ListChoice:
        return ListChoice(
            title=_("Create separate bulk notifications based on"),
            choices=[
                ("folder", _("Folder")),
                ("host", _("Host")),
                ("service", _("Service name")),
                ("sl", _("Service level")),
                ("check_type", _("Check type")),
                ("state", _("Host/Service state")),
            ]
            + (
                [
                    ("ec_contact", _("Event Console contact")),
                    ("ec_comment", _("Event Console comment")),
                ]
                if edition(paths.omd_root) is not Edition.CLOUD  # disabled in CSE
                else []
            ),
            default_value=["host"],
        )

    def _table_title(self, show_title: bool, profilemode: bool, userid: str) -> str | HTML:
        if not show_title:
            return ""
        if profilemode:
            return _("Notification rules")
        if userid:
            url = makeuri(request, [("mode", "user_notifications"), ("user", userid)])
            code = html.render_icon_button(
                url, _("Edit this user's notifications"), StaticIcon(IconNames.edit)
            )
            return code + _("Notification rules of user %s") % userid
        return _("Global notification rules")

    def _rule_infos(self, rule: EventRule, all_users: Users) -> list[str | HTML]:
        infos: list[str | HTML] = []
        if rule.get("contact_object"):
            infos.append(_("all contacts of the notified object"))
        if rule.get("contact_all"):
            infos.append(_("all users"))
        if rule.get("contact_all_with_email"):
            infos.append(_("all users with an email address"))
        if rule.get("contact_users"):
            contact_users_list = rule["contact_users"]
            info = HTML.with_escaping(_("users: "))
            if (
                len(contact_users_list) == 1
                and (explicit_user := contact_users_list[0]) not in all_users
            ):
                info += html.render_static_icon(
                    StaticIcon(IconNames.warning),
                    title=_("User %s does not exist.") % explicit_user,
                )
            info += HTML.with_escaping(", ".join(rule["contact_users"]))
            infos.append(info)
        if rule.get("contact_groups"):
            infos.append(_("contact groups: ") + (", ".join(rule["contact_groups"])))
        if rule.get("contact_emails"):
            infos.append(_("email addresses: ") + (", ".join(rule["contact_emails"])))
        return infos

    def _actions_allowed(self, rule: EventRule) -> bool:
        # In case a notification plug-in does not exist anymore the permission is completely missing.
        permission_name = "notification_plugin.%s" % rule["notify_plugin"][0]
        return permission_name not in permissions.permission_registry or user.may(permission_name)

    def _rule_links(
        self,
        rule: EventRule,
        nr: int,
        profilemode: bool,
        userid: str,
    ) -> NotificationRuleLinks:
        anavar = request.var("analyse", "")

        if profilemode:
            listmode = "user_notifications_p"
        elif userid:
            listmode = "user_notifications"
        else:
            listmode = "notifications"

        if profilemode:
            mode = "notification_rule_p"
        elif userid:
            mode = "user_notification_rule"
        else:
            mode = "notification_rule_quick_setup"

        back_mode: HTTPVariables = []
        mode_from_vars = request.var("mode")
        if mode_from_vars in ["analyze_notifications", "test_notifications"]:
            back_mode.append(("back_mode", mode_from_vars))

        def _delete_url() -> str:
            httpvars: HTTPVariables = [
                ("mode", listmode),
                ("user", userid),
                ("_delete", nr),
            ]
            return make_confirm_delete_link(
                url=make_action_link(httpvars + back_mode),
                title=_("Delete notification rule #%d") % nr,
                suffix=rule.get("description", ""),
            )

        def _drag_url() -> str:
            httpvars: HTTPVariables = [
                ("mode", listmode),
                ("analyse", anavar),
                ("user", userid),
                ("_move", nr),
            ]
            return make_action_link(httpvars + back_mode)

        def _edit_url() -> str:
            httpvars: HTTPVariables = [
                ("mode", mode),
                ("edit", nr),
                ("user", userid),
            ]
            return folder_preserving_link(httpvars + back_mode)

        def _clone_url() -> str:
            httpvars: HTTPVariables = [
                ("mode", mode),
                ("clone", nr),
                ("user", userid),
            ]
            return make_confirm_delete_link(
                url=folder_preserving_link(httpvars + back_mode),
                title=_("Clone & edit notification rule #%d") % nr,
                suffix=rule.get("description", ""),
                confirm_button=_("Yes, clone & edit"),
                cancel_button=_("No, don't clone"),
            )

        return NotificationRuleLinks(
            delete=_delete_url(),
            edit=_edit_url(),
            drag=_drag_url(),
            clone=_clone_url(),
        )


class ModeNotifications(ABCNotificationsMode):
    @classmethod
    def name(cls) -> str:
        return "notifications"

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return ["notifications"]

    def __init__(self) -> None:
        super().__init__()
        options = user.load_file("notification_display_options", {})
        self._show_user_rules = options.get("show_user_rules", False)

    def title(self) -> str:
        return _("Notifications")

    def page_menu(self, config: Config, breadcrumb: Breadcrumb) -> PageMenu:
        menu = PageMenu(
            dropdowns=[
                PageMenuDropdown(
                    name="notification_rules",
                    title=_("Notifications"),
                    topics=[
                        PageMenuTopic(
                            title=_("Add new"),
                            entries=[
                                PageMenuEntry(
                                    title=_("Add notification rule"),
                                    icon_name=StaticIcon(IconNames.new),
                                    item=make_simple_link(
                                        folder_preserving_link(
                                            [("mode", "notification_rule_quick_setup")]
                                        )
                                    ),
                                    is_shortcut=True,
                                    is_suggested=True,
                                ),
                                PageMenuEntry(
                                    title=_("Parameters for notification methods"),
                                    icon_name=StaticIcon(IconNames.clipboard),
                                    item=make_simple_link(
                                        folder_preserving_link(
                                            [
                                                (
                                                    "mode",
                                                    ModeNotificationParametersOverview.name(),
                                                )
                                            ]
                                        )
                                    ),
                                    is_shortcut=True,
                                    is_suggested=True,
                                ),
                            ],
                        ),
                        PageMenuTopic(
                            title=_("Analyze"),
                            entries=[
                                PageMenuEntry(
                                    title=_("Test notifications"),
                                    name="test_notifications",
                                    icon_name=StaticIcon(IconNames.analysis),
                                    item=make_simple_link(
                                        folder_preserving_link([("mode", "test_notifications")])
                                    ),
                                    is_shortcut=True,
                                    is_suggested=True,
                                ),
                                PageMenuEntry(
                                    title=_("Analyze recent notifications"),
                                    icon_name=StaticIcon(IconNames.analyze),
                                    item=make_simple_link(
                                        folder_preserving_link([("mode", "analyze_notifications")])
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
                            title=_("Global settings"),
                            entries=list(self._page_menu_entries_related()),
                        ),
                    ],
                ),
            ],
            breadcrumb=breadcrumb,
            inpage_search=PageMenuSearch(),
        )
        self._extend_display_dropdown(menu)
        menu.add_doc_reference(_("Notifications"), DocReference.NOTIFICATIONS)
        return menu

    def _page_menu_entries_related(self) -> Iterator[PageMenuEntry]:
        yield PageMenuEntry(
            title=_("Fallback email address for notifications"),
            icon_name=StaticIcon(IconNames.configuration),
            item=make_simple_link(
                folder_preserving_link(
                    [
                        ("mode", "edit_configvar"),
                        ("varname", "notification_fallback_email"),
                    ]
                )
            ),
        )

        yield PageMenuEntry(
            title=_("Failed notification horizon"),
            icon_name=StaticIcon(IconNames.configuration),
            item=make_simple_link(
                folder_preserving_link(
                    [
                        ("mode", "edit_configvar"),
                        ("varname", "failed_notification_horizon"),
                    ]
                )
            ),
        )

        yield PageMenuEntry(
            title=_("Notification log level"),
            icon_name=StaticIcon(IconNames.configuration),
            item=make_simple_link(
                folder_preserving_link(
                    [
                        ("mode", "edit_configvar"),
                        ("varname", "notification_logging"),
                    ]
                )
            ),
        )

        yield PageMenuEntryCEEOnly(
            title=_("Logging of the notification mechanics"),
            icon_name=StaticIcon(IconNames.configuration),
            item=make_simple_link(
                folder_preserving_link(
                    [
                        ("mode", "edit_configvar"),
                        ("varname", "cmc_debug_notifications"),
                    ]
                )
            ),
        )

    def _extend_display_dropdown(self, menu: PageMenu) -> None:
        display_dropdown = menu.get_dropdown_by_name("display", make_display_options_dropdown())
        display_dropdown.topics.insert(
            0,
            PageMenuTopic(
                title=_("Toggle elements"),
                entries=[
                    PageMenuEntry(
                        title=_("Show user rules"),
                        icon_name=StaticIcon(
                            IconNames.toggle_on if self._show_user_rules else IconNames.toggle_off
                        ),
                        item=make_simple_link(
                            makeactionuri(
                                request,
                                transactions,
                                [
                                    (
                                        "_show_user",
                                        "" if self._show_user_rules else "1",
                                    ),
                                ],
                            )
                        ),
                    ),
                ],
            ),
        )

    def action(self, config: Config) -> ActionResult:
        check_csrf_token()

        if request.has_var("_show_user"):
            if transactions.check_transaction():
                self._show_user_rules = bool(request.var("_show_user"))
                self._save_notification_display_options()

        else:
            self._generic_rule_list_actions(
                self._get_notification_rules(),
                "notification",
                _("notification rule"),
                lambda c: NotificationRuleConfigFile().save(
                    c, pprint_value=config.wato_pprint_config
                ),
                use_git=config.wato_use_git,
                site_configs=config.sites,
            )

        if back_mode := request.var("back_mode"):
            return redirect(mode_url(back_mode, user=request.get_str_input_mandatory("user")))

        return redirect(self.mode_url())

    def _get_notification_rules(self) -> list[EventRule]:
        return NotificationRuleConfigFile().load_for_reading()

    def _save_notification_display_options(self) -> None:
        user.save_file(
            "notification_display_options",
            {
                "show_user_rules": self._show_user_rules,
            },
        )

    def page(self, config: Config) -> None:
        self._show_overview()
        self._show_rules(analyse=None, config=config)

    def _show_overview(self) -> None:
        html.vue_component(
            component_name="cmk-notification-overview",
            data=asdict(_get_vue_data()),
        )

    def _get_date(self, context: NotificationContext) -> str:
        if "MICROTIME" in context:
            return time.strftime(
                "%Y-%m-%d %H:%M:%S",
                time.localtime(float(context["MICROTIME"]) / 1000000.0),
            )
        return (
            context.get("SHORTDATETIME")
            or context.get("LONGDATETIME")
            or context.get("DATE")
            or _("Unknown date")
        )

    def _add_state_cells(self, table: Table, nottype: str) -> None:
        if nottype.startswith("DOWNTIME"):
            table.cell(_("State"))
            html.static_icon(StaticIcon(IconNames.downtime), title=_("Downtime"))
        elif nottype.startswith("ACK"):
            table.cell(_("State"))
            html.static_icon(StaticIcon(IconNames.ack), title=_("Acknowledgment"))
        elif nottype.startswith("FLAP"):
            table.cell(_("State"))
            html.static_icon(StaticIcon(IconNames.flapping), title=_("Flapping"))
        else:
            table.cell(_("State"), "")

    def _add_host_service_cells(self, table: Table, context: NotificationContext) -> None:
        table.cell(_("Host"), context.get("HOSTNAME", ""))
        table.cell(_("Service"), context.get("SERVICEDESC", ""))

    def _add_plugin_output_cells(
        self, table: Table, context: NotificationContext, *, escape_plugin_output: bool
    ) -> None:
        output = context.get("SERVICEOUTPUT", context.get("HOSTOUTPUT", ""))
        table.cell(
            _("Plug-in output"),
            cmk.gui.view_utils.format_plugin_output(
                output,
                request=request,
                must_escape=True,  # Not sure how to determine this here, so let's go with the safe option
                shall_escape=escape_plugin_output,
            ),
        )

    def _add_toggable_notification_context(
        self,
        table: Table,
        context: NotificationContext,
        ident: str,
    ) -> None:
        table.row(css=["notification_context hidden"], id_=ident)
        table.cell(colspan=8)

        html.open_table()
        for index, (key, val) in enumerate(sorted(context.items())):
            if index % 2 == 0:
                if index != 0:
                    html.close_tr()
                html.open_tr()
            html.th(key)
            html.td(val)
        html.close_table()

    def _show_rules(
        self,
        analyse: NotifyAnalysisInfo | None,
        config: Config,
    ) -> None:
        start_nr = 0
        rules = self._get_notification_rules()
        self._render_notification_rules(
            rules,
            config,
            show_title=True,
            analyse=analyse,
            start_nr=start_nr,
        )
        start_nr += len(rules)
        if self._show_user_rules:
            for user_id, user_rules in sorted(
                load_user_notification_rules().items(), key=lambda u: u[0]
            ):
                self._render_notification_rules(
                    user_rules,
                    config,
                    userid=user_id,
                    show_title=True,
                    show_buttons=False,
                    analyse=analyse,
                    start_nr=start_nr,
                )
                start_nr += len(user_rules)

    def _vs_notification_scripts(self) -> DropdownChoice[str]:
        return DropdownChoice(
            title=_("Notification Script"),
            choices=notification_script_choices,
            default_value="mail",
        )

    def _show_resulting_notifications(self, result: NotifyAnalysisInfo) -> None:
        with table_element(table_id="plugins", title=_("Predicted notifications")) as table:
            for contact, plugin, parameters, bulk in result[1]:
                table.row()
                if contact.startswith("mailto:"):
                    contact = contact[7:]  # strip of fake-contact mailto:-prefix
                table.cell(_("Recipient"), contact.replace(",", ", "))
                table.cell(_("Method"), self._vs_notification_scripts().value_to_html(plugin))
                table.cell(_("Parameters"), ", ".join(list(parameters)))
                table.cell(_("Building bulks"))
                if bulk:
                    html.write_text_permissive(_("Time horizon") + ": ")
                    if is_always_bulk(bulk):
                        html.write_text_permissive(Age().value_to_html(bulk["interval"]))
                    else:
                        html.write_text_permissive(Age().value_to_html(0))
                    html.write_text_permissive(", %s: %d" % (_("Maximum count"), bulk["count"]))
                    html.write_text_permissive(", %s " % (_("group by")))
                    html.write_text_permissive(
                        self._vs_notification_bulkby().value_to_html(bulk["groupby"])
                    )


def _fallback_mail_contacts_configured() -> bool:
    current_settings = load_configuration_settings()
    if current_settings.get("notification_fallback_email"):
        return True

    for user_spec in userdb.load_users(lock=False).values():
        if user_spec.get("fallback_contact", False):
            return True

    return False


def _get_vue_data() -> Notifications:
    all_sites_count, sites_with_disabled_notifications = get_disabled_notifications_infos()
    total_send_notifications = _get_total_sent_notifications_last_seven_days()
    return Notifications(
        overview_title_i18n=_("Notification overview"),
        fallback_warning=(
            NotificationFallbackWarning(
                i18n=NotificationFallbackWarningI18n(
                    title=_("No fallback email address configured"),
                    message=_(
                        "Without a fallback email address, you may miss alerts "
                        "that are not covered by a notification rule. To ensure "
                        "full notification coverage, we recommend that you "
                        "configure the fallback email address to which all "
                        "alerts that don't match a notification rule are sent."
                    ),
                    setup_link_title=_("Configure fallback email address"),
                    do_not_show_again_title=_("Do not show again"),
                ),
                setup_link=makeuri_contextless(
                    request,
                    [
                        ("varname", "notification_fallback_email"),
                        ("mode", "edit_configvar"),
                    ],
                    filename="wato.py",
                ),
                do_not_show_again_link=makeuri_contextless(
                    request,
                    [
                        ("varname", "notification_fallback_email"),
                        ("mode", "edit_configvar"),
                    ],
                    filename="wato.py",
                ),
            )
            if not _fallback_mail_contacts_configured()
            else None
        ),
        notification_stats=NotificationStats(
            num_sent_notifications=total_send_notifications,
            num_failed_notifications=get_failed_notification_count(),
            sent_notification_link=makeuri_contextless(
                request,
                [
                    ("view_name", "notifications"),
                    ("_show_filter_form", "0"),
                    ("filled_in", "filter"),
                    ("_active", "logtime;log_notification_phase;log_class;log_type"),
                    ("logtime_from", "7"),
                    ("is_log_notification_phase", "0"),
                    ("logclass3", "on"),
                    ("log_type", ".*NOTIFICATION RESULT$"),
                ],
                filename="view.py",
            ),
            failed_notification_link=makeuri_contextless(
                request,
                [("view_name", "failed_notifications")],
                filename="view.py",
            ),
            i18n=NotificationStatsI18n(
                sent_notifications=_("Total sent notifications"),
                failed_notifications=_("Failed notifications"),
                sent_notifications_link_title=_("Last 7 days"),
                failed_notifications_link_title=_("View failed notifications"),
            ),
        ),
        core_stats=NotificationCoreStats(
            sites=sites_with_disabled_notifications,
            i18n=NotificationCoreStatsI18n(
                title=_("Core status of notifications"),
                sites_column_title=_("Sites"),
                status_column_title=_("Notification core status"),
                ok_msg=_("Notifications enabled on %d of %d %s")
                % (
                    all_sites_count,
                    all_sites_count,
                    site_prefix := ungettext("site", "sites", all_sites_count),
                ),
                warning_msg=_("Notifications disabled on %d of %d %s")
                % (
                    len(sites_with_disabled_notifications),
                    all_sites_count,
                    site_prefix,
                ),
                disabled_msg=_("Disabled via master control"),
            ),
        ),
        rule_sections=[
            RuleSection(
                i18n=_("Optimize notifications"),
                topics=_get_ruleset_infos(OPTIMIZE_NOTIFICATIONS_ENTRIES),
            ),
            RuleSection(
                i18n=_("Supporting rules"),
                topics=_get_ruleset_infos(SUPPORT_NOTIFICATIONS_ENTRIES),
            ),
        ],
        user_id=str(user.id),
    )


def _get_total_sent_notifications_last_seven_days() -> int:
    current_time = datetime.now()
    seven_days_ago = current_time - timedelta(days=7)
    from_timestamp = int(seven_days_ago.timestamp())
    return get_total_sent_notifications(from_timestamp=from_timestamp)


def _get_ruleset_infos(entries: dict[str, list[str]]) -> list[RuleTopic]:
    all_rulesets = AllRulesets.load_all_rulesets()
    rule_topic_list: list[RuleTopic] = []
    for section, ruleset in entries.items():
        rule_list: list[Rule] = []
        for rule_id in ruleset:
            try:
                # Some rules are only available in CEE
                rule = all_rulesets.get(rule_id)
            except KeyError:
                continue
            # Should not happen
            if rule is None:
                continue

            rule_list.append(
                Rule(
                    i18n=rule.title() or _("Unknown rule with ID %s") % rule_id,
                    count=str(rule.num_rules()),
                    link=makeuri_contextless(
                        request,
                        [("varname", rule_id), ("mode", "edit_ruleset")],
                        filename="wato.py",
                    ),
                )
            )
        rule_topic_list.append(
            RuleTopic(
                i18n=section,
                rules=rule_list,
            )
        )
    return rule_topic_list


class ModeAnalyzeNotifications(ModeNotifications):
    def __init__(self) -> None:
        super().__init__()
        options = user.load_file("analyze_notification_display_options", {})
        self._show_bulks = options.get("show_bulks", False)
        self._show_user_rules = options.get("show_user_rules", False)

    @classmethod
    def name(cls) -> str:
        return "analyze_notifications"

    @classmethod
    def parent_mode(cls) -> type[WatoMode] | None:
        return ModeNotifications

    def title(self) -> str:
        return _("Analyze recent notifications")

    def page_menu(self, config: Config, breadcrumb: Breadcrumb) -> PageMenu:
        menu = PageMenu(
            dropdowns=[
                PageMenuDropdown(
                    name="analyze_notifications",
                    title=_("Analyze recent notifications"),
                    topics=[
                        PageMenuTopic(
                            title=_("Add new"),
                            entries=[
                                PageMenuEntry(
                                    title=_("Add notification rule"),
                                    icon_name=StaticIcon(IconNames.new),
                                    item=make_simple_link(
                                        folder_preserving_link(
                                            [("mode", "notification_rule_quick_setup")]
                                        )
                                    ),
                                    is_shortcut=False,
                                    is_suggested=False,
                                ),
                            ],
                        ),
                        PageMenuTopic(
                            title=_("Test notifications"),
                            entries=[
                                PageMenuEntry(
                                    title=_("Test notifications"),
                                    name="test_notifications",
                                    icon_name=StaticIcon(IconNames.analysis),
                                    item=make_simple_link(
                                        folder_preserving_link([("mode", "test_notifications")])
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
                            title=_("Global settings"),
                            entries=[
                                PageMenuEntry(
                                    title=_("Store notifications for rule analysis"),
                                    icon_name=StaticIcon(IconNames.configuration),
                                    item=make_simple_link(
                                        folder_preserving_link(
                                            [
                                                ("mode", "edit_configvar"),
                                                ("varname", "notification_backlog"),
                                            ]
                                        )
                                    ),
                                ),
                                PageMenuEntry(
                                    title=_("Notification log level"),
                                    icon_name=StaticIcon(IconNames.configuration),
                                    item=make_simple_link(
                                        folder_preserving_link(
                                            [
                                                ("mode", "edit_configvar"),
                                                ("varname", "notification_logging"),
                                            ]
                                        )
                                    ),
                                ),
                                PageMenuEntryCEEOnly(
                                    title=_("Logging of the notification mechanics"),
                                    icon_name=StaticIcon(IconNames.configuration),
                                    item=make_simple_link(
                                        folder_preserving_link(
                                            [
                                                ("mode", "edit_configvar"),
                                                ("varname", "cmc_debug_notifications"),
                                            ]
                                        )
                                    ),
                                ),
                            ],
                        ),
                    ],
                ),
            ],
            breadcrumb=breadcrumb,
            inpage_search=PageMenuSearch(),
        )
        self._extend_display_dropdown(menu)
        menu.add_doc_reference(
            _("Rule evaluation by the notification module"),
            DocReference.ANALYZE_NOTIFICATIONS,
        )
        return menu

    def _extend_display_dropdown(self, menu: PageMenu) -> None:
        display_dropdown = menu.get_dropdown_by_name("display", make_display_options_dropdown())
        display_dropdown.topics.insert(
            0,
            PageMenuTopic(
                title=_("Toggle elements"),
                entries=[
                    PageMenuEntry(
                        title=(
                            _("Hide bulk notifications")
                            if self._show_bulks
                            else _("Show bulk notifications")
                        ),
                        icon_name=StaticIcon(
                            IconNames.toggle_on if self._show_bulks else IconNames.toggle_off
                        ),
                        item=make_simple_link(
                            makeactionuri(
                                request,
                                transactions,
                                [
                                    ("_show_bulks", "" if self._show_bulks else "1"),
                                ],
                            )
                        ),
                        is_shortcut=True,
                        is_suggested=True,
                    ),
                    PageMenuEntry(
                        title=_("Show user rules"),
                        icon_name=StaticIcon(
                            IconNames.toggle_on if self._show_user_rules else IconNames.toggle_off
                        ),
                        item=make_simple_link(
                            makeactionuri(
                                request,
                                transactions,
                                [
                                    (
                                        "_show_user",
                                        "" if self._show_user_rules else "1",
                                    ),
                                ],
                            )
                        ),
                    ),
                ],
            ),
        )

    def page(self, config: Config) -> None:
        result = self._get_result_from_request(debug=config.debug)
        self._show_bulk_notifications(debug=config.debug)
        self._show_notification_backlog(escape_plugin_output=config.escape_plugin_output)
        if request.var("analyse") and result:
            self._show_resulting_notifications(result=result)
        self._show_rules(result, config)

    def _get_result_from_request(self, *, debug: bool) -> NotifyAnalysisInfo | None:
        if request.var("analyse"):
            nr = request.get_integer_input_mandatory("analyse")
            return notification_analyse(nr, debug=debug).result

        return None

    def _show_bulk_notifications(self, *, debug: bool) -> None:
        if self._show_bulks:
            # Warn if there are unsent bulk notifications
            if not self._render_bulks(only_ripe=False, debug=debug):
                html.show_message(_("Currently there are no unsent bulk notifications pending."))
        else:
            # Warn if there are unsent bulk notifications
            self._render_bulks(only_ripe=True, debug=debug)

    def _render_bulks(self, *, only_ripe: bool, debug: bool) -> bool:
        bulks = notification_get_bulks(only_ripe=only_ripe, debug=debug).result
        if not bulks:
            return False

        title = _("Overdue bulk notifications!") if only_ripe else _("Open bulk notifications")
        with table_element(title=title) as table:
            for directory, age, interval, timeperiod, maxcount, uuids in bulks:
                dirparts = directory.split("/")
                contact = dirparts[-3]
                method = dirparts[-2]
                bulk_id = dirparts[-1].split(",", 2)[-1]
                table.row()
                table.cell(_("Contact"), contact)
                table.cell(_("Method"), method)
                table.cell(_("Bulk ID"), bulk_id)
                table.cell(_("Max. Age (sec)"), str(interval), css=["number"])
                table.cell(_("Age (sec)"), str(age), css=["number"])
                if interval and interval != "n.a." and age >= float(interval):
                    html.static_icon(
                        StaticIcon(IconNames.warning),
                        title=_("Age of oldest notification is over maximum age"),
                    )
                table.cell(_("Time Period"), str(timeperiod))
                table.cell(_("Max. Count"), str(maxcount), css=["number"])
                table.cell(_("Count"), str(len(uuids)), css=["number"])
                if len(uuids) >= maxcount:
                    html.static_icon(
                        StaticIcon(IconNames.warning),
                        title=_("Number of notifications exceeds maximum allowed number"),
                    )
        return True

    def _show_notification_backlog(self, escape_plugin_output: bool) -> None:
        """Show recent notifications. We can use them for rule analysis"""
        backlog = store.load_object_from_file(
            cmk.utils.paths.var_dir / "notify/backlog.mk",
            default=[],
        )
        if not backlog:
            return

        with table_element(
            table_id="backlog",
            title=_("Analysis: Recent notifications"),
            sortable=False,
        ) as table:
            for nr, context in enumerate(backlog):
                table.row()
                table.cell("&nbsp;", css=["buttons"])

                analyse_url = makeuri(request, [("analyse", str(nr))])
                html.icon_button(
                    analyse_url,
                    _("Analyze rule set with this notification"),
                    StaticIcon(IconNames.analyze),
                )

                html.icon_button(
                    None,
                    _("Show / hide notification context"),
                    StaticIcon(IconNames.toggle_context),
                    onclick="cmk.wato.toggle_container('notification_context_%d')" % nr,
                )

                replay_url = makeactionuri(request, transactions, [("_replay", str(nr))])
                html.icon_button(
                    replay_url,
                    _("Replay this notification, send it again!"),
                    StaticIcon(IconNames.reload_cmk),
                )

                if request.var("analyse") and nr == request.get_integer_input_mandatory("analyse"):
                    html.static_icon(
                        StaticIcon(IconNames.checkmark),
                        title=_("You are analysing this notification"),
                    )

                table.cell(_("Nr."), str(nr + 1), css=["number"])

                table.cell(_("Time"), self._get_date(context), css=["nobr"])
                nottype = context.get("NOTIFICATIONTYPE", "")
                table.cell(_("Type"), nottype)

                if nottype in ["PROBLEM", "RECOVERY"]:
                    if context.get("SERVICESTATE"):
                        statename = context["SERVICESTATE"][:4]
                        state = context["SERVICESTATEID"]
                        css = [f"state svcstate state{state}"]
                    else:
                        statename = context.get("HOSTSTATE")[:4]
                        state = context["HOSTSTATEID"]
                        css = [f"state hstate hstate{state}"]
                    table.cell(
                        _("State"),
                        HTMLWriter.render_span(statename, class_=["state_rounded_fill"]),
                        css=css,
                    )
                else:
                    self._add_state_cells(table=table, nottype=nottype)

                self._add_host_service_cells(
                    table=table,
                    context=context,
                )
                self._add_plugin_output_cells(
                    table=table, context=context, escape_plugin_output=escape_plugin_output
                )

                self._add_toggable_notification_context(
                    table=table,
                    context=context,
                    ident=f"notification_context_{nr}",
                )

                # This dummy row is needed for not destroying the odd/even row highlighting
                table.row(css=["notification_context hidden"])

    def action(self, config: Config) -> ActionResult:
        check_csrf_token()

        if request.has_var("_show_bulks"):
            if transactions.check_transaction():
                self._show_bulks = bool(request.var("_show_bulks"))
                self._save_analyze_notification_display_options()

        if request.has_var("_show_user"):
            if transactions.check_transaction():
                self._show_user_rules = bool(request.var("_show_user"))
                self._save_analyze_notification_display_options()

        if request.has_var("_replay"):
            if transactions.check_transaction():
                replay_nr = request.get_integer_input_mandatory("_replay")
                notification_replay(replay_nr, debug=config.debug)
                flash(_("Replayed notification number %d") % (replay_nr + 1))
                return None

        return redirect(self.mode_url())

    def _save_analyze_notification_display_options(self) -> None:
        user.save_file(
            "analyze_notification_display_options",
            {
                "show_bulks": self._show_bulks,
                "show_user_rules": self._show_user_rules,
            },
        )


class NotificationTestRequest(NamedTuple):
    context: str
    dispatch: str
    debug: bool


class AutomationNotificationTest(AutomationCommand[NotificationTestRequest]):
    def command_name(self) -> str:
        return "notification-test"

    def get_request(self, config: Config, request: Request) -> NotificationTestRequest:
        if (context := request.var("context")) is None:
            raise MKGeneralException(_("Context is missing"))

        return NotificationTestRequest(
            context=context,
            dispatch=request.var("dispatch", ""),
            debug=request.var("debug", "") == "1",
        )

    def execute(self, api_request: NotificationTestRequest) -> NotifyAnalysisInfo | None:
        return notification_test(
            raw_context=json.loads(api_request.context),
            dispatch=api_request.dispatch,
            debug=api_request.debug,
        ).result


class NotificationTestType(enum.StrEnum):
    host = "host_test"
    service = "svc_test"


class AdvancedTestOptions(TypedDict):
    notification_nr: NotRequired[int]
    date_and_time: NotRequired[tuple[str, str, str]]


class ModeTestNotifications(ModeNotifications):
    def __init__(self) -> None:
        super().__init__()
        options = user.load_file("test_notification_display_options", {})
        self._show_user_rules = options.get("show_user_rules", False)

    @classmethod
    def name(cls) -> str:
        return "test_notifications"

    @classmethod
    def parent_mode(cls) -> type[WatoMode] | None:
        return ModeNotifications

    def title(self) -> str:
        return _("Test notifications")

    def page_menu(self, config: Config, breadcrumb: Breadcrumb) -> PageMenu:
        menu = PageMenu(
            dropdowns=[
                PageMenuDropdown(
                    name="test_notifications",
                    title=_("Test notifications"),
                    topics=[
                        PageMenuTopic(
                            title=_("Add new"),
                            entries=[
                                PageMenuEntry(
                                    title=_("Add notification rule"),
                                    icon_name=StaticIcon(IconNames.new),
                                    item=make_simple_link(
                                        folder_preserving_link(
                                            [("mode", "notification_rule_quick_setup")]
                                        )
                                    ),
                                    is_shortcut=False,
                                    is_suggested=False,
                                ),
                            ],
                        ),
                        PageMenuTopic(
                            title=_("Analyze"),
                            entries=[
                                PageMenuEntry(
                                    title=_("Analyze recent notifications"),
                                    name="analyze_notifications",
                                    icon_name=StaticIcon(IconNames.analyze),
                                    item=make_simple_link(
                                        folder_preserving_link([("mode", "analyze_notifications")])
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
                            title=_("Overview"),
                            entries=[
                                PageMenuEntry(
                                    title=_("Notifications"),
                                    icon_name=StaticIcon(IconNames.notifications),
                                    item=make_simple_link(
                                        folder_preserving_link([("mode", "notifications")])
                                    ),
                                    is_shortcut=True,
                                    is_suggested=True,
                                ),
                            ],
                        ),
                        PageMenuTopic(
                            title=_("Global settings"),
                            entries=[
                                PageMenuEntry(
                                    title=_("Notification log level"),
                                    icon_name=StaticIcon(IconNames.configuration),
                                    item=make_simple_link(
                                        folder_preserving_link(
                                            [
                                                ("mode", "edit_configvar"),
                                                ("varname", "notification_logging"),
                                            ]
                                        )
                                    ),
                                ),
                                PageMenuEntryCEEOnly(
                                    title=_("Logging of the notification mechanics"),
                                    icon_name=StaticIcon(IconNames.configuration),
                                    item=make_simple_link(
                                        folder_preserving_link(
                                            [
                                                ("mode", "edit_configvar"),
                                                ("varname", "cmc_debug_notifications"),
                                            ]
                                        )
                                    ),
                                ),
                            ],
                        ),
                    ],
                ),
            ],
            breadcrumb=breadcrumb,
            inpage_search=PageMenuSearch(),
        )
        self._extend_display_dropdown(menu)
        menu.add_doc_reference(
            _("Testing notifications"),
            DocReference.TEST_NOTIFICATIONS,
        )
        return menu

    def action(self, config: Config) -> ActionResult:
        check_csrf_token()

        if request.has_var("_show_user"):
            if transactions.check_transaction():
                self._show_user_rules = bool(request.var("_show_user"))
                self._save_test_notification_display_options()

        if self._test_notification_ongoing():
            if transactions.check_transaction():
                context, dispatch, test_type = self._infos_from_vars()
                return redirect(
                    makeuri(
                        request,
                        [
                            ("mode", "test_notifications"),
                            ("test_notification", "1"),
                            ("test_context", json.dumps(context)),
                            ("dispatch", dispatch or ""),
                            ("test_type", test_type),
                        ],
                        filename="wato.py",
                    )
                )

        return redirect(self.mode_url())

    def page(self, config: Config) -> None:
        # TODO temp. solution to provide flashed message after quick setup
        if message := request.var("result"):
            # TODO Add notification rule number
            html.javascript(
                "cmk.wato.message(%s, %s, %s)"
                % (
                    json.dumps(message),
                    json.dumps("success"),
                    json.dumps("result"),
                )
            )

        self._render_test_notifications()

        analyse = None
        if not user_errors:
            context, analyse = self._result_from_request(
                site_configs=config.sites, debug=config.debug
            )
            self._show_notification_test_overview(context, analyse)
            self._show_notification_test_details(
                context, analyse, escape_plugin_output=config.escape_plugin_output
            )
            if request.var("test_notification") and analyse:
                self._show_resulting_notifications(result=analyse)
        self._show_rules(analyse, config)

    def _result_from_request(
        self, *, site_configs: Mapping[SiteId, SiteConfiguration], debug: bool
    ) -> tuple[NotificationContext | None, NotifyAnalysisInfo | None]:
        if request.var("test_notification"):
            try:
                context: NotificationContext = json.loads(
                    request.get_str_input_mandatory("test_context")
                )
            except Exception as e:
                raise MKUserError(None, "Failed to parse context from request.") from e

            event_date = time.time()
            self._add_missing_host_context(context, event_date)
            if context["WHAT"] == "SERVICE":
                self._add_missing_service_context(context, event_date)

            site_id = SiteId(context["SITEOFHOST"])
            site_config = site_configs[site_id]
            remote_spooling = site_config.get("globals", {}).get("notification_spooling", False)
            automation_config = make_automation_config(site_config)
            if isinstance(automation_config, LocalAutomationConfig) or remote_spooling:
                return (
                    context,
                    notification_test(
                        raw_context=context,
                        dispatch=request.var("dispatch", ""),
                        debug=debug,
                    ).result,
                )

            remote_result = cast(
                NotifyAnalysisInfo,
                do_remote_automation(
                    automation_config,
                    "notification-test",
                    [
                        ("context", json.dumps(context)),
                        ("dispatch", request.var("dispatch", "")),
                        ("debug", "1" if debug else ""),
                    ],
                    debug=debug,
                ),
            )

            return (context, remote_result)

        return None, None

    def _show_notification_test_overview(
        self,
        context: NotificationContext | None,
        analyse: NotifyAnalysisInfo | None,
    ) -> None:
        if not context or not analyse:
            return

        html.open_div(id_="notification_analysis_container")
        html.open_div(class_="state_bar state0")
        html.open_span()
        html.static_icon(StaticIcon(IconNames.check))
        html.close_span()
        html.close_div()

        html.open_div(class_="message_container")
        html.h2(_("Test results"))
        analyse_rules, analyse_resulting_notifications = analyse
        match_count_all = len(tuple(entry for entry in analyse_rules if "match" in entry))
        match_count_user = len(
            [rule for rule in analyse_rules if rule[1].get("contact") and "match" in rule]
        )
        match_count_global = match_count_all - match_count_user

        html.write_text_permissive(
            _("%s notification %s (%d global %s, %d user %s)")
            % (
                match_count_all,
                ungettext(
                    "rule matches",
                    "rules are matching",
                    match_count_all,
                ),
                match_count_global,
                ungettext(
                    "rule",
                    "rules",
                    match_count_global,
                ),
                match_count_user,
                ungettext(
                    "rule",
                    "rules",
                    match_count_user,
                ),
            )
        )
        html.br()
        resulting_notifications_count = _get_resulting_notifications_count(
            analyse_resulting_notifications
        )
        html.write_text_permissive(
            ("%d %s")
            % (
                resulting_notifications_count,
                ungettext(
                    "notification would have been sent based on your notification rules (see table: 'Predicted notifications')",
                    "notifications would have been sent based on your notification rules (see table: 'Predicted notifications')",
                    resulting_notifications_count,
                ),
            )
        )
        if dispatch_method := request.var("dispatch"):
            unique_contacts = {
                contact
                for raw_contact, method, *_ in analyse_resulting_notifications
                for contact in raw_contact.split(",")
                if method == dispatch_method
            }
            notification_sent_count = len(unique_contacts)
            html.br()
            html.write_text_permissive(
                _("%d %s %s.")
                % (
                    notification_sent_count,
                    self._vs_notification_scripts().value_to_html(dispatch_method),
                    ungettext(
                        "notification has been triggered",
                        "notifications have been triggered",
                        notification_sent_count,
                    ),
                )
            )
        html.br()
        html.br()
        html.write_text_permissive("See the following tables for more details.")
        html.close_div()
        html.close_div()

    def _show_notification_test_details(
        self,
        context: NotificationContext | None,
        analyse: NotifyAnalysisInfo | None,
        *,
        escape_plugin_output: bool,
    ) -> None:
        if not context:
            return

        with table_element(
            table_id="notification_test",
            title=_("Analysis: Test notifications"),
            sortable=False,
        ) as table:
            table.row()
            table.cell("&nbsp;", css=["buttons"])

            html.icon_button(
                None,
                _("Show / hide notification context"),
                StaticIcon(IconNames.toggle_context),
                onclick="cmk.wato.toggle_container('notification_context_test')",
            )

            if analyse:
                table.cell(css=["buttons"])
                analyse_rules, _analyse_plugins = analyse
                if any("match" in entry for entry in analyse_rules):
                    html.static_icon(
                        StaticIcon(IconNames.checkmark), title=_("This notification matches")
                    )
                else:
                    html.static_icon(
                        StaticIcon(IconNames.hyphen),
                        title=_(
                            "This notification does not match. See reasons in "
                            "global notification rule list."
                        ),
                    )

            table.cell(_("Date and time"), self._get_date(context), css=["nobr"])
            nottype = context.get("NOTIFICATIONTYPE", "")
            table.cell(_("Type"), nottype)

            if nottype in ["PROBLEM", "RECOVERY"]:
                if context.get("SERVICESTATE"):
                    css = "state svcstate state"
                    last_state_name = context["PREVIOUSSERVICEHARDSTATE"]
                    last_state = {
                        "OK": "0",
                        "WARNING": "1",
                        "CRITICAL": "2",
                        "UNKNOWN": "3",
                    }[last_state_name]
                    state = context["SERVICESTATEID"]
                    state_name = context["SERVICESTATE"]
                else:
                    css = "state hstate hstate"
                    last_state_name = context["PREVIOUSHOSTHARDSTATE"]
                    last_state = {"UP": "0", "DOWN": "1", "UNREACHABLE": "2"}[last_state_name]
                    state = context["HOSTSTATEID"]
                    state_name = context["HOSTSTATE"]
                table.cell(
                    _("From"),
                    HTMLWriter.render_span(last_state_name[:4], class_=["state_rounded_fill"]),
                    css=[f"{css}{last_state}"],
                )
                table.cell(
                    _("To"),
                    HTMLWriter.render_span(state_name[:4], class_=["state_rounded_fill"]),
                    css=[f"{css}{state}"],
                )
            else:
                self._add_state_cells(table=table, nottype=nottype)

            self._add_host_service_cells(
                table=table,
                context=context,
            )
            self._add_plugin_output_cells(
                table=table, context=context, escape_plugin_output=escape_plugin_output
            )

            self._add_toggable_notification_context(
                table=table,
                context=context,
                ident="notification_context_test",
            )

        # This dummy row is needed for not destroying the odd/even row highlighting
        table.row(css=["notification_context hidden"])

    def _render_test_notifications(self) -> None:
        general_test_options = self._get_default_options(
            request.var("host_name"),
            request.var("service_name"),
        )
        advanced_test_options: AdvancedTestOptions = {}
        notify_plugin = {}
        if (
            form_submitted := request.var("test_notification")
        ) or self._test_notification_ongoing():
            general_test_options = self._vs_general_test_options().from_html_vars("general_opts")
            if form_submitted:
                advanced_test_options = self._vs_advanced_test_options().from_html_vars(
                    "advanced_opts"
                )
                notify_plugin = self._vs_notify_plugin().from_html_vars("notify_plugin")

        self._ensure_correct_default_test_options()

        with html.form_context("test_notifications", method="POST"):
            html.help(_("Test a self-defined notification against your rule set."))
            self._vs_test_on_options()
            self._vs_general_test_options().render_input_as_form(
                "general_opts",
                general_test_options,
            )
            self._vs_notify_plugin().render_input("notify_plugin", notify_plugin)
            self._vs_advanced_test_options().render_input("advanced_opts", advanced_test_options)
            html.hidden_fields()
            forms.end()

        html.button(
            varname="_test_host_notifications",
            title=_("Test notifications"),
            cssclass="hot",
            form="form_test_notifications",
        )
        html.javascript("""
        document.getElementById('_test_host_notifications').addEventListener('click', cmk.utils.setButtonLoadingState);
        """)
        html.buttonlink(
            makeuri_contextless(request, [("mode", "test_notifications")], filename="wato.py"),
            _("Reset"),
        )

    def _test_notification_ongoing(self) -> bool:
        return request.has_var("_test_host_notifications") or request.has_var(
            "_test_service_notifications"
        )

    def _infos_from_vars(self) -> tuple[dict[str, Any], str | None, str]:
        general_test_options = self._vs_general_test_options().from_html_vars("general_opts")
        self._vs_general_test_options().validate_value(general_test_options, "general_opts")

        advanced_test_options = self._vs_advanced_test_options().from_html_vars("advanced_opts")
        self._vs_advanced_test_options().validate_value(advanced_test_options, "advanced_opts")

        hostname = general_test_options["on_hostname_hint"]
        context: dict[str, Any] = {
            "HOSTNAME": hostname,
        }

        notify_plugin = self._vs_notify_plugin().from_html_vars("notify_plugin")
        self._vs_notify_plugin().validate_value(notify_plugin, "notify_plugin")
        dispatch = None
        if notify_plugin:
            method, parameter_id = notify_plugin["notify_plugin"]
            dispatch = method
            all_parameters = NotificationParameterConfigFile().load_for_reading()
            method_parameters = all_parameters[method][parameter_id]["parameter_properties"]
            context.update({key: str(value) for key, value in method_parameters.items()})

        simulation_mode = general_test_options["simulation_mode"]
        assert isinstance(simulation_mode, tuple)
        if "status_change" in simulation_mode:
            context["NOTIFICATIONTYPE"] = "PROBLEM"
            context["HOSTPROBLEMID"] = "notify_test_" + str(int(time.time() * 1000000))
            context["PREVIOUSHOSTHARDSTATE"] = host_state_name(
                int(simulation_mode[1]["host_states"][0])
            )
            context["HOSTSTATE"] = host_state_name(int(simulation_mode[1]["host_states"][1]))
            context["HOSTSTATEID"] = str(simulation_mode[1]["host_states"][1])
        else:
            context["NOTIFICATIONTYPE"] = "DOWNTIMESTART"
            context["PREVIOUSHOSTHARDSTATE"] = "UP"
            context["HOSTSTATE"] = "UP"

        notification_nr = str(advanced_test_options["notification_nr"])
        test_type = NotificationTestType.host
        if service_desc := general_test_options.get("on_service_hint"):
            test_type = NotificationTestType.service
            if not service_desc:
                raise MKUserError(None, _("Please provide a service."))

            context["SERVICEDESC"] = service_desc

            context["WHAT"] = "SERVICE"
            context["SERVICENOTIFICATIONNUMBER"] = notification_nr
            context["PREVIOUSSERVICEHARDSTATE"] = (
                "OK"
                if "downtime" in simulation_mode
                else service_state_name(int(simulation_mode[1]["svc_states"][0]))
            )
            context["SERVICESTATE"] = (
                "OK"
                if "downtime" in simulation_mode
                else service_state_name(int(simulation_mode[1]["svc_states"][1]))
            )
            context["SERVICESTATEID"] = (
                "0" if "downtime" in simulation_mode else str(simulation_mode[1]["svc_states"][1])
            )
        else:
            context["WHAT"] = "HOST"
            context["HOSTNOTIFICATIONNUMBER"] = notification_nr

        date_and_time_opts = advanced_test_options["date_and_time"]
        date = date_and_time_opts[0]
        time_ = date_and_time_opts[1]
        context["MICROTIME"] = str(
            int(
                time.mktime(datetime.strptime(f"{date} {time_}", "%Y-%m-%d %H:%M").timetuple())
                * 1000000.0
            )
        )

        plugin_output = general_test_options["plugin_output"]
        if context["WHAT"] == "SERVICE":
            context["SERVICEOUTPUT"] = plugin_output
            context["LONGSERVICEOUTPUT"] = plugin_output
        else:
            context["HOSTOUTPUT"] = plugin_output

        return context, dispatch, test_type

    def _add_missing_host_context(self, context: NotificationContext, event_date: float) -> None:
        """We don't want to transport all possible informations via HTTP vars
        so we enrich the context after fetching all user defined options"""
        hostname = context["HOSTNAME"]
        with sites.prepend_site():
            resp = sites.live().query(
                "GET hosts\n"
                "Columns: custom_variable_names custom_variable_values groups "
                "contact_groups labels host_alias host_address contacts\n"
                f"Filter: host_name = {hostname}\n"
            )

        if len(resp) < 1:
            raise MKUserError(
                None,
                _("Host '%s' is not known in the activated monitoring configuration") % hostname,
            )

        self._set_custom_variables(context, resp, "HOST")
        # we can not use OMD_SITE here because it's used for processing in some
        # cases. See cmk.base.events.complete_raw_context
        context["SITEOFHOST"] = resp[0][0]
        context["HOSTGROUPNAMES"] = ",".join(resp[0][3])
        context["HOSTCONTACTGROUPNAMES"] = ",".join(resp[0][4])
        self._set_labels(context, resp[0][5], "HOST")
        context["HOSTALIAS"] = resp[0][6]
        context["HOSTADDRESS"] = resp[0][7]
        context["CONTACTS"] = ",".join(resp[0][8])
        context["LASTHOSTSTATECHANGE"] = str(int(event_date))

    def _set_custom_variables(
        self,
        context: NotificationContext,
        resp: LivestatusResponse,
        prefix: Literal["HOST", "SERVICE"],
    ) -> None:
        custom_vars = (
            dict(zip(resp[0][1], resp[0][2]))
            if prefix == "HOST"
            else dict(zip(resp[0][0], resp[0][1]))
        )
        for key, value in custom_vars.items():
            # Special case for service level
            if key == "EC_SL":
                context["HOST_SL" if prefix == "HOST" else "SVC_SL"] = value
                continue
            context[f"{prefix}_{key}"] = value
            # TODO in the context of a real notification, some variables are
            # set two times. Why?!
            # e.g. event_match_hosttags would not match with "_" set while
            # user defined custom attributes would not match without.
            # For now we just set both.
            context[f"{prefix}{key}"] = value

    def _add_missing_service_context(self, context: NotificationContext, event_date: float) -> None:
        hostname = context["HOSTNAME"]
        resp = sites.live().query(
            "GET services\n"
            "Columns: custom_variable_names custom_variable_values groups contact_groups check_command labels contacts display_name\n"
            "Filter: host_name = %s\nFilter: service_description = %s"
            % (hostname, context["SERVICEDESC"])
        )
        if len(resp) < 1:
            raise MKUserError(
                None,
                _("Host '%s' is not known in the activated monitoring configuration") % hostname,
            )

        self._set_custom_variables(context, resp, "SERVICE")
        context["SERVICEGROUPNAMES"] = ",".join(resp[0][2])
        context["SERVICECONTACTGROUPNAMES"] = ",".join(resp[0][3])
        context["SERVICECHECKCOMMAND"] = resp[0][4]
        self._set_labels(context, resp[0][5], "SERVICE")
        context["CONTACTS"] = ",".join(resp[0][6])
        context["SERVICEDISPLAYNAME"] = resp[0][7]

        context["LASTSERVICESTATECHANGE"] = str(int(event_date))
        context["SERVICEPROBLEMID"] = "notify_test_" + str(int(event_date * 1000000))

    def _set_labels(
        self,
        context: NotificationContext,
        labels: Labels,
        prefix: Literal["HOST", "SERVICE"],
    ) -> None:
        for k, v in labels.items():
            context[f"{prefix}LABEL_" + k] = v

    def _vs_test_on_options(self) -> None:
        html.open_table(class_="test_on")
        html.open_tr()
        html.td(_("Test notifications on"), class_="legend")
        html.open_td(class_="test_type")
        html.jsbutton(
            varname=(varname := "test_on_host"),
            text="Host",
            onclick=f'cmk.wato.toggle_test_notification_visibility("{varname}", "test_on_service", true)',
            cssclass=f"{varname} active",
        )
        html.jsbutton(
            varname=(varname := "test_on_service"),
            text="Service",
            onclick=f'cmk.wato.toggle_test_notification_visibility("{varname}", "test_on_host")',
            cssclass=varname,
        )
        html.close_td()
        html.close_tr()
        html.close_table()

    def _notification_script_choices_with_parameters(
        self,
    ) -> list[tuple[str, str, DropdownChoice[None]]]:
        return_choices: list[tuple[str, str, DropdownChoice[None]]] = []
        all_parameters = NotificationParameterConfigFile().load_for_reading()
        for script_name, title in notification_script_choices():
            choices = []
            if script_name in all_parameters:
                for parameter_id in all_parameters[script_name]:
                    choices.append(
                        (
                            parameter_id,
                            all_parameters[script_name][parameter_id]["general"]["description"],
                        )
                    )

            vs: DropdownChoice[None] = DropdownChoice(
                title=_("Notification parameter"),
                choices=choices,
                empty_text=_(
                    "There are no parameters defined for this method yet. Please "
                    '<a href="wato.py?mode=notification_parameters&method=%s">create</a> '
                    "at least one first."
                )
                % script_name,
            )

            return_choices.append((script_name, title, vs))
        return return_choices

    def _vs_general_test_options(self) -> Dictionary:
        return Dictionary(
            elements=[
                (
                    # we use the already existing logic for the host aware
                    # service selection. It needs "_hostname_hint" as suffix
                    "on_hostname_hint",
                    MonitoredHostname(
                        title=_("Host"),
                        strict="True",
                        help=_(
                            "Host properties, such as labels or contact groups, are inherited.",
                        ),
                    ),
                ),
                (
                    # we use the already existing logic for the host aware
                    # service selection. It needs "_service_hint" as suffix
                    "on_service_hint",
                    MonitoredServiceDescription(
                        title=_("Service"),
                        autocompleter=ContextAutocompleterConfig(
                            ident=MonitoredServiceDescription.ident,
                            show_independent_of_context=True,
                            strict=True,
                            dynamic_params_callback_name="host_hinted_autocompleter",
                        ),
                    ),
                ),
                (
                    "simulation_mode",
                    CascadingDropdown(
                        title=_("Simulate"),
                        choices=[
                            (
                                "downtime",
                                _("Start of downtime"),
                                FixedValue(
                                    value="DOWNTIME",
                                    totext="",
                                ),
                            ),
                            (
                                "status_change",
                                _("Status change"),
                                Dictionary(
                                    elements=[
                                        (
                                            "svc_states",
                                            Tuple(
                                                orientation="horizontal",
                                                title_br=False,
                                                elements=[
                                                    MonitoringState(
                                                        label=_("From"), default_value=0
                                                    ),
                                                    MonitoringState(label=_("to"), default_value=1),
                                                ],
                                            ),
                                        ),
                                        (
                                            "host_states",
                                            Tuple(
                                                orientation="horizontal",
                                                title_br=False,
                                                elements=[
                                                    HostState(label=_("From"), default_value=0),
                                                    HostState(label=_("to"), default_value=1),
                                                ],
                                            ),
                                        ),
                                    ],
                                    columns=2,
                                    optional_keys=[],
                                ),
                            ),
                        ],
                        default_value="status_change",
                    ),
                ),
                (
                    "plugin_output",
                    TextInput(
                        title=_("Plug-in output"),
                        placeholder=_("This is a notification test"),
                        size=46,
                    ),
                ),
            ],
            optional_keys=[],
            validate=_validate_general_opts,  # type: ignore[arg-type]
        )

    def _vs_notify_plugin(self) -> Dictionary:
        return Dictionary(
            elements=[
                (
                    "notify_plugin",
                    CascadingDropdown(
                        label=_("Notification method and parameter"),
                        title=_("Trigger notification for a specific method"),
                        choices=self._notification_script_choices_with_parameters,
                        default_value=("mail", None),
                        orientation="horizontal",
                    ),
                ),
            ],
        )

    def _vs_advanced_test_options(self) -> Foldable[AdvancedTestOptions]:
        return Foldable(
            valuespec=Dictionary(  # type: ignore[arg-type]
                title=_("Advanced condition simulation"),
                elements=[
                    (
                        "date_and_time",
                        Tuple(
                            orientation="horizontal",
                            title_br=False,
                            elements=[
                                DatePicker(
                                    label=_("Event date and time"),
                                    default_value=time.strftime("%Y-%m-%d"),
                                ),
                                TimePicker(default_value=time.strftime("%H:%M")),
                                TextInput(
                                    title=timezone_utc_offset_str()
                                    + " "
                                    + _("Server time (currently: %s)")
                                    % time.strftime("%m/%d/%Y %H:%M", time.localtime()),
                                    cssclass="server_time",
                                ),
                            ],
                        ),
                    ),
                    (
                        "notification_nr",
                        Integer(label="Notification number", default_value=1),
                    ),
                ],
                optional_keys=[],
            )
        )

    def _get_default_options(self, hostname: str | None, servicename: str | None) -> dict[str, str]:
        if hostname and servicename:
            return {"on_hostname_hint": hostname, "on_service_hint": servicename}
        if hostname:
            return {"on_hostname_hint": hostname}
        return {}

    def _ensure_correct_default_test_options(self) -> None:
        test_type = request.var("test_type")
        if (
            request.has_var("_test_service_notifications")
            or test_type == NotificationTestType.service
        ):
            html.final_javascript(
                'cmk.wato.toggle_test_notification_visibility("test_on_service", "test_on_host");'
            )
        elif request.has_var("_test_host_notifications") or test_type == NotificationTestType.host:
            html.final_javascript(
                'cmk.wato.toggle_test_notification_visibility("test_on_service", "test_on_host", true);'
            )
        else:
            html.final_javascript(
                'cmk.wato.toggle_test_notification_visibility("test_on_host", "test_on_service", true);'
            )

    def _save_test_notification_display_options(self) -> None:
        user.save_file(
            "test_notification_display_options",
            {
                "show_user_rules": self._show_user_rules,
            },
        )


def _get_resulting_notifications_count(
    analyse_resulting_notifications: list[NotifyPluginInfo],
) -> int:
    if not analyse_resulting_notifications:
        return 0

    method_dict: dict[str, list[str]] = {}
    for match in analyse_resulting_notifications:
        method = match[1]
        method_dict.setdefault(method, [])

        for contact in match[0].split(","):
            if contact in method_dict[method]:
                continue
            method_dict[method].append(contact)

    return sum(len(value) for value in method_dict.values())


class GeneralTestOptions(TypedDict):
    on_hostname_hint: str
    on_service_hint: str
    simulation_mode: tuple[str, dict[str, list[int]]]
    plugin_output: str


def _validate_general_opts(general_test_options: GeneralTestOptions, varprefix: str) -> None:
    if not general_test_options["on_hostname_hint"]:
        raise MKUserError(
            f"{varprefix}_p_on_hostname_hint",
            _("Please provide a host name to test with."),
        )

    if (
        request.has_var("_test_service_notifications")
        and not general_test_options["on_service_hint"]
    ):
        raise MKUserError(
            f"{varprefix}_p_on_service_hint",
            _("If you want to test service notifications, please provide a service to test with."),
        )


class ABCUserNotificationsMode(ABCNotificationsMode):
    def __init__(self) -> None:
        super().__init__()
        self._start_async_repl = False

    def _from_vars(self) -> None:
        self._users = userdb.load_users(
            lock=transactions.is_transaction() or request.has_var("_move")
        )

        try:
            user_spec = self._users[self._user_id()]
        except KeyError:
            raise MKUserError(None, _("The requested user does not exist"))

        self._rules = user_spec.setdefault("notification_rules", [])

    @abc.abstractmethod
    def _user_id(self) -> UserId:
        raise NotImplementedError()

    def title(self) -> str:
        return _("Custom notification table for user %s") % self._user_id()

    def action(self, config: Config) -> ActionResult:
        if not transactions.check_transaction():
            return redirect(self.mode_url(user=self._user_id()))

        now = datetime.now()
        if request.has_var("_delete"):
            nr = request.get_integer_input_mandatory("_delete")
            del self._rules[nr]
            userdb.save_users(
                self._users,
                userdb.get_user_attributes(config.wato_user_attrs),
                config.user_connections,
                now=now,
                pprint_value=config.wato_pprint_config,
                call_users_saved_hook=True,
            )
            self._add_change(
                action_name="notification-delete-user-rule",
                text=_("Deleted notification rule %d of user %s") % (nr, self._user_id()),
                use_git=config.wato_use_git,
                site_configs=config.sites,
            )

        elif request.has_var("_move"):
            from_pos = request.get_integer_input_mandatory("_move")
            to_pos = request.get_integer_input_mandatory("_index")
            rule = self._rules[from_pos]
            del self._rules[from_pos]  # make to_pos now match!
            self._rules[to_pos:to_pos] = [rule]
            userdb.save_users(
                self._users,
                userdb.get_user_attributes(config.wato_user_attrs),
                config.user_connections,
                now=now,
                pprint_value=config.wato_pprint_config,
                call_users_saved_hook=True,
            )

            self._add_change(
                action_name="notification-move-user-rule",
                text=_("Changed position of notification rule %d of user %s")
                % (from_pos, self._user_id()),
                use_git=config.wato_use_git,
                site_configs=config.sites,
            )

        return redirect(self.mode_url(user=self._user_id()))

    def page(self, config: Config) -> None:
        if self._start_async_repl:
            user_profile_async_replication_dialog(
                sites=_get_notification_sync_sites(config.sites),
                back_url=ModePersonalUserNotifications.mode_url(),
            )
            html.h3(_("Notification Rules"))

        self._render_notification_rules(
            rules=self._rules,
            config=config,
            userid=self._user_id(),
            profilemode=isinstance(self, ModePersonalUserNotifications),
        )


def _get_notification_sync_sites(site_configs: SiteConfigurations) -> list[SiteId]:
    return sorted(
        site_id
        for site_id in distributed_setup_remote_sites(site_configs)
        if not site_is_local(site_configs[SiteId(site_id)])
    )


class ModeUserNotifications(ABCUserNotificationsMode):
    @classmethod
    def name(cls) -> str:
        return "user_notifications"

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return ["users"]

    @classmethod
    def parent_mode(cls) -> type[WatoMode] | None:
        return ModeEditUser

    @overload
    @classmethod
    def mode_url(cls, *, user: str) -> str: ...

    @overload
    @classmethod
    def mode_url(cls, **kwargs: str) -> str: ...

    @classmethod
    def mode_url(cls, **kwargs: str) -> str:
        return super().mode_url(**kwargs)

    def _breadcrumb_url(self) -> str:
        return self.mode_url(user=self._user_id())

    def _user_id(self) -> UserId:
        return request.get_validated_type_input_mandatory(UserId, "user")

    def page_menu(self, config: Config, breadcrumb: Breadcrumb) -> PageMenu:
        menu = PageMenu(
            dropdowns=[
                PageMenuDropdown(
                    name="notification_rules",
                    title=_("Notification rules"),
                    topics=[
                        PageMenuTopic(
                            title=_("Add new"),
                            entries=[
                                PageMenuEntry(
                                    title=_("Add notification rule"),
                                    icon_name=StaticIcon(IconNames.new),
                                    item=make_simple_link(
                                        folder_preserving_link(
                                            [
                                                ("mode", "user_notification_rule"),
                                                ("user", self._user_id()),
                                            ]
                                        )
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
                            entries=list(self._page_menu_entries_related()),
                        ),
                    ],
                ),
            ],
            breadcrumb=breadcrumb,
            inpage_search=PageMenuSearch(),
        )
        return menu

    def _page_menu_entries_related(self) -> Iterator[PageMenuEntry]:
        yield PageMenuEntry(
            title=_("Users"),
            icon_name=StaticIcon(IconNames.users),
            item=make_simple_link(folder_preserving_link([("mode", "users")])),
        )


class ModePersonalUserNotifications(ABCUserNotificationsMode):
    @classmethod
    def name(cls) -> str:
        return "user_notifications_p"

    @staticmethod
    def static_permissions() -> None:
        return None

    def __init__(self) -> None:
        super().__init__()
        user.need_permission("general.edit_notifications")

    def main_menu(self) -> MainMenu:
        return main_menu_registry.menu_user()

    def page_menu(self, config: Config, breadcrumb: Breadcrumb) -> PageMenu:
        return PageMenu(
            dropdowns=[
                PageMenuDropdown(
                    name="rules",
                    title=_("Rules"),
                    topics=[
                        PageMenuTopic(
                            title=_("Personal rules"),
                            entries=[
                                PageMenuEntry(
                                    title=_("Add rule"),
                                    icon_name=StaticIcon(IconNames.new),
                                    item=make_simple_link(
                                        folder_preserving_link([("mode", "notification_rule_p")])
                                    ),
                                    is_shortcut=True,
                                    is_suggested=True,
                                ),
                            ],
                        )
                    ],
                ),
                page_menu_dropdown_user_related("user_notifications_p"),
            ],
            breadcrumb=breadcrumb,
            inpage_search=PageMenuSearch(),
        )

    def _user_id(self) -> UserId:
        if user.id is None:
            raise MKUserError("user", _("User ID must not be None"))
        return user.id

    def _add_change(
        self,
        *,
        action_name: str,
        text: str,
        use_git: bool,
        site_configs: SiteConfigurations,
    ) -> None:
        if has_distributed_setup_remote_sites(site_configs):
            self._start_async_repl = True
            _audit_log.log_audit(
                action=action_name,
                message=text,
                user_id=user.id,
                use_git=use_git,
            )
        else:
            super()._add_change(
                action_name=action_name,
                text=text,
                use_git=use_git,
                site_configs=site_configs,
            )

    def title(self) -> str:
        return _("Your personal notification rules")


class ABCEditNotificationRuleMode(ABCNotificationsMode):
    def __init__(self) -> None:
        super().__init__()
        self._start_async_repl = False

    @abc.abstractmethod
    def _load_rules(self) -> list[EventRule]:
        raise NotImplementedError()

    @abc.abstractmethod
    def _save_rules(
        self,
        rules: list[EventRule],
        user_attributes: Sequence[tuple[str, UserAttribute]],
        pprint_value: bool,
    ) -> None:
        raise NotImplementedError()

    @abc.abstractmethod
    def _user_id(self) -> UserId | None:
        raise NotImplementedError()

    @abc.abstractmethod
    def _back_mode(self) -> ActionResult:
        raise NotImplementedError()

    @abc.abstractmethod
    def title(self) -> str:
        raise NotImplementedError()

    @abc.abstractmethod
    def _log_text(self, edit_nr: int) -> str:
        raise NotImplementedError()

    def _rule_from_valuespec(self, rule: EventRule) -> EventRule:
        """Optional method to update the rule after editing with the valuespec"""
        return rule

    def _from_vars(self) -> None:
        self._edit_nr = request.get_integer_input_mandatory("edit", -1)
        self._clone_nr = request.get_integer_input_mandatory("clone", -1)
        self._new = self._edit_nr < 0

        self._rules = self._load_rules()

        if self._new:
            if self._clone_nr >= 0 and not request.var("_clear"):
                try:
                    self._rule = deepcopy(self._rules[self._clone_nr])
                    self._rule["rule_id"] = new_notification_rule_id()
                except IndexError:
                    raise MKUserError(None, _("This %s does not exist.") % "notification rule")
            else:
                # For user notifications, we still need the old way to load the
                # default rule. Parameters are stored within the rule
                # (contacts.mk) so no need for a parameter ID here.
                self._rule = self._get_default_notification_rule()  # type: ignore[assignment]
        else:
            try:
                self._rule = self._rules[self._edit_nr]
            except IndexError:
                raise MKUserError(None, _("This %s does not exist.") % "notification rule")

    def _get_default_notification_rule(self) -> EventRule | dict[str, object]:
        return get_default_notification_rule()

    def _valuespec(self, config: Config) -> Dictionary:
        return self._vs_notification_rule(
            self._user_id(),
            config.sites,
            config.mkeventd_service_levels,
        )

    def _vs_notification_rule(
        self,
        userid: UserId | None,
        sites: SiteConfigurations,
        service_levels: Sequence[tuple[int, str]],
    ) -> Dictionary:
        if userid:
            contact_headers: list[tuple[str, list[str]] | tuple[str, str, list[str]]] = []
            section_contacts = []
            section_override: list[DictionaryEntry] = []
        else:
            contact_headers = [
                (
                    _("Contact selection"),
                    [
                        "contact_all",
                        "contact_all_with_email",
                        "contact_object",
                        "contact_users",
                        "contact_groups",
                        "contact_emails",
                        "contact_match_macros",
                        "contact_match_groups",
                    ],
                ),
            ]
            section_contacts = [
                # Contact selection
                (
                    "contact_object",
                    Checkbox(
                        title=_("All contacts of the notified object"),
                        label=_("Notify all contacts of the notified host or service."),
                        default_value=True,
                    ),
                ),
                (
                    "contact_all",
                    Checkbox(
                        title=_("All users"),
                        label=_("Notify all users"),
                    ),
                ),
                (
                    "contact_all_with_email",
                    Checkbox(
                        title=_("All users with an email address"),
                        label=_(
                            "Notify all users that have configured an email address in their profile"
                        ),
                    ),
                ),
                (
                    "contact_users",
                    ListOf(
                        valuespec=userdb.UserSelection(only_contacts=False),
                        title=_("The following users"),
                        help=_(
                            "Enter a list of user IDs to be notified here. These users need to be members "
                            "of at least one contact group in order to be notified."
                        ),
                        movable=False,
                        add_label=_("Add user"),
                    ),
                ),
                (
                    "contact_groups",
                    ListOf(
                        valuespec=ContactGroupSelection(),
                        title=_("Members of contact groups"),
                        movable=False,
                    ),
                ),
                (
                    "contact_emails",
                    ListOfStrings(
                        valuespec=EmailAddress(size=44),
                        title=_("Explicit email addresses"),
                        orientation="vertical",
                    ),
                ),
                (
                    "contact_match_macros",
                    ListOf(
                        valuespec=Tuple(
                            elements=[
                                TextInput(
                                    title=_("Name of the macro"),
                                    help=_(
                                        "As configured in the users settings. Do not add a leading underscore."
                                    ),
                                    allow_empty=False,
                                ),
                                RegExp(
                                    title=_("Required match (regular expression)"),
                                    help=_("This expression must match the value of the variable"),
                                    allow_empty=False,
                                    mode=RegExp.complete,
                                ),
                            ]
                        ),
                        title=_("Restrict by custom macros"),
                        help=_(
                            "Here you can <i>restrict</i> the list of contacts that has been "
                            "built up by the previous options to those who have certain values "
                            "in certain custom macros. If you add more than one macro here then "
                            "<i>all</i> macros must match. The matches are regular expressions "
                            "that must fully match the value of the macro."
                        ),
                        add_label=_("Add condition"),
                    ),
                ),
                (
                    "contact_match_groups",
                    ListOf(
                        valuespec=ContactGroupSelection(),
                        title=_("Restrict by contact groups"),
                        help=_(
                            "Here you can <i>restrict</i> the list of contacts that has been "
                            "built up by the previous options to those that are members of "
                            "selected contact groups. If you select more than one contact group here then "
                            "the user must be member of <i>all</i> these groups."
                        ),
                        add_label=_("Add Group"),
                        movable=False,
                    ),
                ),
            ]
            section_override = [
                (
                    "allow_disable",
                    Checkbox(
                        title=_("Overriding by users"),
                        help=_(
                            "If you uncheck this option then users are not allowed to deactive notifications "
                            "that are created by this rule."
                        ),
                        label=_("allow users to deactivate this notification"),
                        default_value=True,
                    ),
                ),
            ]

        bulk_options: list[DictionaryEntry] = [
            (
                "count",
                Integer(
                    title=_("Maximum bulk size"),
                    label=_("Build bulks up to"),
                    unit=_("Notifications"),
                    help=_(
                        "At most that many notifications are kept back to build bulks. A value of 1 essentially turns off the bulk notification."
                    ),
                    default_value=1000,
                    minvalue=1,
                ),
            ),
            (
                "groupby",
                self._vs_notification_bulkby(),
            ),
            (
                "groupby_custom",
                ListOfStrings(
                    valuespec=ID(),
                    orientation="horizontal",
                    title=_(
                        "Create separate bulk notifications for different values of the following custom macros."
                    ),
                    help=_(
                        "If you enter the names of host/service-custom macros here then for each different combination of values of those macros a separate bulk will be created. Service macros match first, if no service macro is found, the host macros are searched. This can be used in combination with the grouping by folder, host etc. Omit any leading underscore. <b>Note</b>: If you are using Nagios as a core you need to make sure that the values of the required macros are "
                        "present in the notification context. This is done in <tt>check_mk_templates.cfg</tt>. If you "
                        "macro is <tt>_FOO</tt> then you need to add the variables <tt>NOTIFY_HOST_FOO</tt> and "
                        "<tt>NOTIFY_SERVICE_FOO</tt>."
                    ),
                ),
            ),
            (
                "bulk_subject",
                TextInput(
                    title=_("Subject for bulk notifications"),
                    help=_(
                        "Customize the subject for bulk notifications and overwrite "
                        "default subject <tt>Check_MK: $COUNT_NOTIFICATIONS$ notifications for HOST</tt>"
                        " resp. <tt>Check_MK: $COUNT_NOTIFICATIONS$ notifications for $COUNT_HOSTS$ hosts</tt>. "
                        "Both macros <tt>$COUNT_NOTIFICATIONS$</tt> and <tt>$COUNT_HOSTS$</tt> can be used in "
                        "any customized subject. If <tt>$COUNT_NOTIFICATIONS$</tt> is used, the amount of "
                        "notifications will be inserted and if you use <tt>$COUNT_HOSTS$</tt> then the "
                        "amount of hosts will be applied."
                    ),
                    size=80,
                    default_value="Check_MK: $COUNT_NOTIFICATIONS$ notifications for $COUNT_HOSTS$ hosts",
                ),
            ),
        ]

        def make_interval_entry() -> list[DictionaryEntry]:
            return [
                (
                    "interval",
                    Age(
                        title=_("Time horizon"),
                        label=_("Build bulks up to"),
                        help=_("Notifications are kept back to build bulks at most for this time."),
                        default_value=60,
                    ),
                ),
            ]

        timeperiod_entry: list[DictionaryEntry] = [
            (
                "timeperiod",
                TimeperiodSelection(
                    title=_("Only bulk notifications during the following time period"),
                ),
            ),
        ]

        bulk_outside_entry: list[DictionaryEntry] = [
            (
                "bulk_outside",
                Dictionary(
                    title=_("Build bulks also outside of time period"),
                    help=_(
                        "By enabling this option notifications will be bundled outside of the defined time period as well."
                    ),
                    elements=make_interval_entry() + bulk_options,
                    columns=1,
                    optional_keys=["bulk_subject"],
                ),
            ),
        ]

        headers_part1: list[tuple[str, list[str]] | tuple[str, str, list[str]]] = [
            (
                _("Rule properties"),
                ["description", "comment", "disabled", "docu_url", "allow_disable"],
            ),
            (_("Notification method"), ["notify_plugin", "notify_method", "bulk"]),
        ]

        headers_part2: list[tuple[str, list[str]] | tuple[str, str, list[str]]] = [
            (
                _("Conditions"),
                [
                    "match_site",
                    "match_folder",
                    "match_hosttags",
                    "match_hostlabels",
                    "match_hostgroups",
                    "match_hosts",
                    "match_exclude_hosts",
                    "match_servicelabels",
                    "match_servicegroups",
                    "match_exclude_servicegroups",
                    "match_servicegroups_regex",
                    "match_exclude_servicegroups_regex",
                    "match_services",
                    "match_exclude_services",
                    "match_checktype",
                    "match_contacts",
                    "match_contactgroups",
                    "match_plugin_output",
                    "match_timeperiod",
                    "match_escalation",
                    "match_escalation_throttle",
                    "match_sl",
                    "match_host_event",
                    "match_service_event",
                    "match_ec",
                    "match_notification_comment",
                ],
            ),
        ]

        return Dictionary(
            title=_("Rule Properties"),
            elements=rule_option_elements()
            + section_override
            + self._rule_match_conditions(sites, service_levels)
            + section_contacts
            + [
                (
                    "rule_id",
                    UUID(),
                ),
            ]
            + [
                # Notification
                (
                    "notify_plugin",
                    CascadingDropdown(
                        title=_("Notification method"),
                        choices=self._notification_script_choices_with_parameters,
                        default_value=("mail", {}),
                    ),
                ),
                (
                    "bulk",
                    MigrateNotUpdated(
                        valuespec=CascadingDropdown(
                            title="Notification Bulking",
                            orientation="vertical",
                            choices=[
                                (
                                    "always",
                                    _("Always build bulks"),
                                    Dictionary(
                                        help=_(
                                            "Enabling the bulk notifications will collect several subsequent notifications "
                                            "for the same contact into one single notification, which lists of all the "
                                            "actual problems, e.g. in a single email. This cuts down the number of notifications "
                                            "in cases where many (related) problems occur within a short time."
                                        ),
                                        elements=make_interval_entry() + bulk_options,
                                        columns=1,
                                        optional_keys=["bulk_subject"],
                                    ),
                                ),
                                (
                                    "timeperiod",
                                    _("Build bulks during time period"),
                                    Dictionary(
                                        help=_(
                                            "By enabling this option notifications will be bulked only if the "
                                            "specified time period is active. When the time period ends a "
                                            "bulk containing all notifications that appeared during that time "
                                            "will be sent. "
                                            "If bulking should be enabled outside of the time period as well, "
                                            'the option "Also Bulk outside of time period" can be used.'
                                        ),
                                        elements=timeperiod_entry
                                        + bulk_options
                                        + bulk_outside_entry,
                                        columns=1,
                                        optional_keys=["bulk_subject", "bulk_outside"],
                                    ),
                                ),
                            ],
                        ),
                        migrate=self._migrate_bulk,
                    ),
                ),
            ],
            optional_keys=[
                "match_site",
                "match_folder",
                "match_hosttags",
                "match_hostlabels",
                "match_hostgroups",
                "match_hosts",
                "match_exclude_hosts",
                "match_servicelabels",
                "match_servicegroups",
                "match_exclude_servicegroups",
                "match_servicegroups_regex",
                "match_exclude_servicegroups_regex",
                "match_services",
                "match_exclude_services",
                "match_contacts",
                "match_contactgroups",
                "match_plugin_output",
                "match_timeperiod",
                "match_escalation",
                "match_escalation_throttle",
                "match_sl",
                "match_host_event",
                "match_service_event",
                "match_ec",
                "match_notification_comment",
                "match_checktype",
                "bulk",
                "contact_users",
                "contact_groups",
                "contact_emails",
                "contact_match_macros",
                "contact_match_groups",
            ],
            hidden_keys=(["contact_emails"] if edition(paths.omd_root) == Edition.CLOUD else []),
            headers=headers_part1 + contact_headers + headers_part2,
            render="form",
            form_narrow=True,
            validate=self._validate_notification_rule,  # type: ignore[arg-type]
        )

    def _notification_script_choices_with_parameters(self) -> list[tuple[str, str, Alternative]]:
        choices: list[tuple[str, str, Alternative]] = []
        for script_name, title in notification_script_choices():
            if script_name in notification_parameter_registry:
                plugin = notification_parameter_registry[script_name]
                if isinstance(plugin, NotificationParameters):
                    vs = convert_to_legacy_valuespec(plugin.parameter_form(), _)
                else:
                    vs = plugin.spec()
            else:
                vs = ListOfStrings(
                    title=_("Call with the following parameters:"),
                    help=_(
                        "The given parameters are available in scripts as NOTIFY_PARAMETER_1, NOTIFY_PARAMETER_2, etc."
                    ),
                    valuespec=TextInput(size=24),
                    orientation="horizontal",
                )

            vs_alternative = Alternative(
                elements=[
                    vs,
                    FixedValue(
                        value=None,
                        totext=_("previous notifications of this type are cancelled"),
                        title=_("Cancel previous notifications"),
                    ),
                ],
            )

            choices.append((script_name, title, vs_alternative))
        return choices

    def _validate_notification_rule(self, event_rule: EventRule, varprefix: str) -> None:
        if "bulk" in event_rule and event_rule["notify_plugin"][1] is None:
            raise MKUserError(
                varprefix + "_p_bulk_USE",
                _("It does not make sense to add a bulk configuration for cancelling rules."),
            )

        if "bulk" in event_rule or "bulk_period" in event_rule:
            if event_rule["notify_plugin"][0]:
                info = load_notification_scripts()[event_rule["notify_plugin"][0]]
                if not info["bulk"]:
                    raise MKUserError(
                        varprefix + "_p_notify_plugin",
                        _("The notification script %s does not allow building bulks.")
                        % info["title"],
                    )
            else:
                raise MKUserError(
                    varprefix + "_p_notify_plugin",
                    _(
                        "Legacy ASCII emails do not support building bulks. You can either disable bulk notifications or choose another notification plug-in which allows building bulks."
                    ),
                )

    @staticmethod
    def _migrate_bulk(
        v: CascadingDropdownChoiceValue | Mapping[str, Any],
    ) -> CascadingDropdownChoiceValue:
        return v if isinstance(v, tuple) else ("always", v)

    def page_menu(self, config: Config, breadcrumb: Breadcrumb) -> PageMenu:
        return make_simple_form_page_menu(
            _("Notification rule"), breadcrumb, form_name="rule", button_name="_save"
        )

    def action(self, config: Config) -> ActionResult:
        check_csrf_token()

        if not transactions.check_transaction():
            return self._back_mode()

        vs = self._valuespec(config)
        raw_value = vs.from_html_vars("rule")
        vs.validate_value(raw_value, "rule")
        # There is currently no way around this as we don't have typing support from the VS
        self._rule = self._rule_from_valuespec(cast(EventRule, raw_value))

        if self._new and self._clone_nr >= 0:
            self._rules[self._clone_nr : self._clone_nr] = [self._rule]
        elif self._new:
            self._rules[0:0] = [self._rule]
        else:
            self._rules[self._edit_nr] = self._rule

        self._save_rules(
            self._rules, get_user_attributes(config.wato_user_attrs), config.wato_pprint_config
        )

        log_what = "new-notification-rule" if self._new else "edit-notification-rule"
        self._add_change(
            action_name=log_what,
            text=self._log_text(self._edit_nr),
            use_git=config.wato_use_git,
            site_configs=config.sites,
        )
        flash(
            (
                _("New notification rule #%d successfully created!") % (len(self._rules) - 1)
                if self._new
                else _("Notification rule number #%d successfully edited!") % self._edit_nr
            ),
        )

        if back_mode := request.var("back_mode"):
            return redirect(mode_url(back_mode))

        return self._back_mode()

    def page(self, config: Config) -> None:
        if self._start_async_repl:
            user_profile_async_replication_dialog(
                sites=_get_notification_sync_sites(config.sites),
                back_url=ModePersonalUserNotifications.mode_url(),
            )
            return

        with html.form_context("rule", method="POST"):
            vs = self._valuespec(config)
            vs.render_input("rule", dict(self._rule))
            vs.set_focus("rule")
            forms.end()
            html.hidden_fields()


class ModeEditNotificationRule(ABCEditNotificationRuleMode):
    """Edit a global notification rule"""

    @classmethod
    def name(cls) -> str:
        return "notification_rule"

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return ["notifications"]

    @classmethod
    def parent_mode(cls) -> type[WatoMode] | None:
        return ModeNotifications

    def _load_rules(self) -> list[EventRule]:
        if transactions.is_transaction():
            return NotificationRuleConfigFile().load_for_modification()
        return NotificationRuleConfigFile().load_for_reading()

    def _save_rules(
        self,
        rules: list[EventRule],
        user_attributes: Sequence[tuple[str, UserAttribute]],
        pprint_value: bool,
    ) -> None:
        NotificationRuleConfigFile().save(rules, pprint_value=pprint_value)

    def _user_id(self) -> None:
        return None

    def _back_mode(self) -> ActionResult:
        return redirect(mode_url("notifications"))

    def title(self) -> str:
        if self._new:
            return _("Add notification rule")
        return _("Edit notification rule %d") % self._edit_nr

    def _log_text(self, edit_nr: int) -> str:
        if self._new:
            return _("Created new notification rule")
        return _("Changed notification rule %d") % edit_nr


def _log_text(new: bool, user_id: UserId, edit_nr: int) -> str:
    if new:
        return _("Created new notification rule for user %s") % user_id
    return _("Changed notification rule %d of user %s") % (edit_nr, user_id)


def _set_event_rule_attrs(event_rule: EventRule, user_id: UserId) -> EventRule:
    # Force selection of our user
    event_rule["contact_users"] = [user_id]

    # User rules are always allow_disable
    event_rule["allow_disable"] = True
    return event_rule


def _load_rules_ensure_user(user_id: UserId, users: Users) -> list[EventRule]:
    if user_id not in users:
        raise MKUserError(
            None,
            _("The user you are trying to edit notification rules for does not exist."),
        )
    user_spec = users[user_id]
    return user_spec.setdefault("notification_rules", [])


class ModeEditUserNotificationRule(ABCEditNotificationRuleMode):
    """Edit notification rule of a given user"""

    @classmethod
    def name(cls) -> str:
        return "user_notification_rule"

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return ["notifications"]

    @classmethod
    def parent_mode(cls) -> type[WatoMode] | None:
        return ModeUserNotifications

    def _user_id(self) -> UserId:
        return request.get_validated_type_input_mandatory(UserId, "user")

    def _back_mode(self) -> ActionResult:
        return redirect(mode_url("user_notifications", user=self._user_id()))

    def title(self) -> str:
        if self._new:
            return _("Add notification rule for user %s") % self._user_id()
        return _("Edit notification rule %d of user %s") % (
            self._edit_nr,
            self._user_id(),
        )

    def _load_rules(self) -> list[EventRule]:
        self._users = userdb.load_users(lock=transactions.is_transaction())
        return _load_rules_ensure_user(user_id=self._user_id(), users=self._users)

    def _save_rules(
        self,
        rules: list[EventRule],
        user_attributes: Sequence[tuple[str, UserAttribute]],
        pprint_value: bool,
    ) -> None:
        userdb.save_users(
            self._users,
            user_attributes,
            active_config.user_connections,
            now=datetime.now(),
            pprint_value=active_config.wato_pprint_config,
            call_users_saved_hook=True,
        )

    def _rule_from_valuespec(self, rule: EventRule) -> EventRule:
        return _set_event_rule_attrs(event_rule=rule, user_id=self._user_id())

    def _log_text(self, edit_nr: int) -> str:
        return _log_text(self._new, self._user_id(), edit_nr)


class ModeEditPersonalNotificationRule(ABCEditNotificationRuleMode):
    @classmethod
    def name(cls) -> str:
        return "notification_rule_p"

    @classmethod
    def parent_mode(cls) -> type[WatoMode] | None:
        return ModePersonalUserNotifications

    @staticmethod
    def static_permissions() -> None:
        return None

    def __init__(self) -> None:
        super().__init__()
        user.need_permission("general.edit_notifications")

    def _user_id(self) -> UserId:
        if user.id is None:
            raise MKUserError("user", _("User ID must not be None"))
        return user.id

    def _add_change(
        self,
        action_name: str,
        text: str,
        use_git: bool,
        site_configs: SiteConfigurations,
    ) -> None:
        if has_distributed_setup_remote_sites(site_configs):
            self._start_async_repl = True
            _audit_log.log_audit(
                action=action_name,
                message=text,
                user_id=self._user_id(),
                use_git=use_git,
            )
        else:
            super()._add_change(
                action_name=action_name,
                text=text,
                use_git=use_git,
                site_configs=site_configs,
            )

    def _back_mode(self) -> ActionResult:
        if has_distributed_setup_remote_sites(active_config.sites):
            return None
        return redirect(mode_url("user_notifications_p"))

    def title(self) -> str:
        if self._new:
            return _("Create new notification rule")
        return _("Edit notification rule %d") % self._edit_nr

    def _get_default_notification_rule(self) -> EventRule | dict[str, object]:
        # For user notifications, we still need the old way to load the
        # default rule. Parameters are stored within the rule
        # (contacts.mk) so no need for a parameter ID here.
        return {}

    def _load_rules(self) -> list[EventRule]:
        self._users = userdb.load_users(lock=transactions.is_transaction())
        return _load_rules_ensure_user(user_id=self._user_id(), users=self._users)

    def _save_rules(
        self,
        rules: list[EventRule],
        user_attributes: Sequence[tuple[str, UserAttribute]],
        pprint_value: bool,
    ) -> None:
        userdb.save_users(
            self._users,
            user_attributes,
            active_config.user_connections,
            now=datetime.now(),
            pprint_value=active_config.wato_pprint_config,
            call_users_saved_hook=True,
        )

    def _rule_from_valuespec(self, rule: EventRule) -> EventRule:
        return _set_event_rule_attrs(event_rule=rule, user_id=self._user_id())

    def _log_text(self, edit_nr: int) -> str:
        return _log_text(self._new, self._user_id(), edit_nr)


class ModeNotificationParametersOverview(WatoMode):
    @classmethod
    def name(cls) -> str:
        return "notification_parameters_overview"

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return ["notifications"]

    @classmethod
    def parent_mode(cls) -> type[WatoMode] | None:
        return ModeNotifications

    def title(self) -> str:
        return _("Parameters for notification methods")

    def page_menu(self, config: Config, breadcrumb: Breadcrumb) -> PageMenu:
        menu = PageMenu(
            dropdowns=[
                PageMenuDropdown(
                    name="notification_rules",
                    title=_("Parameters for notification methods"),
                    topics=[
                        PageMenuTopic(
                            title=_("Add"),
                            entries=[
                                PageMenuEntry(
                                    title=_("Define parameters for HTML email"),
                                    icon_name=StaticIcon(IconNames.new),
                                    item=make_simple_link(
                                        folder_preserving_link(
                                            [
                                                ("mode", "notification_parameters"),
                                                ("method", "mail"),
                                                ("back_mode", self.name()),
                                                ("rule_folder", ""),
                                            ]
                                        )
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
                    topics=[],  # TODO: add related topics here
                ),
            ],
            breadcrumb=breadcrumb,
            inpage_search=PageMenuSearch(),
        )
        menu.add_doc_reference(_("Notifications"), DocReference.NOTIFICATIONS)
        return menu

    def page(self, config: Config) -> None:
        html.vue_component(
            component_name="cmk-notification-parameters-overview",
            data=asdict(self._get_notification_parameters_data()),
        )

    def _get_parameter_rulesets(
        self,
        all_parameters: NotificationParameterSpecs,
    ) -> Generator[Rule]:
        search_term = request.get_str_input("search", "")
        search_term = search_term.lower() if search_term else ""
        match_regex = re.compile(search_term, re.IGNORECASE)
        for script_name, title in notification_script_choices():
            if not match_regex.search(title):
                continue

            method_parameters: dict[NotificationParameterID, NotificationParameterItem] | None = (
                all_parameters.get(script_name)
            )
            yield Rule(
                i18n=title,
                count="0" if method_parameters is None else f"{len(method_parameters)}",
                link=makeuri(
                    request,
                    [
                        ("mode", "notification_parameters"),
                        ("method", script_name),
                        ("back_mode", self.name()),
                    ],
                ),
            )

    def _get_notification_parameters_data(self) -> NotificationParametersOverview:
        all_parameters = NotificationParameterConfigFile().load_for_reading()
        filtered_parameters = list(self._get_parameter_rulesets(all_parameters))
        return NotificationParametersOverview(
            parameters=(
                [
                    RuleSection(
                        i18n=_("Parameters for"),
                        topics=[RuleTopic(i18n=None, rules=filtered_parameters)],
                    )
                ]
                if filtered_parameters
                else []
            ),
            i18n={
                "no_parameter_match": _(
                    "Found no matching parameters. Please try another search term."
                )
            },
        )


class ABCNotificationParameterMode(WatoMode):
    @classmethod
    def name(cls) -> str:
        return "notification_parameter"

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return ["notifications"]

    def title(self) -> str:
        raise NotImplementedError()

    def _back_mode(self) -> ActionResult:
        raise NotImplementedError()

    def _load_parameters(self) -> NotificationParameterSpecs:
        if transactions.is_transaction():
            return NotificationParameterConfigFile().load_for_modification()
        return NotificationParameterConfigFile().load_for_reading()

    def _save_parameters(
        self,
        parameters: NotificationParameterSpecs,
        pprint_value: bool,
    ) -> None:
        NotificationParameterConfigFile().save(parameters, pprint_value=pprint_value)

    def _add_change(
        self, *, action_name: str, text: str, use_git: bool, site_configs: SiteConfigurations
    ) -> None:
        _changes.add_change(
            action_name=action_name,
            text=text,
            user_id=user.id,
            need_restart=False,
            use_git=use_git,
        )

    def _log_text(self, edit_nr: int) -> str:
        raise NotImplementedError()

    def _from_vars(self) -> None:
        self._edit_nr = request.get_integer_input_mandatory("edit", -1)
        self._edit_parameter = request.get_str_input_mandatory("parameter", "")
        clone_id = request.get_str_input_mandatory("clone", "")
        self._clone_id = NotificationParameterID(clone_id)

        self._parameters = self._load_parameters()
        method_parameters: dict[NotificationParameterID, NotificationParameterItem]
        self._new = (
            not (method_parameters := self._parameters.get(self._method(), {}))
            or self._edit_parameter not in method_parameters
        )

        if self._new:
            if self._clone_id and not request.var("_clear"):
                try:
                    self._parameter = deepcopy(method_parameters[self._clone_id])
                    self._parameter["general"]["description"] = unique_clone_increment_suggestion(
                        self._parameter["general"]["description"],
                        [
                            param["general"]["description"]
                            for paramId, param in method_parameters.items()
                        ],
                        "_clone",
                    )
                except KeyError:
                    raise MKUserError(None, _("This %s does not exist.") % "notification parameter")
            else:
                self._parameter = NotificationParameterItem(
                    general=NotificationParameterGeneralInfos(
                        description="",
                        comment="",
                        docu_url="",
                    ),
                    parameter_properties=DEFAULT_VALUE,  # type: ignore[typeddict-item]  # can not import in cmk.utils.notify_types
                )
        else:
            try:
                self._parameter = method_parameters[NotificationParameterID(self._edit_parameter)]
            except IndexError:
                raise MKUserError(None, _("This %s does not exist.") % "notification parameter")

    def _spec(self) -> ValueSpec[Any]:
        try:
            plugin = notification_parameter_registry[self._method()]
        except KeyError:
            if any(
                self._method() == script_name
                for script_name, _title in notification_script_choices()
            ):
                return convert_to_legacy_valuespec(
                    notification_parameter_registry.parameter_called(), _
                )
            raise MKUserError(
                None,
                _("No notification parameters for method '%s' found") % self._method(),
            )

        if isinstance(plugin, NotificationParameters):
            return convert_to_legacy_valuespec(plugin.parameter_form(), _)
        return plugin.spec()

    def page_menu(self, config: Config, breadcrumb: Breadcrumb) -> PageMenu:
        return make_simple_form_page_menu(
            _("Notification parameter"),
            breadcrumb,
            form_name="parameter",
            button_name="_save",
        )

    def action(self, config: Config) -> ActionResult:
        check_csrf_token()

        self._parameters = self._load_parameters()
        if (method_parameters := self._parameters.get(self._method())) is None:
            return redirect(mode_url("notification_parameters", method=self._method()))

        method_parameter_list = list(method_parameters.items())
        if request.has_var("_delete"):
            parameter_id = request.get_validated_type_input_mandatory(
                NotificationParameterID, "_delete"
            )
            rules = NotificationRuleConfigFile().load_for_reading()

            if get_rules_related_to_parameter(rules, parameter_id):
                return redirect(
                    mode_url(
                        "notification_parameters",
                        method=self._method(),
                        _parameter_id_with_related_rules=parameter_id,
                    )
                )

            method_parameters.pop(parameter_id, None)
            self._parameters[self._method()] = method_parameters
            self._save_parameters(self._parameters, config.wato_pprint_config)

            parameter_number = next(
                i for i, v in enumerate(method_parameter_list) if v[0] == parameter_id
            )
            self._add_change(
                action_name="notification-delete-notification-parameter",
                text=_("Deleted notification parameter %d") % parameter_number,
                use_git=config.wato_use_git,
                site_configs=config.sites,
            )

        elif request.has_var("_move"):
            from_pos = request.get_integer_input_mandatory("_move")
            to_pos = request.get_integer_input_mandatory("_index")

            parameter = method_parameter_list[from_pos]
            del method_parameter_list[from_pos]  # make to_pos now match!
            method_parameter_list[to_pos:to_pos] = [parameter]
            method_parameter_dict = dict(method_parameter_list)
            self._parameters[self._method()] = method_parameter_dict
            self._save_parameters(self._parameters, config.wato_pprint_config)

            self._add_change(
                action_name="notification-move-notification-parameter",
                text=_("Changed position of notification parameter %d") % from_pos,
                use_git=config.wato_use_git,
                site_configs=config.sites,
            )

        if back_mode := request.var("back_mode"):
            return redirect(mode_url(back_mode, method=self._method()))

        return redirect(mode_url("notification_parameters", method=self._method()))

    def _vue_field_id(self) -> str:
        return "_vue_edit_notification_parameter"

    def _get_parameter_value_and_origin(
        self,
    ) -> RawFrontendData | RawDiskData:
        if request.has_var(self._vue_field_id()):
            return RawFrontendData(
                json.loads(request.get_str_input_mandatory(self._vue_field_id()))
            )

        return RawDiskData(self._parameter)

    def _method(self) -> str:
        return request.get_str_input_mandatory("method")

    def _method_name(self) -> str:
        try:
            return [
                entry[1] for entry in notification_script_choices() if entry[0] == self._method()
            ][0]
        except IndexError:
            return self._method()


class ModeNotificationParameters(ABCNotificationParameterMode):
    """Show notification parameter for a specific method"""

    @classmethod
    def name(cls) -> str:
        return "notification_parameters"

    @classmethod
    def parent_mode(cls) -> type[WatoMode] | None:
        return ModeNotificationParametersOverview

    def _breadcrumb_url(self) -> str:
        """Ensure the URL is computed correctly when linking from man pages to the topic"""
        return self.mode_url(method=self._method())

    def title(self) -> str:
        return _("Parameters for %s") % self._method_name()

    def _log_text(self, edit_nr: int) -> str:
        if self._new:
            return _("Created new notification parameter")
        return _("Changed notification parameter %d") % edit_nr

    def page_menu(self, config: Config, breadcrumb: Breadcrumb) -> PageMenu:
        return PageMenu(
            dropdowns=[
                PageMenuDropdown(
                    name="parameters",
                    title=_("Notification parameter"),
                    topics=[
                        PageMenuTopic(
                            title=_("Parameter"),
                            entries=[
                                PageMenuEntry(
                                    title=_("Add parameter"),
                                    icon_name=StaticIcon(IconNames.new),
                                    item=make_simple_link(
                                        folder_preserving_link(
                                            [
                                                ("mode", "edit_notification_parameter"),
                                                ("method", self._method()),
                                            ]
                                        )
                                    ),
                                    is_shortcut=True,
                                    is_suggested=True,
                                ),
                            ],
                        )
                    ],
                ),
            ],
            breadcrumb=breadcrumb,
            inpage_search=PageMenuSearch(),
        )

    def page(self, config: Config) -> None:
        if self._method() not in load_notification_scripts():
            raise MKUserError(None, _("Notification method '%s' does not exist") % self._method())

        if parameter_id_with_related_rules := request.var("_parameter_id_with_related_rules"):
            parameter_id = NotificationParameterID(parameter_id_with_related_rules)
            all_rules = NotificationRuleConfigFile().load_for_reading()
            related_rules = get_rules_related_to_parameter(all_rules, parameter_id)
            self._render_related_rule_error(related_rules)

        parameters = self._load_parameters()
        if not (method_parameters := parameters.get(self._method())):
            html.show_message(
                _("You have not created any parameters for this notification method yet.")
            )
            return
        self._render_notification_parameters(method_parameters)

    def _render_related_rule_error(self, related_rules: list[EventRule]) -> None:
        def build_href(query: str) -> str:
            return makeuri(
                request,
                [
                    ("mode", "notifications"),
                    ("search", query),
                    ("filled_in", "inpage_search_form"),
                ],
                filename="wato.py",
            )

        links_to_related_rules = HTML.with_escaping("").join(
            html.render_li(html.render_a(rule["description"], href=build_href(rule["description"])))
            for rule in related_rules
            if rule["description"]
        )

        # If description not available, link to all rules filtered by their method, i.e. "mail".
        if nondescript_rule_count := sum(not bool(rule["description"]) for rule in related_rules):
            links_to_related_rules += html.render_li(
                HTML.with_escaping("").join(
                    (
                        _("%d notification rule(s) ") % nondescript_rule_count,
                        html.render_a(
                            _("without a description were found"),
                            href=build_href(query=self._method()),
                        ),
                    )
                )
            )

        html.show_error(
            _("This notification parameter is used by the following notification rule(s):")
            + html.render_ul(links_to_related_rules)
            + _("Only unused parameters can be deleted.")
        )

    def _render_notification_parameters(
        self,
        parameters: NotificationParameterSpec,
    ) -> None:
        spec = self._spec()
        method_name = self._method_name()
        with table_element(title=_("Parameters"), limit=None, sortable=False) as table:
            for nr, (parameter_id, parameter) in enumerate(parameters.items()):
                table.row()

                table.cell("#", css=["narrow nowrap"])
                html.write_text_permissive(nr)
                table.cell(_("Actions"), css=["buttons"])
                links = self._parameter_links(parameter, parameter_id, nr)
                html.icon_button(
                    links.edit, _("Edit this notification parameter"), StaticIcon(IconNames.edit)
                )
                html.icon_button(
                    links.clone,
                    _("Create a copy of this notification parameter"),
                    StaticIcon(IconNames.clone),
                )
                html.element_dragger_url("tr", base_url=links.drag)
                html.icon_button(
                    links.delete,
                    _("Delete this notification parameter"),
                    StaticIcon(IconNames.delete),
                )

                table.cell(_("Method"), method_name)

                table.cell(_("Description"))
                url = parameter["general"].get("docu_url")
                if url:
                    html.icon_button(
                        url,
                        _("Context information about this parameter"),
                        StaticIcon(IconNames.url),
                        target="_blank",
                    )
                    html.write_text_permissive("&nbsp;")
                html.write_text_permissive(parameter["general"]["description"])

                table.cell(_("Parameter properties"))
                num_properties = len(parameter["parameter_properties"])
                title = _("%d defined parameter properties") % num_properties
                with foldable_container(
                    treename="parameter_{nr}",
                    id_=str(nr),
                    isopen=False,
                    title=title,
                    indent=False,
                ):
                    assert hasattr(spec, "value_to_html")
                    html.write_text_permissive(
                        spec.value_to_html(parameter["parameter_properties"])
                    )

    def _add_change(
        self, *, action_name: str, text: str, use_git: bool, site_configs: SiteConfigurations
    ) -> None:
        _changes.add_change(
            action_name=action_name,
            user_id=user.id,
            text=text,
            need_restart=False,
            use_git=use_git,
        )

    def _parameter_links(
        self,
        parameter: NotificationParameterItem,
        parameter_id: NotificationParameterID,
        nr: int,
    ) -> NotificationRuleLinks:
        listmode = "notification_parameters"
        mode = "edit_notification_parameter"

        additional_vars: HTTPVariables = [
            ("back_mode", "notification_parameters"),
            ("method", self._method()),
        ]

        delete_url = make_confirm_delete_link(
            url=make_action_link(
                [
                    ("mode", listmode),
                    ("_delete", parameter_id),
                ]
                + additional_vars
            ),
            title=_("Delete notification parameter #%d") % nr,
            suffix=parameter["general"].get("description", ""),
        )
        drag_url = make_action_link(
            [
                ("mode", listmode),
                ("_move", str(nr)),
            ]
            + additional_vars
        )
        edit_url = folder_preserving_link(
            [
                ("mode", mode),
                ("parameter", parameter_id),
                ("edit", str(nr)),
            ]
            + additional_vars
        )
        clone_url = folder_preserving_link(
            [
                ("mode", mode),
                ("clone", parameter_id),
            ]
            + additional_vars
        )

        return NotificationRuleLinks(
            delete=delete_url, edit=edit_url, drag=drag_url, clone=clone_url
        )


class ModeEditNotificationParameter(ABCNotificationParameterMode):
    """Edit a notification parameter"""

    @classmethod
    def name(cls) -> str:
        return "edit_notification_parameter"

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return ["notifications"]

    @classmethod
    def parent_mode(cls) -> type[WatoMode] | None:
        return ModeNotificationParameters

    def breadcrumb(self) -> Breadcrumb:
        with request.stashed_vars():
            request.set_var("method", self._method())
            return super().breadcrumb()

    def _back_mode(self) -> ActionResult:
        return redirect(mode_url("notification_parameters", method=self._method()))

    def title(self) -> str:
        if self._new:
            if self._clone_id:
                return _("Clone %s notification parameter") % self._method_name()
            return _("Add %s notification parameter") % self._method_name()
        return _("Edit %s notification parameter #%s") % (
            self._method_name(),
            self._edit_nr,
        )

    def _log_text(self, edit_nr: int) -> str:
        if self._new:
            return _("Created new notification parameter")
        return _("Changed notification parameter #%s") % edit_nr

    def _form_spec(self) -> TransformDataForLegacyFormatOrRecomposeFunction:
        return notification_parameter_registry.form_spec(self._method())

    def action(self, config: Config) -> ActionResult:
        check_csrf_token()

        if not transactions.check_transaction():
            return self._back_mode()

        value = parse_data_from_field_id(
            self._form_spec(),
            self._vue_field_id(),
        )

        self._parameter = cast(NotificationParameterItem, value)

        if self._new and self._clone_id:
            self._parameters[self._method()][new_notification_parameter_id()] = self._parameter
        elif self._new:
            self._parameters.setdefault(self._method(), {})
            self._parameters[self._method()][new_notification_parameter_id()] = self._parameter
        else:
            self._parameters[self._method()][NotificationParameterID(self._edit_parameter)] = (
                self._parameter
            )

        self._save_parameters(self._parameters, config.wato_pprint_config)

        log_what = "new-notification-parameter" if self._new else "edit-notification-parameter"
        self._add_change(
            action_name=log_what,
            text=self._log_text(self._edit_nr),
            use_git=config.wato_use_git,
            site_configs=config.sites,
        )

        if back_mode := request.var("back_mode"):
            return redirect(mode_url(back_mode, method=self._method()))

        return self._back_mode()

    def _validate_form_spec(self, data: RawDiskData | RawFrontendData) -> bool:
        return isinstance(data, RawFrontendData) or (
            isinstance(data, RawDiskData) and not self._new
        )

    def page(self, config: Config) -> None:
        value = self._get_parameter_value_and_origin()

        with html.form_context("parameter", method="POST"):
            render_form_spec(
                self._form_spec(),
                self._vue_field_id(),
                value,
                self._validate_form_spec(value),
            )

            forms.end()
            html.hidden_fields()


class ModeEditNotificationRuleQuickSetup(WatoMode):
    @classmethod
    def name(cls) -> str:
        return "notification_rule_quick_setup"

    @classmethod
    def parent_mode(cls) -> type[WatoMode] | None:
        return ModeNotifications

    def _from_vars(self) -> None:
        self._edit_nr = request.get_integer_input_mandatory("edit", -1)
        self._clone_nr = request.get_integer_input_mandatory("clone", -1)
        notifications_rules = list(NotificationRuleConfigFile().load_for_reading())
        if self._clone_nr >= 0 and not request.var("_clear"):
            try:
                rule = deepcopy(notifications_rules[self._clone_nr])
                rule["rule_id"] = new_notification_rule_id()
                notifications_rules.append(rule)
                NotificationRuleConfigFile().save(
                    notifications_rules, pprint_value=active_config.wato_pprint_config
                )
                self._edit_nr = len(notifications_rules) - 1
            except IndexError:
                raise MKUserError(None, _("Notification rule does not exist."))

        self._new = self._edit_nr < 0
        if self._edit_nr >= len(notifications_rules):
            raise MKUserError(None, _("Notification rule does not exist."))
        self._object_id: str | None = (
            None
            if self._new and self._clone_nr < 0
            else notifications_rules[self._edit_nr]["rule_id"]
        )
        quick_setup = quick_setup_registry["notification_rule"]
        self._quick_setup_id = quick_setup.id

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return ["notifications"]

    def title(self) -> str:
        if self._new:
            return _("Add notification rule")
        return _("Edit notification rule %d") % self._edit_nr

    def breadcrumb(self) -> Breadcrumb:
        with request.stashed_vars():
            return super().breadcrumb()

    def page_menu(self, config: Config, breadcrumb: Breadcrumb) -> PageMenu:
        return make_simple_form_page_menu(
            title=_("Notification rule"),
            breadcrumb=breadcrumb,
            add_cancel_link=True,
            cancel_url=mode_url(mode_name=ModeNotifications.name()),
        )

    def page(self, config: Config) -> None:
        html.enable_help_toggle()
        # TODO temp. solution to provide flashed message after quick setup
        if message := request.var("result"):
            # TODO Add notification rule number
            html.javascript(
                "cmk.wato.message(%s, %s, %s)"
                % (
                    json.dumps(message),
                    json.dumps("success"),
                    json.dumps("result"),
                )
            )

        html.vue_component(
            component_name="cmk-quick-setup",
            data={
                "quick_setup_id": self._quick_setup_id,
                "mode": "guided" if self._new and self._clone_nr < 0 else "overview",
                "toggle_enabled": True,
                "object_id": self._object_id,
            },
        )


class MatchItemGeneratorNotificationParameter(ABCMatchItemGenerator):
    def generate_match_items(self, user_permissions: UserPermissions) -> MatchItems:
        for script_name, script_title in notification_script_choices():
            title = _("%s") % script_title
            yield MatchItem(
                title=title,
                topic=_("Notification parameter"),
                url=makeuri_contextless(
                    request,
                    [
                        ("mode", "notification_parameters"),
                        ("method", script_name),
                    ],
                    filename="wato.py",
                ),
                match_texts=[title],
            )

    @staticmethod
    def is_affected_by_change(_change_action_name: str) -> bool:
        return False

    @property
    def is_localization_dependent(self) -> bool:
        return True
