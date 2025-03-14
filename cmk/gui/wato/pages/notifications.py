#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Modes for managing notification configuration"""

import abc
import json
import time
from collections.abc import Collection, Iterator, Mapping
from copy import deepcopy
from datetime import datetime
from typing import Any, Literal, NamedTuple, overload

from livestatus import LivestatusResponse

import cmk.utils.store as store
from cmk.utils.labels import Labels
from cmk.utils.notify import NotificationContext
from cmk.utils.notify_types import EventRule, is_always_bulk, NotifyAnalysisInfo
from cmk.utils.statename import host_state_name, service_state_name
from cmk.utils.version import Edition, edition

import cmk.gui.forms as forms
import cmk.gui.permissions as permissions
import cmk.gui.userdb as userdb
import cmk.gui.view_utils
import cmk.gui.watolib.audit_log as _audit_log
import cmk.gui.watolib.changes as _changes
from cmk.gui import sites
from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.config import active_config
from cmk.gui.exceptions import MKUserError
from cmk.gui.htmllib.foldable_container import foldable_container
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.main_menu import mega_menu_registry
from cmk.gui.mkeventd import syslog_facilities, syslog_priorities
from cmk.gui.page_menu import (
    make_display_options_dropdown,
    make_simple_form_page_menu,
    make_simple_link,
    PageMenu,
    PageMenuDropdown,
    PageMenuEntry,
    PageMenuPopup,
    PageMenuSearch,
    PageMenuTopic,
)
from cmk.gui.site_config import has_wato_slave_sites, site_is_local, wato_slave_sites
from cmk.gui.table import Table, table_element
from cmk.gui.type_defs import ActionResult, PermissionName
from cmk.gui.utils.autocompleter_config import ContextAutocompleterConfig
from cmk.gui.utils.csrf_token import check_csrf_token
from cmk.gui.utils.flashed_messages import flash
from cmk.gui.utils.html import HTML
from cmk.gui.utils.output_funnel import output_funnel
from cmk.gui.utils.time import timezone_utc_offset_str
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.utils.urls import (
    DocReference,
    make_confirm_delete_link,
    makeactionuri,
    makeuri,
)
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
)
from cmk.gui.wato.pages.events import ABCEventsMode
from cmk.gui.wato.pages.user_profile.async_replication import (
    user_profile_async_replication_dialog,
)
from cmk.gui.wato.pages.user_profile.page_menu import page_menu_dropdown_user_related
from cmk.gui.wato.pages.users import ModeEditUser
from cmk.gui.watolib.check_mk_automations import (
    notification_analyse,
    notification_get_bulks,
    notification_replay,
    notification_test,
)
from cmk.gui.watolib.global_settings import load_configuration_settings
from cmk.gui.watolib.hosts_and_folders import folder_preserving_link, make_action_link
from cmk.gui.watolib.mode import mode_url, ModeRegistry, redirect, WatoMode
from cmk.gui.watolib.notifications import (
    load_notification_rules,
    load_user_notification_rules,
    save_notification_rules,
)
from cmk.gui.watolib.sample_config import (
    get_default_notification_rule,
    new_notification_rule_id,
)
from cmk.gui.watolib.timeperiods import TimeperiodSelection
from cmk.gui.watolib.user_scripts import load_notification_scripts
from cmk.gui.watolib.users import notification_script_choices

from .._group_selection import ContactGroupSelection
from .._notification_parameter import notification_parameter_registry


def register(mode_registry: ModeRegistry) -> None:
    mode_registry.register(ModeNotifications)
    mode_registry.register(ModeUserNotifications)
    mode_registry.register(ModePersonalUserNotifications)
    mode_registry.register(ModeEditNotificationRule)
    mode_registry.register(ModeEditUserNotificationRule)
    mode_registry.register(ModeEditPersonalNotificationRule)


class ABCNotificationsMode(ABCEventsMode):
    def __init__(self) -> None:
        super().__init__()

        # Make sure that all dynamic permissions are available
        permissions.load_dynamic_permissions()

    # TODO: Clean this up. Use inheritance
    @classmethod
    def _rule_match_conditions(cls):
        return (
            cls._generic_rule_match_conditions()
            + cls._event_rule_match_conditions(flavour="notify")
            + cls._notification_rule_match_conditions()
        )

    @classmethod
    def _notification_rule_match_conditions(cls):
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
        if edition() is Edition.CSE:  # disabled in CSE
            return []

        def migrate_ec_rule_id_match(val):
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

    def _render_notification_rules(  # pylint: disable=too-many-branches
        self,
        rules,
        userid="",
        show_title=False,
        show_buttons=True,
        analyse=False,
        start_nr=0,
        profilemode=False,
    ):
        if not rules:
            html.show_message(_("You have not created any rules yet."))
            return

        vs_match_conditions = Dictionary(elements=self._rule_match_conditions())

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
                        html.icon("checkmark", _("This rule matches"))
                    elif what == "miss":
                        html.icon("hyphen", _("This rule does not match: %s") % reason)

                table.cell("#", css=["narrow nowrap"])

                if show_buttons and self._actions_allowed(rule):
                    html.write_text(nr)
                    table.cell(_("Actions"), css=["buttons"])
                    links = self._rule_links(rule, nr, profilemode, userid)
                    html.icon_button(links.edit, _("Edit this notification rule"), "edit")
                    html.icon_button(
                        links.clone,
                        _("Create a copy of this notification rule"),
                        "clone",
                    )
                    html.element_dragger_url("tr", base_url=links.drag)
                    html.icon_button(links.delete, _("Delete this notification rule"), "delete")
                else:
                    table.cell("", css=["buttons"])
                    for _x in range(4):
                        html.empty_icon_button()

                table.cell("", css=["narrow"])
                if rule.get("disabled"):
                    html.icon(
                        "cross",
                        _("This rule is currently disabled and will not be applied"),
                    )
                else:
                    html.empty_icon_button()

                notify_method = rule["notify_plugin"]
                # Catch rules with empty notify_plugin key
                # Maybe this should be avoided somewhere else (e.g. rule editor)
                if not notify_method:
                    notify_method = (None, [])
                notify_plugin = notify_method[0]

                table.cell(_("Type"), css=["narrow"])
                if notify_method[1] is None:
                    html.icon(
                        "cross_bg_white",
                        _("Cancel notifications for this plug-in type"),
                    )
                else:
                    html.icon("checkmark", _("Create a notification"))

                table.cell(
                    _("Plug-in"),
                    notify_plugin or _("Plain email"),
                    css=["narrow nowrap"],
                )

                table.cell(_("Bulk"), css=["narrow"])
                if "bulk" in rule or "bulk_period" in rule:
                    html.icon("bulk", _("This rule configures bulk notifications."))

                table.cell(_("Description"))
                url = rule.get("docu_url")
                if url:
                    html.icon_button(
                        url,
                        _("Context information about this rule"),
                        "url",
                        target="_blank",
                    )
                    html.write_text("&nbsp;")
                html.write_text(rule["description"])
                table.cell(_("Contacts"))

                infos = self._rule_infos(rule)
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
                        html.write_text(vs_match_conditions.value_to_html(rule))
                else:
                    html.i(_("(no conditions)"))

    def _add_change(self, log_what, log_text):
        _changes.add_change(log_what, log_text, need_restart=False)

    def _vs_notification_bulkby(self):
        return ListChoice(
            title=_("Create separate notification bulks based on"),
            choices=[
                ("folder", _("Folder")),
                ("host", _("Host")),
                ("service", _("Service description")),
                ("sl", _("Service level")),
                ("check_type", _("Check type")),
                ("state", _("Host/Service state")),
            ]
            + (
                [
                    ("ec_contact", _("Event Console contact")),
                    ("ec_comment", _("Event Console comment")),
                ]
                if edition() is not Edition.CSE  # disabled in CSE
                else []
            ),
            default_value=["host"],
        )

    def _table_title(self, show_title, profilemode, userid):
        if not show_title:
            return ""
        if profilemode:
            return _("Notification rules")
        if userid:
            url = makeuri(request, [("mode", "user_notifications"), ("user", userid)])
            code = html.render_icon_button(url, _("Edit this user's notifications"), "edit")
            return code + _("Notification rules of user %s") % userid
        return _("Global notification rules")

    def _rule_infos(self, rule):
        infos = []
        if rule.get("contact_object"):
            infos.append(_("all contacts of the notified object"))
        if rule.get("contact_all"):
            infos.append(_("all users"))
        if rule.get("contact_all_with_email"):
            infos.append(_("all users with and email address"))
        if rule.get("contact_users"):
            infos.append(_("users: ") + (", ".join(rule["contact_users"])))
        if rule.get("contact_groups"):
            infos.append(_("contact groups: ") + (", ".join(rule["contact_groups"])))
        if rule.get("contact_emails"):
            infos.append(_("email addresses: ") + (", ".join(rule["contact_emails"])))
        return infos

    def _actions_allowed(self, rule):
        # In case a notification plug-in does not exist anymore the permission is completely missing.
        permission_name = "notification_plugin.%s" % rule["notify_plugin"][0]
        return permission_name not in permissions.permission_registry or user.may(permission_name)

    def _rule_links(self, rule, nr, profilemode, userid):
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
            mode = "notification_rule"
        search_vars = []
        if query := request.var("search"):
            search_vars.append(("search", query))

        delete_url = make_confirm_delete_link(
            url=make_action_link(
                [
                    ("mode", listmode),
                    ("user", userid),
                    ("_delete", nr),
                ]
                + search_vars
            ),
            title=_("Delete notification rule #%d") % nr,
            suffix=rule.get("description", ""),
        )
        drag_url = make_action_link(
            [
                ("mode", listmode),
                ("analyse", anavar),
                ("user", userid),
                ("_move", nr),
            ]
            + search_vars
        )
        edit_url = folder_preserving_link(
            [
                ("mode", mode),
                ("edit", nr),
                ("user", userid),
            ]
            + search_vars
        )
        clone_url = folder_preserving_link(
            [
                ("mode", mode),
                ("clone", nr),
                ("user", userid),
            ]
            + search_vars
        )

        return NotificationRuleLinks(
            delete=delete_url, edit=edit_url, drag=drag_url, clone=clone_url
        )


class NotificationRuleLinks(NamedTuple):
    delete: str
    edit: str
    drag: str
    clone: str


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
        self._show_backlog = options.get("show_backlog", False)
        self._show_bulks = options.get("show_bulks", False)

    def title(self) -> str:
        return _("Notification configuration")

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
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
                                    title=_("Add rule"),
                                    icon_name="new",
                                    item=make_simple_link(
                                        folder_preserving_link([("mode", "notification_rule")])
                                    ),
                                    is_shortcut=True,
                                    is_suggested=True,
                                ),
                                PageMenuEntry(
                                    title=_("Test notifications"),
                                    name="test_notifications",
                                    icon_name="analysis",
                                    item=PageMenuPopup(
                                        content=self._render_test_notifications(),
                                        css_classes=(
                                            ["active"] if self._test_notification_ongoing() else []
                                        ),
                                    ),
                                    is_shortcut=True,
                                    is_suggested=True,
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
        menu.add_doc_reference(_("Notifications"), DocReference.NOTIFICATIONS)
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
                            _("Hide user rules") if self._show_user_rules else _("Show user rules")
                        ),
                        icon_name={
                            "icon": "checkbox",
                            "emblem": "disable" if self._show_user_rules else "enable",
                        },
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
                    PageMenuEntry(
                        title=(
                            _("Hide analysis")
                            if self._show_backlog and not request.var("test_notification")
                            else _("Show analysis")
                        ),
                        icon_name={
                            "icon": "analyze",
                            "emblem": "disable" if self._show_backlog else "enable",
                        },
                        item=make_simple_link(
                            makeactionuri(
                                request,
                                transactions,
                                addvars=[
                                    (
                                        "_show_backlog",
                                        "" if self._show_backlog else "1",
                                    ),
                                ],
                                delvars=("test_context", "test_notification"),
                            )
                        ),
                        is_shortcut=True,
                        is_suggested=True,
                    ),
                    PageMenuEntry(
                        title=_("Hide bulks") if self._show_bulks else _("Show bulks"),
                        icon_name={
                            "icon": "bulk",
                            "emblem": "disable" if self._show_bulks else "enable",
                        },
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
                ],
            ),
        )

    def action(self) -> ActionResult:
        check_csrf_token()

        if request.has_var("_show_user"):
            if transactions.check_transaction():
                self._show_user_rules = bool(request.var("_show_user"))
                self._save_notification_display_options()

        elif request.has_var("_show_backlog"):
            if transactions.check_transaction():
                self._show_backlog = bool(request.var("_show_backlog"))
                self._save_notification_display_options()

        elif request.has_var("_show_bulks"):
            if transactions.check_transaction():
                self._show_bulks = bool(request.var("_show_bulks"))
                self._save_notification_display_options()

        elif self._test_notification_ongoing():
            if transactions.check_transaction():
                return redirect(
                    mode_url(
                        "notifications",
                        test_notification="1",
                        test_context=json.dumps(self._context_from_vars()),
                        dispatch=request.var("dispatch", ""),
                    )
                )

        elif request.has_var("_replay"):
            if transactions.check_transaction():
                nr = request.get_integer_input_mandatory("_replay")
                notification_replay(nr)
                flash(_("Replayed notification number %d") % (nr + 1))
                return None

        else:
            self._generic_rule_list_actions(
                self._get_notification_rules(),
                "notification",
                _("notification rule"),
                save_notification_rules,
            )

        if query := request.var("search"):
            return redirect(self.mode_url(search=query, filled_in="inpage_search_form"))

        return redirect(self.mode_url())

    def _test_notification_ongoing(self) -> bool:
        return request.has_var("_test_host_notifications") or request.has_var(
            "_test_service_notifications"
        )

    def _context_from_vars(self) -> dict[str, Any]:
        general_test_options = self._vs_general_test_options().from_html_vars("general_opts")
        self._vs_general_test_options().validate_value(general_test_options, "general_opts")

        advanced_test_options = self._vs_advanced_test_options().from_html_vars("advanced_opts")
        self._vs_advanced_test_options().validate_value(advanced_test_options, "advanced_opts")

        hostname = general_test_options["on_hostname_hint"]
        context: dict[str, Any] = {
            "HOSTNAME": hostname,
        }

        simulation_mode = general_test_options["simulation_mode"]
        assert isinstance(simulation_mode, tuple)
        if "status_change" in simulation_mode:
            context["NOTIFICATIONTYPE"] = "PROBLEM"
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
        if service_desc := general_test_options.get("on_service_hint"):
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

        return context

    def _get_notification_rules(self):
        return load_notification_rules()

    def _save_notification_display_options(self):
        user.save_file(
            "notification_display_options",
            {
                "show_user_rules": self._show_user_rules,
                "show_backlog": self._show_backlog,
                "show_bulks": self._show_bulks,
            },
        )

    def page(self) -> None:
        context, analyse = self._analyse_result_from_request()
        # do not show notification backlog if test notifications was performed
        self._show_backlog = self._show_backlog and not context
        self._show_no_fallback_contact_warning()
        self._show_bulk_notifications()
        self._show_notification_test_overview(context, analyse)
        self._show_notification_test_details(context, analyse)
        self._show_notification_backlog()
        self._show_rules(analyse)

    def _analyse_result_from_request(
        self,
    ) -> tuple[NotificationContext | None, NotifyAnalysisInfo | None]:
        if request.var("analyse"):
            nr = request.get_integer_input_mandatory("analyse")
            return NotificationContext({}), notification_analyse(nr).result
        if request.var("test_notification"):
            try:
                context = json.loads(request.get_str_input_mandatory("test_context"))
            except Exception as e:
                raise MKUserError(None, "Failed to parse context from request.") from e

            self._add_missing_host_context(context)
            if context["WHAT"] == "SERVICE":
                self._add_missing_service_context(context)

            return (
                context,
                notification_test(
                    raw_context=context, dispatch=bool(request.var("dispatch"))
                ).result,
            )
        return None, None

    def _add_missing_host_context(self, context: NotificationContext) -> None:
        """We don't want to transport all possible informations via HTTP vars
        so we enrich the context after fetching all user defined options"""
        hostname = context["HOSTNAME"]
        resp = sites.live().query(
            "GET hosts\n"
            "Columns: custom_variable_names custom_variable_values groups "
            "contact_groups labels host_alias\n"
            f"Filter: host_name = {hostname}\n"
        )
        if len(resp) < 1:
            raise MKUserError(
                None,
                _("Host '%s' is not known in the activated monitoring configuration") % hostname,
            )

        self._set_custom_variables(context, resp, "HOST")
        context["HOSTGROUPNAMES"] = ",".join(resp[0][2])
        context["HOSTCONTACTGROUPNAMES"] = ",".join(resp[0][3])
        self._set_labels(context, resp[0][4], "HOST")
        context["HOSTALIAS"] = resp[0][5]

    def _set_custom_variables(
        self,
        context: NotificationContext,
        resp: LivestatusResponse,
        prefix: Literal["HOST", "SERVICE"],
    ) -> None:
        custom_vars = dict(zip(resp[0][0], resp[0][1]))
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

    def _add_missing_service_context(self, context: NotificationContext) -> None:
        hostname = context["HOSTNAME"]
        resp = sites.live().query(
            "GET services\nColumns: custom_variable_names custom_variable_values groups contact_groups check_command labels\nFilter: host_name = %s\nFilter: service_description = %s"
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

    def _set_labels(
        self,
        context: NotificationContext,
        labels: Labels,
        prefix: Literal["HOST", "SERVICE"],
    ) -> None:
        for k, v in labels.items():
            context[f"{prefix}LABEL_" + k] = v

    def _show_no_fallback_contact_warning(self):
        if not self._fallback_mail_contacts_configured():
            url = "wato.py?mode=edit_configvar&varname=notification_fallback_email"
            html.show_warning(
                _(
                    "<b>Warning</b><br><br>You haven't configured a "
                    '<a href="%s">fallback email address</a> nor enabled receiving fallback emails for '
                    "any user. If your monitoring produces a notification that is not matched by any of your "
                    "notification rules, the notification will not be sent out. To prevent that, please "
                    "configure either the global setting or enable the fallback contact option for at least "
                    "one of your users."
                )
                % url
            )

    def _fallback_mail_contacts_configured(self):
        current_settings = load_configuration_settings()
        if current_settings.get("notification_fallback_email"):
            return True

        for user_spec in userdb.load_users(lock=False).values():
            if user_spec.get("fallback_contact", False):
                return True

        return False

    def _show_bulk_notifications(self):
        if self._show_bulks:
            # Warn if there are unsent bulk notifications
            if not self._render_bulks(only_ripe=False):
                html.show_message(_("Currently there are no unsent notification bulks pending."))
        else:
            # Warn if there are unsent bulk notifications
            self._render_bulks(only_ripe=True)

    def _render_bulks(self, only_ripe) -> bool:  # type: ignore[no-untyped-def]
        bulks = notification_get_bulks(only_ripe).result
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
                    html.icon("warning", _("Age of oldest notification is over maximum age"))
                table.cell(_("Time Period"), str(timeperiod))
                table.cell(_("Max. Count"), str(maxcount), css=["number"])
                table.cell(_("Count"), str(len(uuids)), css=["number"])
                if len(uuids) >= maxcount:
                    html.icon(
                        "warning",
                        _("Number of notifications exceeds maximum allowed number"),
                    )
        return True

    def _show_notification_test_overview(
        self,
        context: NotificationContext | None,
        analyse: NotifyAnalysisInfo | None,
    ) -> None:
        if not context or not analyse:
            return
        html.open_div(class_="matching_message")
        html.icon("toggle_details")
        html.b(_("Matching: "))
        html.write_text(
            _(
                "Each parameter is defined by the first matching rule where that parameter "
                "is set (checked)."
            )
        )
        html.close_div()
        html.open_div(id_="notification_analysis_container")

        html.open_div(class_="state_bar state0")
        html.open_span()
        html.icon("check")
        html.close_span()
        html.close_div()

        html.open_div(class_="message_container")
        html.h2(_("Analysis results"))
        analyse_rules, analyse_resulting_notifications = analyse
        html.write_text(
            _("%s notification rules are matching")
            % len(tuple(entry for entry in analyse_rules if "match" in entry))
        )
        html.br()
        html.write_text(_("%s resulting notifications") % len(analyse_resulting_notifications))
        html.br()
        if request.var("dispatch"):
            html.write_text(_("Notifications have been sent. "))
        html.write_text("View the following tables for more details.")
        html.close_div()
        html.close_div()

    def _show_notification_test_details(
        self,
        context: NotificationContext | None,
        analyse: NotifyAnalysisInfo | None,
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
                "toggle_context",
                onclick="cmk.wato.toggle_container('notification_context_test')",
            )

            if analyse:
                table.cell(css=["buttons"])
                analyse_rules, _analyse_plugins = analyse
                if any("match" in entry for entry in analyse_rules):
                    html.icon("checkmark", _("This notification matches"))
                else:
                    html.icon(
                        "hyphen",
                        _(
                            "This notification does not match. See reasons in global notification rule list."
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
            self._add_plugin_output_cells(table=table, context=context)

            self._add_toggable_notification_context(
                table=table,
                context=context,
                ident="notification_context_test",
            )

        # This dummy row is needed for not destroying the odd/even row highlighting
        table.row(css=["notification_context hidden"])

        if analyse is not None:
            self._show_resulting_notifications(result=analyse)

    def _show_notification_backlog(self):
        """Show recent notifications. We can use them for rule analysis"""
        if not self._show_backlog:
            return

        backlog = store.load_object_from_file(
            cmk.utils.paths.var_dir + "/notify/backlog.mk",
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
                    analyse_url, _("Analyze ruleset with this notification"), "analyze"
                )

                html.icon_button(
                    None,
                    _("Show / hide notification context"),
                    "toggle_context",
                    onclick="cmk.wato.toggle_container('notification_context_%d')" % nr,
                )

                replay_url = makeactionuri(request, transactions, [("_replay", str(nr))])
                html.icon_button(
                    replay_url,
                    _("Replay this notification, send it again!"),
                    "reload_cmk",
                )

                if request.var("analyse") and nr == request.get_integer_input_mandatory("analyse"):
                    html.icon("checkmark", _("You are analysing this notification"))

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
                self._add_plugin_output_cells(table=table, context=context)

                self._add_toggable_notification_context(
                    table=table,
                    context=context,
                    ident=f"notification_context_{nr}",
                )

                # This dummy row is needed for not destroying the odd/even row highlighting
                table.row(css=["notification_context hidden"])

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
            html.icon("downtime", _("Downtime"))
        elif nottype.startswith("ACK"):
            table.cell(_("State"))
            html.icon("ack", _("Acknowledgement"))
        elif nottype.startswith("FLAP"):
            table.cell(_("State"))
            html.icon("flapping", _("Flapping"))
        else:
            table.cell(_("State"), "")

    def _add_host_service_cells(self, table: Table, context: NotificationContext) -> None:
        table.cell(_("Host"), context.get("HOSTNAME", ""))
        table.cell(_("Service"), context.get("SERVICEDESC", ""))

    def _add_plugin_output_cells(self, table: Table, context: NotificationContext) -> None:
        output = context.get("SERVICEOUTPUT", context.get("HOSTOUTPUT", ""))
        table.cell(
            _("Plug-in output"),
            cmk.gui.view_utils.format_plugin_output(
                output, shall_escape=active_config.escape_plugin_output
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

    # TODO: Refactor this
    def _show_rules(self, analyse: NotifyAnalysisInfo | None) -> None:
        start_nr = 0
        rules = self._get_notification_rules()
        self._render_notification_rules(rules, show_title=True, analyse=analyse, start_nr=start_nr)
        start_nr += len(rules)

        if self._show_user_rules:
            for user_id, user_rules in sorted(
                load_user_notification_rules().items(), key=lambda u: u[0]
            ):
                self._render_notification_rules(
                    user_rules,
                    user_id,
                    show_title=True,
                    show_buttons=False,
                    analyse=analyse,
                    start_nr=start_nr,
                )
                start_nr += len(user_rules)

        if request.var("analyse") and analyse is not None:
            self._show_resulting_notifications(result=analyse)

    def _show_resulting_notifications(self, result: NotifyAnalysisInfo) -> None:
        with table_element(table_id="plugins", title=_("Resulting notifications")) as table:
            for contact, plugin, parameters, bulk in result[1]:
                table.row()
                if contact.startswith("mailto:"):
                    contact = contact[7:]  # strip of fake-contact mailto:-prefix
                table.cell(_("Recipient"), contact)
                table.cell(_("Plug-in"), self._vs_notification_scripts().value_to_html(plugin))
                table.cell(_("Plug-in parameters"), ", ".join(parameters))
                table.cell(_("Bulking"))
                if bulk:
                    html.write_text(_("Time horizon") + ": ")
                    if is_always_bulk(bulk):
                        html.write_text(Age().value_to_html(bulk["interval"]))
                    else:
                        html.write_text(Age().value_to_html(0))
                    html.write_text(", %s: %d" % (_("Maximum count"), bulk["count"]))
                    html.write_text(", %s " % (_("group by")))
                    html.write_text(self._vs_notification_bulkby().value_to_html(bulk["groupby"]))

    def _vs_notification_scripts(self):
        return DropdownChoice(
            title=_("Notification Script"),
            choices=notification_script_choices,
            default_value="mail",
        )

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
            validate=_validate_general_opts,
        )

    def _vs_dispatched_option(self) -> Checkbox:
        return Checkbox(
            title=_("Dispatch notification"),
            label=_(
                "Send out HTML/ASCII email notification according "
                "to notification rules (uncheck to avoid spam)"
            ),
            default_value=False,
        )

    def _vs_advanced_test_options(self) -> Foldable:
        return Foldable(
            valuespec=Dictionary(
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

    def _render_test_notifications(self) -> HTML:
        self._ensure_correct_default_test_options()

        with output_funnel.plugged():
            with html.form_context("test_notifications", method="POST"):
                html.help(_("Test a self defined notification against your ruleset."))
                self._vs_test_on_options()
                self._vs_general_test_options().render_input_as_form(
                    "general_opts",
                    self._get_default_options(
                        request.var("host_name"), request.var("service_name")
                    ),
                )
                self._vs_dispatched_option().render_input("dispatch", False)
                self._vs_advanced_test_options().render_input("advanced_opts", "")
                html.hidden_fields()

            html.button(
                varname="_test_host_notifications",
                title=_("Test notifications"),
                cssclass="hot",
                form="form_test_notifications",
            )
            html.buttonlink(makeuri(request, []), _("Cancel"))

            return HTML(output_funnel.drain())

    def _get_default_options(self, hostname: str | None, servicename: str | None) -> dict[str, str]:
        if hostname and servicename:
            return {"on_hostname_hint": hostname, "on_service_hint": servicename}
        if hostname:
            return {"on_hostname_hint": hostname}
        return {}

    def _ensure_correct_default_test_options(self) -> None:
        if request.has_var("_test_service_notifications"):
            html.final_javascript(
                'cmk.wato.toggle_test_notification_visibility("test_on_service", "test_on_host");'
            )
        elif request.has_var("_test_host_notifications"):
            html.final_javascript(
                'cmk.wato.toggle_test_notification_visibility("test_on_service", "test_on_host", true);'
            )
        else:
            html.final_javascript(
                'cmk.wato.toggle_test_notification_visibility("test_on_host", "test_on_service", true);'
            )


def _validate_general_opts(value, varprefix):
    if not value["on_hostname_hint"]:
        raise MKUserError(
            f"{varprefix}_p_on_hostname_hint",
            _("Please provide a hostname to test with."),
        )

    if request.has_var("_test_service_notifications") and not value["on_service_hint"]:
        raise MKUserError(
            f"{varprefix}_p_on_service_hint",
            _("If you want to test service notifications, please provide a service to test with."),
        )


class ABCUserNotificationsMode(ABCNotificationsMode):
    def __init__(self) -> None:
        super().__init__()
        self._start_async_repl = False

    def _from_vars(self):
        self._users = userdb.load_users(
            lock=transactions.is_transaction() or request.has_var("_move")
        )

        try:
            user_spec = self._users[self._user_id()]
        except KeyError:
            raise MKUserError(None, _("The requested user does not exist"))

        self._rules = user_spec.setdefault("notification_rules", [])

    @abc.abstractmethod
    def _user_id(self):
        raise NotImplementedError()

    def title(self) -> str:
        return _("Custom notification table for user %s") % self._user_id()

    def action(self) -> ActionResult:
        if not transactions.check_transaction():
            return redirect(self.mode_url(user=self._user_id()))

        now = datetime.now()
        if request.has_var("_delete"):
            nr = request.get_integer_input_mandatory("_delete")
            del self._rules[nr]
            userdb.save_users(self._users, now)
            self._add_change(
                "notification-delete-user-rule",
                _("Deleted notification rule %d of user %s") % (nr, self._user_id()),
            )

        elif request.has_var("_move"):
            from_pos = request.get_integer_input_mandatory("_move")
            to_pos = request.get_integer_input_mandatory("_index")
            rule = self._rules[from_pos]
            del self._rules[from_pos]  # make to_pos now match!
            self._rules[to_pos:to_pos] = [rule]
            userdb.save_users(self._users, now)

            self._add_change(
                "notification-move-user-rule",
                _("Changed position of notification rule %d of user %s")
                % (from_pos, self._user_id()),
            )

        return redirect(self.mode_url(user=self._user_id()))

    def page(self) -> None:
        if self._start_async_repl:
            user_profile_async_replication_dialog(
                sites=_get_notification_sync_sites(),
                back_url=ModePersonalUserNotifications.mode_url(),
            )
            html.h3(_("Notification Rules"))

        self._render_notification_rules(
            rules=self._rules,
            userid=self._user_id(),
            profilemode=isinstance(self, ModePersonalUserNotifications),
        )


def _get_notification_sync_sites():
    # Astroid 2.x bug prevents us from using NewType https://github.com/PyCQA/pylint/issues/2296
    # pylint: disable=not-an-iterable
    return sorted(site_id for site_id in wato_slave_sites() if not site_is_local(site_id))


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

    # pylint does not understand this overloading
    @overload
    @classmethod
    def mode_url(cls, *, user: str) -> str:  # pylint: disable=arguments-differ,redefined-outer-name
        ...

    @overload
    @classmethod
    def mode_url(cls, **kwargs: str) -> str: ...

    @classmethod
    def mode_url(cls, **kwargs: str) -> str:
        return super().mode_url(**kwargs)

    def _breadcrumb_url(self) -> str:
        return self.mode_url(user=self._user_id())

    def _user_id(self):
        return request.get_str_input("user")

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
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
                                    title=_("Add rule"),
                                    icon_name="new",
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
            icon_name="users",
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

    def main_menu(self):
        return mega_menu_registry.menu_user()

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
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
                                    icon_name="new",
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

    def _user_id(self):
        return user.id

    def _add_change(self, log_what, log_text):
        if has_wato_slave_sites():
            self._start_async_repl = True
            _audit_log.log_audit(log_what, log_text)
        else:
            super()._add_change(log_what, log_text)

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
    def _save_rules(self, rules: list[EventRule]) -> None:
        raise NotImplementedError()

    @abc.abstractmethod
    def _user_id(self):
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

    # TODO: Refactor this
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
                self._rule = get_default_notification_rule()
        else:
            try:
                self._rule = self._rules[self._edit_nr]
            except IndexError:
                raise MKUserError(None, _("This %s does not exist.") % "notification rule")

    def _valuespec(self):
        return self._vs_notification_rule(self._user_id())

    # TODO: Refactor this mess
    def _vs_notification_rule(self, userid=None):
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
                    label=_("Bulk up to"),
                    unit=_("Notifications"),
                    help=_(
                        "At most that many notifications are kept back for bulking. A value of "
                        "1 essentially turns off notification bulking."
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
                        "Create separate notification bulks for different values of the following custom macros"
                    ),
                    help=_(
                        "If you enter the names of host/service-custom macros here "
                        "then for each different combination of values of those "
                        "macros a separate bulk will be created. Service macros "
                        "match first, if no service macro is found, the host macros "
                        "are searched. This can be used in combination with the grouping by folder, host etc. "
                        "Omit any leading underscore. <b>Note</b>: If you are using "
                        "Nagios as a core you need to make sure that the values of the required macros are "
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
                        label=_("Bulk up to"),
                        help=_("Notifications are kept back for bulking at most for this time."),
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
                    title=_("Also bulk outside of time period"),
                    help=_(
                        "By enabling this option notifications will be bulked "
                        "outside of the defined time period as well."
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
            + self._rule_match_conditions()
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
                        title=_("Notification Method"),
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
                                    _("Always bulk"),
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
                                    _("Bulk during time period"),
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
            hidden_keys=["contact_emails"] if edition() == Edition.CSE else [],
            headers=headers_part1 + contact_headers + headers_part2,
            render="form",
            form_narrow=True,
            validate=self._validate_notification_rule,
        )

    def _notification_script_choices_with_parameters(self):
        choices = []
        for script_name, title in notification_script_choices():
            if script_name in notification_parameter_registry:
                vs: Dictionary | ListOfStrings = notification_parameter_registry[script_name]().spec
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

    def _validate_notification_rule(self, rule, varprefix):
        if "bulk" in rule and rule["notify_plugin"][1] is None:
            raise MKUserError(
                varprefix + "_p_bulk_USE",
                _("It does not make sense to add a bulk configuration for cancelling rules."),
            )

        if "bulk" in rule or "bulk_period" in rule:
            if rule["notify_plugin"][0]:
                info = load_notification_scripts()[rule["notify_plugin"][0]]
                if not info["bulk"]:
                    raise MKUserError(
                        varprefix + "_p_notify_plugin",
                        _("The notification script %s does not allow bulking.") % info["title"],
                    )
            else:
                raise MKUserError(
                    varprefix + "_p_notify_plugin",
                    _(
                        "Legacy ASCII emails do not support bulking. You can either disable notification "
                        "bulking or choose another notification plug-in which allows bulking."
                    ),
                )

    @staticmethod
    def _migrate_bulk(
        v: CascadingDropdownChoiceValue | Mapping[str, Any],
    ) -> CascadingDropdownChoiceValue:
        return v if isinstance(v, tuple) else ("always", v)

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        return make_simple_form_page_menu(
            _("Notification rule"), breadcrumb, form_name="rule", button_name="_save"
        )

    def action(self) -> ActionResult:
        check_csrf_token()

        if not transactions.check_transaction():
            if query := request.var("search"):
                return redirect(
                    mode_url("notifications", search=query, filled_in="inpage_search_form")
                )

            return self._back_mode()

        vs = self._valuespec()
        self._rule = self._rule_from_valuespec(vs.from_html_vars("rule"))
        vs.validate_value(self._rule, "rule")

        if self._new and self._clone_nr >= 0:
            self._rules[self._clone_nr : self._clone_nr] = [self._rule]
        elif self._new:
            self._rules[0:0] = [self._rule]
        else:
            self._rules[self._edit_nr] = self._rule

        self._save_rules(self._rules)

        log_what = "new-notification-rule" if self._new else "edit-notification-rule"
        self._add_change(log_what, self._log_text(self._edit_nr))

        if query := request.var("search"):
            return redirect(mode_url("notifications", search=query, filled_in="inpage_search_form"))

        return self._back_mode()

    def page(self) -> None:
        if self._start_async_repl:
            user_profile_async_replication_dialog(
                sites=_get_notification_sync_sites(),
                back_url=ModePersonalUserNotifications.mode_url(),
            )
            return

        with html.form_context("rule", method="POST"):
            vs = self._valuespec()
            vs.render_input("rule", self._rule)
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
        return load_notification_rules(lock=transactions.is_transaction())

    def _save_rules(self, rules: list[EventRule]) -> None:
        save_notification_rules(rules)

    def _user_id(self):
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


class ABCEditUserNotificationRuleMode(ABCEditNotificationRuleMode):
    def _load_rules(self) -> list[EventRule]:
        self._users = userdb.load_users(lock=transactions.is_transaction())
        if self._user_id() not in self._users:
            raise MKUserError(
                None,
                _("The user you are trying to edit notification rules for does not exist."),
            )
        user_spec = self._users[self._user_id()]
        return user_spec.setdefault("notification_rules", [])

    def _save_rules(self, rules: list[EventRule]) -> None:
        userdb.save_users(self._users, datetime.now())

    def _rule_from_valuespec(self, rule: EventRule) -> EventRule:
        # Force selection of our user
        rule["contact_users"] = [self._user_id()]

        # User rules are always allow_disable
        rule["allow_disable"] = True
        return rule

    def _log_text(self, edit_nr: int) -> str:
        if self._new:
            return _("Created new notification rule for user %s") % self._user_id()
        return _("Changed notification rule %d of user %s") % (edit_nr, self._user_id())


class ModeEditUserNotificationRule(ABCEditUserNotificationRuleMode):
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

    def _user_id(self):
        return request.get_str_input_mandatory("user")

    def _back_mode(self) -> ActionResult:
        return redirect(mode_url("user_notifications", user=self._user_id()))

    def title(self) -> str:
        if self._new:
            return _("Add notification rule for user %s") % self._user_id()
        return _("Edit notification rule %d of user %s") % (
            self._edit_nr,
            self._user_id(),
        )


class ModeEditPersonalNotificationRule(ABCEditUserNotificationRuleMode):
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

    def _user_id(self):
        return user.id

    def _add_change(self, log_what, log_text):
        if has_wato_slave_sites():
            self._start_async_repl = True
            _audit_log.log_audit(log_what, log_text)
        else:
            super()._add_change(log_what, log_text)

    def _back_mode(self) -> ActionResult:
        if has_wato_slave_sites():
            return None
        return redirect(mode_url("user_notifications_p"))

    def title(self) -> str:
        if self._new:
            return _("Create new notification rule")
        return _("Edit notification rule %d") % self._edit_nr
