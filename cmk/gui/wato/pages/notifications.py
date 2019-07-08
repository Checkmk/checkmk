#!/usr/bin/env python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.
"""Modes for managing notification configuration"""

import abc
import time

import cmk
import cmk.utils.store as store

import cmk.gui.view_utils
import cmk.gui.wato.user_profile
import cmk.gui.userdb as userdb
import cmk.gui.permissions as permissions
import cmk.gui.config as config
import cmk.gui.watolib as watolib
from cmk.gui.table import table_element
import cmk.gui.forms as forms
from cmk.gui.exceptions import MKUserError
from cmk.gui.i18n import _
from cmk.gui.globals import html
from cmk.gui.valuespec import (
    TextUnicode,
    Dictionary,
    Alternative,
    FixedValue,
    Tuple,
    Integer,
    Transform,
    ListOf,
    EmailAddress,
    ID,
    DropdownChoice,
    RegExp,
    RegExpUnicode,
    ListChoice,
    Age,
    CascadingDropdown,
    TextAscii,
    ListOfStrings,
    Checkbox,
)

from cmk.gui.plugins.wato import (
    EventsMode,
    mode_registry,
    wato_confirm,
    global_buttons,
    make_action_link,
    add_change,
    rule_option_elements,
    notification_parameter_registry,
)
from cmk.gui.watolib.notifications import (
    save_notification_rules,
    load_notification_rules,
)


class NotificationsMode(EventsMode):
    # TODO: Clean this up. Use inheritance
    @classmethod
    def _rule_match_conditions(cls):
        return cls._generic_rule_match_conditions() \
            + cls._event_rule_match_conditions(flavour="notify") \
            + cls._notification_rule_match_conditions()

    @classmethod
    def _notification_rule_match_conditions(cls):
        def transform_ec_rule_id_match(val):
            if isinstance(val, list):
                return val
            return [val]

        return [
            ("match_escalation",
             Tuple(
                 title=_("Restrict to n<sup>th</sup> to m<sup>th</sup> notification"),
                 orientation="float",
                 elements=[
                     Integer(
                         label=_("from"),
                         help=_("Let through notifications counting from this number. "
                                "The first notification always has the number 1."),
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
             )),
            ("match_escalation_throttle",
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
                     )
                 ],
             )),
            ("match_notification_comment",
             RegExpUnicode(
                 title=_("Match notification comment"),
                 help=
                 _("This match only makes sense for custom notifications. When a user creates "
                   "a custom notification then he/she can enter a comment. This comment is shipped "
                   "in the notification context variable <tt>NOTIFICATIONCOMMENT</tt>. Here you can "
                   "make a condition of that comment. It is a regular expression matching the beginning "
                   "of the comment."),
                 size=60,
                 mode=RegExpUnicode.prefix,
             )),
            ("match_ec",
             Alternative(
                 title=_("Event Console alerts"),
                 help=_("The Event Console can have events create notifications in Check_MK. "
                        "These notifications will be processed by the rule based notification "
                        "system of Check_MK. This matching option helps you distinguishing "
                        "and also gives you access to special event fields."),
                 style="dropdown",
                 elements=[
                     FixedValue(False, title=_("Do not match Event Console alerts"), totext=""),
                     Dictionary(
                         title=_("Match only Event Console alerts"),
                         elements=[
                             ("match_rule_id",
                              Transform(
                                  ListOf(ID(title=_("Match event rule"),
                                            label=_("Rule ID:"),
                                            size=12,
                                            allow_empty=False),
                                         add_label=_("Add Rule ID"),
                                         title=_("Rule IDs")),
                                  forth=transform_ec_rule_id_match,
                              )),
                             ("match_priority",
                              Tuple(
                                  title=_("Match syslog priority"),
                                  help=_("Define a range of syslog priorities this rule matches"),
                                  orientation="horizontal",
                                  show_titles=False,
                                  elements=[
                                      DropdownChoice(label=_("from:"),
                                                     choices=cmk.gui.mkeventd.syslog_priorities,
                                                     default_value=4),
                                      DropdownChoice(label=_(" to:"),
                                                     choices=cmk.gui.mkeventd.syslog_priorities,
                                                     default_value=0),
                                  ],
                              )),
                             ("match_facility",
                              DropdownChoice(
                                  title=_("Match syslog facility"),
                                  help=
                                  _("Make the rule match only if the event has a certain syslog facility. "
                                    "Messages not having a facility are classified as <tt>user</tt>."
                                   ),
                                  choices=cmk.gui.mkeventd.syslog_facilities,
                              )),
                             ("match_comment",
                              RegExpUnicode(
                                  title=_("Match event comment"),
                                  help=
                                  _("This is a regular expression for matching the event's comment."
                                   ),
                                  mode=RegExpUnicode.prefix,
                              )),
                         ])
                 ]))
        ]

    def _render_notification_rules(self,
                                   rules,
                                   userid="",
                                   show_title=False,
                                   show_buttons=True,
                                   analyse=False,
                                   start_nr=0,
                                   profilemode=False):
        if not rules:
            html.message(_("You have not created any rules yet."))
            return

        vs_match_conditions = Dictionary(elements=self._rule_match_conditions())

        if rules:
            if not show_title:
                title = ""
            elif profilemode:
                title = _("Notification rules")
            elif userid:
                url = html.makeuri([("mode", "user_notifications"), ("user", userid)])
                code = html.render_icon_button(url, _("Edit this user's notifications"), "edit")
                title = code + _("Notification rules of user %s") % userid
            else:
                title = _("Global notification rules")
            with table_element(title=title, limit=None, sortable=False) as table:

                if analyse:
                    analyse_rules, _analyse_plugins = analyse

                # have_match = False
                for nr, rule in enumerate(rules):
                    table.row()

                    # Analyse
                    if analyse:
                        table.cell(css="buttons")
                        what, _anarule, reason = analyse_rules[nr + start_nr]
                        if what == "match":
                            html.icon(_("This rule matches"), "rulematch")
                        elif what == "miss":
                            html.icon(_("This rule does not match: %s") % reason, "rulenmatch")

                    if profilemode:
                        listmode = "user_notifications_p"
                    elif userid:
                        listmode = "user_notifications"
                    else:
                        listmode = "notifications"

                    # In case a notification plugin does not exist anymore the permission is completely missing.
                    permission_name = "notification_plugin.%s" % rule['notify_plugin'][0]
                    actions_allowed = permission_name not in permissions.permission_registry \
                        or config.user.may(permission_name)

                    if show_buttons and actions_allowed:
                        anavar = html.request.var("analyse", "")
                        delete_url = make_action_link([
                            ("mode", listmode),
                            ("user", userid),
                            ("_delete", nr),
                        ])
                        drag_url = make_action_link([
                            ("mode", listmode),
                            ("analyse", anavar),
                            ("user", userid),
                            ("_move", nr),
                        ])
                        suffix = "_p" if profilemode else ""
                        edit_url = watolib.folder_preserving_link([
                            ("mode", "notification_rule" + suffix),
                            ("edit", nr),
                            ("user", userid),
                        ])
                        clone_url = watolib.folder_preserving_link([
                            ("mode", "notification_rule" + suffix),
                            ("clone", nr),
                            ("user", userid),
                        ])

                        table.cell(_("Actions"), css="buttons")
                        html.icon_button(edit_url, _("Edit this notification rule"), "edit")
                        html.icon_button(clone_url, _("Create a copy of this notification rule"),
                                         "clone")
                        html.element_dragger_url("tr", base_url=drag_url)
                        html.icon_button(delete_url, _("Delete this notification rule"), "delete")
                    else:
                        table.cell("", css="buttons")
                        for _x in xrange(4):
                            html.empty_icon_button()

                    table.cell("", css="narrow")
                    if rule.get("disabled"):
                        html.icon(_("This rule is currently disabled and will not be applied"),
                                  "disabled")
                    else:
                        html.empty_icon_button()

                    notify_method = rule["notify_plugin"]
                    # Catch rules with empty notify_plugin key
                    # Maybe this should be avoided somewhere else (e.g. rule editor)
                    if not notify_method:
                        notify_method = (None, [])
                    notify_plugin = notify_method[0]

                    table.cell(_("Type"), css="narrow")
                    if notify_method[1] is None:
                        html.icon(_("Cancel notifications for this plugin type"), "notify_cancel")
                    else:
                        html.icon(_("Create a notification"), "notify_create")

                    table.cell(_("Plugin"), notify_plugin or _("Plain Email"), css="narrow nowrap")

                    table.cell(_("Bulk"), css="narrow")
                    if "bulk" in rule or "bulk_period" in rule:
                        html.icon(_("This rule configures bulk notifications."), "bulk")

                    table.cell(_("Description"))
                    url = rule.get("docu_url")
                    if url:
                        html.icon_button(url,
                                         _("Context information about this rule"),
                                         "url",
                                         target="_blank")
                        html.write("&nbsp;")
                    html.write_text(rule["description"])
                    table.cell(_("Contacts"))
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
                    if not infos:
                        html.i(_("(no one)"))

                    else:
                        for line in infos:
                            html.write("&bullet; %s" % line)
                            html.br()

                    table.cell(_("Conditions"), css="rule_conditions")
                    num_conditions = len([key for key in rule if key.startswith("match_")])
                    if num_conditions:
                        title = _("%d conditions") % num_conditions
                        html.begin_foldable_container(
                            treename="rule_%s_%d" % (userid, nr),
                            id_="%s" % nr,
                            isopen=False,
                            title=title,
                            indent=False,
                            tree_img="tree_black",
                        )
                        html.write(vs_match_conditions.value_to_text(rule))
                        html.end_foldable_container()
                    else:
                        html.i(_("(no conditions)"))

    def _add_change(self, log_what, log_text):
        add_change(log_what, log_text, need_restart=False)

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
                ("ec_contact", _("Event Console contact")),
                ("ec_comment", _("Event Console comment")),
            ],
            default_value=["host"],
        )


@mode_registry.register
class ModeNotifications(NotificationsMode):
    @classmethod
    def name(cls):
        return "notifications"

    @classmethod
    def permissions(cls):
        return ["notifications"]

    def __init__(self):
        super(ModeNotifications, self).__init__()
        options = config.user.load_file("notification_display_options", {})
        self._show_user_rules = options.get("show_user_rules", False)
        self._show_backlog = options.get("show_backlog", False)
        self._show_bulks = options.get("show_bulks", False)

    def title(self):
        return _("Notification configuration")

    def buttons(self):
        global_buttons()
        html.context_button(_("New Rule"),
                            watolib.folder_preserving_link([("mode", "notification_rule")]), "new")
        if self._show_user_rules:
            html.context_button(_("Hide user rules"), html.makeactionuri([("_show_user", "")]),
                                "users")
        else:
            html.context_button(_("Show user rules"), html.makeactionuri([("_show_user", "1")]),
                                "users")

        if self._show_backlog:
            html.context_button(_("Hide Analysis"), html.makeactionuri([("_show_backlog", "")]),
                                "analyze")
        else:
            html.context_button(_("Analyse"), html.makeactionuri([("_show_backlog", "1")]),
                                "analyze")

        if self._show_bulks:
            html.context_button(_("Hide Bulks"), html.makeactionuri([("_show_bulks", "")]), "bulk")
        else:
            html.context_button(_("Show Bulks"), html.makeactionuri([("_show_bulks", "1")]), "bulk")

    def action(self):
        if html.request.has_var("_show_user"):
            if html.check_transaction():
                self._show_user_rules = bool(html.request.var("_show_user"))
                self._save_notification_display_options()

        elif html.request.has_var("_show_backlog"):
            if html.check_transaction():
                self._show_backlog = bool(html.request.var("_show_backlog"))
                self._save_notification_display_options()

        elif html.request.has_var("_show_bulks"):
            if html.check_transaction():
                self._show_bulks = bool(html.request.var("_show_bulks"))
                self._save_notification_display_options()

        elif html.request.has_var("_replay"):
            if html.check_transaction():
                nr = int(html.request.var("_replay"))
                watolib.check_mk_local_automation("notification-replay", [str(nr)], None)
                return None, _("Replayed notifiation number %d") % (nr + 1)

        else:
            return self._generic_rule_list_actions(self._get_notification_rules(), "notification",
                                                   _("notification rule"), save_notification_rules)

    def _get_notification_rules(self):
        return load_notification_rules()

    def _save_notification_display_options(self):
        config.user.save_file(
            "notification_display_options", {
                "show_user_rules": self._show_user_rules,
                "show_backlog": self._show_backlog,
                "show_bulks": self._show_bulks,
            })

    def page(self):
        self._show_not_enabled_warning()
        self._show_no_fallback_contact_warning()
        self._show_bulk_notifications()
        self._show_notification_backlog()
        self._show_rules()

    def _show_not_enabled_warning(self):
        # Check setting of global notifications. Are they enabled? If not, display
        # a warning here. Note: this is a main.mk setting, so we cannot access this
        # directly.
        current_settings = watolib.load_configuration_settings()
        if not current_settings.get("enable_rulebased_notifications"):
            url = 'wato.py?mode=edit_configvar&varname=enable_rulebased_notifications'
            html.show_warning(
                _("<b>Warning</b><br><br>Rule based notifications are disabled in your global settings. "
                  "The rules that you edit here will have affect only on notifications that are "
                  "created by the Event Console. Normal monitoring alerts will <b>not</b> use the "
                  "rule based notifications now."
                  "<br><br>"
                  "You can change this setting <a href=\"%s\">here</a>.") % url)

    def _show_no_fallback_contact_warning(self):
        if not self._fallback_mail_contacts_configured():
            url = 'wato.py?mode=edit_configvar&varname=notification_fallback_email'
            html.show_warning(
                _("<b>Warning</b><br><br>You haven't configured a "
                  "<a href=\"%s\">fallback email address</a> nor enabled receiving fallback emails for "
                  "any user. If your monitoring produces a notification that is not matched by any of your "
                  "notification rules, the notification will not be sent out. To prevent that, please "
                  "configure either the global setting or enable the fallback contact option for at least "
                  "one of your users.") % url)

    def _fallback_mail_contacts_configured(self):
        current_settings = watolib.load_configuration_settings()
        if current_settings.get("notification_fallback_email"):
            return True

        for user in userdb.load_users(lock=False).itervalues():
            if user.get("fallback_contact", False):
                return True

        return False

    def _show_bulk_notifications(self):
        if self._show_bulks:
            # Warn if there are unsent bulk notifications
            if not self._render_bulks(only_ripe=False):
                html.message(_("Currently there are no unsent notification bulks pending."))
        else:
            # Warn if there are unsent bulk notifications
            self._render_bulks(only_ripe=True)

    def _render_bulks(self, only_ripe):
        bulks = watolib.check_mk_local_automation("notification-get-bulks",
                                                  ["1" if only_ripe else "0"], None)
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
                table.cell(_("Max. Age (sec)"), "%s" % interval, css="number")
                table.cell(_("Age (sec)"), "%d" % age, css="number")
                if interval and age >= interval:
                    html.icon(_("Age of oldest notification is over maximum age"), "warning")
                table.cell(_("Timeperiod"), "%s" % timeperiod)
                table.cell(_("Max. Count"), str(maxcount), css="number")
                table.cell(_("Count"), str(len(uuids)), css="number")
                if len(uuids) >= maxcount:
                    html.icon(_("Number of notifications exceeds maximum allowed number"),
                              "warning")
        return True

    def _show_notification_backlog(self):
        """Show recent notifications. We can use them for rule analysis"""
        if not self._show_backlog:
            return

        backlog = store.load_data_from_file(cmk.utils.paths.var_dir + "/notify/backlog.mk", [])
        if not backlog:
            return

        with table_element(table_id="backlog",
                           title=_("Recent notifications (for analysis)"),
                           sortable=False) as table:
            for nr, context in enumerate(backlog):
                self._convert_context_to_unicode(context)
                table.row()
                table.cell("&nbsp;", css="buttons")

                analyse_url = html.makeuri([("analyse", str(nr))])
                html.icon_button(analyse_url, _("Analyze ruleset with this notification"),
                                 "analyze")

                html.icon_button(None,
                                 _("Show / hide notification context"),
                                 "toggle_context",
                                 onclick="cmk.wato.toggle_container('notification_context_%d')" %
                                 nr)

                replay_url = html.makeactionuri([("_replay", str(nr))])
                html.icon_button(replay_url, _("Replay this notification, send it again!"),
                                 "replay")

                if html.request.var("analyse") and nr == int(html.request.var("analyse")):
                    html.icon(_("You are analysing this notification"), "rulematch")

                table.cell(_("Nr."), nr + 1, css="number")
                if "MICROTIME" in context:
                    date = time.strftime("%Y-%m-%d %H:%M:%S",
                                         time.localtime(int(context["MICROTIME"]) / 1000000.0))
                else:
                    date = context.get("SHORTDATETIME") or \
                           context.get("LONGDATETIME") or \
                           context.get("DATE") or \
                           _("Unknown date")

                table.cell(_("Date/Time"), date, css="nobr")
                nottype = context.get("NOTIFICATIONTYPE", "")
                table.cell(_("Type"), nottype)

                if nottype in ["PROBLEM", "RECOVERY"]:
                    if context.get("SERVICESTATE"):
                        statename = context["SERVICESTATE"][:4]
                        state = context["SERVICESTATEID"]
                        css = "state svcstate state%s" % state
                    else:
                        statename = context.get("HOSTSTATE")[:4]
                        state = context["HOSTSTATEID"]
                        css = "state hstate hstate%s" % state
                    table.cell(_("State"), statename, css=css)
                elif nottype.startswith("DOWNTIME"):
                    table.cell(_("State"))
                    html.icon(_("Downtime"), "downtime")
                elif nottype.startswith("ACK"):
                    table.cell(_("State"))
                    html.icon(_("Acknowledgement"), "ack")
                elif nottype.startswith("FLAP"):
                    table.cell(_("State"))
                    html.icon(_("Flapping"), "flapping")
                else:
                    table.cell(_("State"), "")

                table.cell(_("Host"), context.get("HOSTNAME", ""))
                table.cell(_("Service"), context.get("SERVICEDESC", ""))
                output = context.get("SERVICEOUTPUT", context.get("HOSTOUTPUT"))

                table.cell(
                    _("Plugin output"),
                    cmk.gui.view_utils.format_plugin_output(
                        output, shall_escape=config.escape_plugin_output))

                # Add toggleable notitication context
                table.row(class_="notification_context hidden", id_="notification_context_%d" % nr)
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

                # This dummy row is needed for not destroying the odd/even row highlighting
                table.row(class_="notification_context hidden")

    def _convert_context_to_unicode(self, context):
        # Convert all values to unicode
        for key, value in context.iteritems():
            if isinstance(value, str):
                try:
                    value_unicode = value.decode("utf-8")
                except:
                    try:
                        value_unicode = value.decode("latin-1")
                    except:
                        value_unicode = u"(Invalid byte sequence)"
                context[key] = value_unicode

    # TODO: Refactor this
    def _show_rules(self):
        # Do analysis
        if html.request.var("analyse"):
            nr = int(html.request.var("analyse"))
            analyse = watolib.check_mk_local_automation("notification-analyse", [str(nr)], None)
        else:
            analyse = False

        start_nr = 0
        rules = self._get_notification_rules()
        self._render_notification_rules(rules, show_title=True, analyse=analyse, start_nr=start_nr)
        start_nr += len(rules)

        if self._show_user_rules:
            users = userdb.load_users()
            userids = users.keys()
            userids.sort()  # Create same order as modules/notification.py
            for userid in userids:
                user = users[userid]
                user_rules = user.get("notification_rules", [])
                if user_rules:
                    self._render_notification_rules(user_rules,
                                                    userid,
                                                    show_title=True,
                                                    show_buttons=False,
                                                    analyse=analyse,
                                                    start_nr=start_nr)
                    start_nr += len(user_rules)

        if analyse:
            with table_element(table_id="plugins", title=_("Resulting notifications")) as table:
                for contact, plugin, parameters, bulk in analyse[1]:
                    table.row()
                    if contact.startswith('mailto:'):
                        contact = contact[7:]  # strip of fake-contact mailto:-prefix
                    table.cell(_("Recipient"), contact)
                    table.cell(_("Plugin"), self._vs_notification_scripts().value_to_text(plugin))
                    table.cell(_("Plugin parameters"), ", ".join(parameters))
                    table.cell(_("Bulking"))
                    if bulk:
                        html.write(_("Time horizon") + ": " + Age().value_to_text(bulk["interval"]))
                        html.write_text(", %s: %d" % (_("Maximum count"), bulk["count"]))
                        html.write(", %s %s" %
                                   (_("group by"), self._vs_notification_bulkby().value_to_text(
                                       bulk["groupby"])))

    def _vs_notification_scripts(self):
        return DropdownChoice(title=_("Notification Script"),
                              choices=watolib.notification_script_choices,
                              default_value="mail")


class UserNotificationsMode(NotificationsMode):
    def __init__(self):
        super(UserNotificationsMode, self).__init__()
        self._start_async_repl = False

    def _from_vars(self):
        self._users = userdb.load_users(lock=html.is_transaction() or html.request.has_var("_move"))

        try:
            user = self._users[self._user_id()]
        except KeyError:
            raise MKUserError(None, _('The requested user does not exist'))

        self._rules = user.setdefault("notification_rules", [])

    @abc.abstractmethod
    def _user_id(self):
        raise NotImplementedError()

    def title(self):
        return _("Custom notification table for user %s") % self._user_id()

    def buttons(self):
        html.context_button(_("All Users"), watolib.folder_preserving_link([("mode", "users")]),
                            "back")
        html.context_button(
            _("User Properties"),
            watolib.folder_preserving_link([("mode", "edit_user"), ("edit", self._user_id())]),
            "edit")
        html.context_button(
            _("New Rule"),
            watolib.folder_preserving_link([("mode", "notification_rule"),
                                            ("user", self._user_id())]), "new")

    def action(self):
        if html.request.has_var("_delete"):
            nr = int(html.request.var("_delete"))
            rule = self._rules[nr]
            c = wato_confirm(
                _("Confirm notification rule deletion"),
                _("Do you really want to delete the notification rule <b>%d</b> <i>%s</i>?") %
                (nr, rule.get("description", "")))
            if c:
                del self._rules[nr]
                userdb.save_users(self._users)

                self._add_change(
                    "notification-delete-user-rule",
                    _("Deleted notification rule %d of user %s") % (nr, self._user_id()))
            elif c is False:
                return ""
            else:
                return

        elif html.request.has_var("_move"):
            if html.check_transaction():
                from_pos = html.get_integer_input("_move")
                to_pos = html.get_integer_input("_index")
                rule = self._rules[from_pos]
                del self._rules[from_pos]  # make to_pos now match!
                self._rules[to_pos:to_pos] = [rule]
                userdb.save_users(self._users)

                self._add_change(
                    "notification-move-user-rule",
                    _("Changed position of notification rule %d of user %s") %
                    (from_pos, self._user_id()))

    def page(self):
        if self._start_async_repl:
            cmk.gui.wato.user_profile.user_profile_async_replication_dialog(
                sites=_get_notification_sync_sites())
            html.h3(_('Notification Rules'))

        self._render_notification_rules(
            rules=self._rules,
            userid=self._user_id(),
            profilemode=isinstance(self, ModePersonalUserNotifications),
        )


def _get_notification_sync_sites():
    return sorted(site_id for site_id, _site in config.wato_slave_sites()
                  if not config.site_is_local(site_id))


@mode_registry.register
class ModeUserNotifications(UserNotificationsMode):
    @classmethod
    def name(cls):
        return "user_notifications"

    @classmethod
    def permissions(cls):
        return ["users"]

    def _user_id(self):
        return html.get_unicode_input("user")


@mode_registry.register
class ModePersonalUserNotifications(UserNotificationsMode):
    @classmethod
    def name(cls):
        return "user_notifications_p"

    @classmethod
    def permissions(cls):
        return None

    def __init__(self):
        super(ModePersonalUserNotifications, self).__init__()
        config.user.need_permission("general.edit_notifications")

    def _user_id(self):
        return config.user.id

    def _add_change(self, log_what, log_text):
        if config.has_wato_slave_sites():
            self._start_async_repl = True
            watolib.log_audit(None, log_what, log_text)
        else:
            super(ModePersonalUserNotifications, self)._add_change(log_what, log_text)

    def title(self):
        return _("Your personal notification rules")

    def buttons(self):
        html.context_button(_("Profile"), "user_profile.py", "back")
        html.context_button(_("New Rule"),
                            watolib.folder_preserving_link([("mode", "notification_rule_p")]),
                            "new")


# TODO: Split editing of user notification rule and global notification rule
#       into separate classes
class EditNotificationRuleMode(NotificationsMode):
    def __init__(self):
        super(EditNotificationRuleMode, self).__init__()
        self._start_async_repl = False

    # TODO: Refactor this
    def _from_vars(self):
        self._edit_nr = html.get_integer_input("edit", -1)
        self._clone_nr = html.get_integer_input("clone", -1)
        self._new = self._edit_nr < 0

        if self._user_id():
            self._users = userdb.load_users(lock=html.is_transaction())
            if self._user_id() not in self._users:
                raise MKUserError(
                    None,
                    _("The user you are trying to edit "
                      "notification rules for does not exist."))
            user = self._users[self._user_id()]
            self._rules = user.setdefault("notification_rules", [])
        else:
            self._rules = load_notification_rules(lock=html.is_transaction())

        if self._new:
            if self._clone_nr >= 0 and not html.request.var("_clear"):
                self._rule = {}
                try:
                    self._rule.update(self._rules[self._clone_nr])
                except IndexError:
                    raise MKUserError(None, _("This %s does not exist.") % "notification rule")
            else:
                self._rule = {}
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
            contact_headers = []
            section_contacts = []
            section_override = []
        else:
            contact_headers = [
                (_("Contact Selection"), [
                    "contact_all",
                    "contact_all_with_email",
                    "contact_object",
                    "contact_users",
                    "contact_groups",
                    "contact_emails",
                    "contact_match_macros",
                    "contact_match_groups",
                ]),
            ]
            section_contacts = [
                # Contact selection
                ("contact_object",
                 Checkbox(
                     title=_("All contacts of the notified object"),
                     label=_("Notify all contacts of the notified host or service."),
                     default_value=True,
                 )),
                ("contact_all", Checkbox(
                    title=_("All users"),
                    label=_("Notify all users"),
                )),
                ("contact_all_with_email",
                 Checkbox(
                     title=_("All users with an email address"),
                     label=_(
                         "Notify all users that have configured an email address in their profile"),
                 )),
                ("contact_users",
                 ListOf(
                     userdb.UserSelection(only_contacts=False),
                     title=_("The following users"),
                     help=_(
                         "Enter a list of user IDs to be notified here. These users need to be members "
                         "of at least one contact group in order to be notified."),
                     movable=False,
                     add_label=_("Add user"),
                 )),
                ("contact_groups",
                 ListOf(
                     cmk.gui.plugins.wato.ContactGroupSelection(),
                     title=_("The members of certain contact groups"),
                     movable=False,
                 )),
                ("contact_emails",
                 ListOfStrings(
                     valuespec=EmailAddress(size=44),
                     title=_("The following explicit email addresses"),
                     orientation="vertical",
                 )),
                ("contact_match_macros",
                 ListOf(
                     Tuple(elements=[
                         TextAscii(
                             title=_("Name of the macro"),
                             help=
                             _("As configured in the users settings. Do not add a leading underscore."
                              ),
                             allow_empty=False,
                         ),
                         RegExp(
                             title=_("Required match (regular expression)"),
                             help=_("This expression must match the value of the variable"),
                             allow_empty=False,
                             mode=RegExp.complete,
                         ),
                     ]),
                     title=_("Restrict by custom macros"),
                     help=_("Here you can <i>restrict</i> the list of contacts that has been "
                            "built up by the previous options to those who have certain values "
                            "in certain custom macros. If you add more than one macro here then "
                            "<i>all</i> macros must match. The matches are regular expressions "
                            "that must fully match the value of the macro."),
                     add_label=_("Add condition"),
                 )),
                ("contact_match_groups",
                 ListOf(
                     cmk.gui.plugins.wato.ContactGroupSelection(),
                     title=_("Restrict by contact groups"),
                     help=_(
                         "Here you can <i>restrict</i> the list of contacts that has been "
                         "built up by the previous options to those that are members of "
                         "selected contact groups. If you select more than one contact group here then "
                         "the user must be member of <i>all</i> these groups."),
                     add_label=_("Add Group"),
                     movable=False,
                 )),
            ]
            section_override = [
                ("allow_disable",
                 Checkbox(
                     title=_("Overriding by users"),
                     help=_(
                         "If you uncheck this option then users are not allowed to deactive notifications "
                         "that are created by this rule."),
                     label=_("allow users to deactivate this notification"),
                     default_value=True,
                 )),
            ]

        bulk_options = [
            ("count",
             Integer(
                 title=_("Maximum bulk size"),
                 label=_("Bulk up to"),
                 unit=_("Notifications"),
                 help=_("At most that many Notifications are kept back for bulking. A value of "
                        "1 essentially turns off notification bulking."),
                 default_value=1000,
                 minvalue=1,
             )),
            (
                "groupby",
                self._vs_notification_bulkby(),
            ),
            ("groupby_custom",
             ListOfStrings(
                 valuespec=ID(),
                 orientation="horizontal",
                 title=
                 _("Create separate notification bulks for different values of the following custom macros"
                  ),
                 help=
                 _("If you enter the names of host/service-custom macros here then for each different "
                   "combination of values of those macros a separate bulk will be created. This can be used "
                   "in combination with the grouping by folder, host etc. Omit any leading underscore. "
                   "<b>Note</b>: If you are using "
                   "Nagios as a core you need to make sure that the values of the required macros are "
                   "present in the notification context. This is done in <tt>check_mk_templates.cfg</tt>. If you "
                   "macro is <tt>_FOO</tt> then you need to add the variables <tt>NOTIFY_HOST_FOO</tt> and "
                   "<tt>NOTIFY_SERVICE_FOO</tt>."),
             )),
            ("bulk_subject",
             TextAscii(
                 title=_("Subject for bulk notifications"),
                 help=
                 _("Customize the subject for bulk notifications and overwrite "
                   "default subject <tt>Check_MK: $COUNT_NOTIFICATIONS$ notifications for HOST</tt>"
                   " resp. <tt>Check_MK: $COUNT_NOTIFICATIONS$ notifications for $COUNT_HOSTS$ hosts</tt>. "
                   "Both macros <tt>$COUNT_NOTIFICATIONS$</tt> and <tt>$COUNT_HOSTS$</tt> can be used in "
                   "any customized subject. If <tt>$COUNT_NOTIFICATIONS$</tt> is used, the amount of "
                   "notifications will be inserted and if you use <tt>$COUNT_HOSTS$</tt> then the "
                   "amount of hosts will be applied."),
                 size=80,
                 default_value=
                 "Check_MK: $COUNT_NOTIFICATIONS$ notifications for $COUNT_HOSTS$ hosts")),
        ]

        return Dictionary(
            title=_("Rule Properties"),
            elements=rule_option_elements() + section_override + self._rule_match_conditions() +
            section_contacts + [
                # Notification
                ("notify_plugin",
                 CascadingDropdown(
                     title=_("Notification Method"),
                     choices=self._notification_script_choices_with_parameters,
                     default_value=("mail", {}),
                 )),
                ("bulk",
                 Transform(CascadingDropdown(
                     title="Notification Bulking",
                     orientation="vertical",
                     choices=[
                         ("always", _("Always bulk"),
                          Dictionary(
                              help=
                              _("Enabling the bulk notifications will collect several subsequent notifications "
                                "for the same contact into one single notification, which lists of all the "
                                "actual problems, e.g. in a single email. This cuts down the number of notifications "
                                "in cases where many (related) problems occur within a short time."
                               ),
                              elements=[
                                  ("interval",
                                   Age(
                                       title=_("Time horizon"),
                                       label=_("Bulk up to"),
                                       help=
                                       _("Notifications are kept back for bulking at most for this time."
                                        ),
                                       default_value=60,
                                   )),
                              ] + bulk_options,
                              columns=1,
                              optional_keys=["bulk_subject"],
                          )),
                         ("timeperiod", _("Bulk during timeperiod"),
                          Dictionary(
                              help=_(
                                  "By enabling this option notifications will be bulked only if the "
                                  "specified timeperiod is active. When the timeperiod ends a "
                                  "bulk containing all notifications that appeared during that time "
                                  "will be sent. "
                                  "If bulking should be enabled outside of the timeperiod as well, "
                                  "the option \"Also Bulk outside of timeperiod\" can be used."),
                              elements=[
                                  ("timeperiod",
                                   watolib.timeperiods.TimeperiodSelection(title=_(
                                       "Only bulk notifications during the following timeperiod"),)
                                  ),
                              ] + bulk_options + [
                                  ("bulk_outside",
                                   Dictionary(
                                       title=_("Also bulk outside of timeperiod"),
                                       help=_(
                                           "By enabling this option notifications will be bulked "
                                           "outside of the defined timeperiod as well."),
                                       elements=[
                                           ("interval",
                                            Age(
                                                title=_("Time horizon"),
                                                label=_("Bulk up to"),
                                                help=
                                                _("Notifications are kept back for bulking at most for this time."
                                                 ),
                                                default_value=60,
                                            )),
                                       ] + bulk_options,
                                       columns=1,
                                       optional_keys=["bulk_subject"],
                                   )),
                              ],
                              columns=1,
                              optional_keys=["bulk_subject", "bulk_outside"],
                          )),
                     ],
                 ),
                           forth=lambda x: x if isinstance(x, tuple) else ("always", x))),
            ],
            optional_keys=[
                "match_site", "match_folder", "match_hosttags", "match_hostgroups", "match_hosts",
                "match_exclude_hosts", "match_servicegroups", "match_exclude_servicegroups",
                "match_servicegroups_regex", "match_exclude_servicegroups_regex", "match_services",
                "match_exclude_services", "match_contacts", "match_contactgroups",
                "match_plugin_output", "match_timeperiod", "match_escalation",
                "match_escalation_throttle", "match_sl", "match_host_event", "match_service_event",
                "match_ec", "match_notification_comment", "match_checktype", "bulk",
                "contact_users", "contact_groups", "contact_emails", "contact_match_macros",
                "contact_match_groups"
            ],
            headers=[
                (_("Rule Properties"),
                 ["description", "comment", "disabled", "docu_url", "allow_disable"]),
                (_("Notification Method"), ["notify_plugin", "notify_method", "bulk"]),
            ] + contact_headers + [
                (_("Conditions"), [
                    "match_site", "match_folder", "match_hosttags", "match_hostgroups",
                    "match_hosts", "match_exclude_hosts", "match_servicegroups",
                    "match_exclude_servicegroups", "match_servicegroups_regex",
                    "match_exclude_servicegroups_regex", "match_services", "match_exclude_services",
                    "match_checktype", "match_contacts", "match_contactgroups",
                    "match_plugin_output", "match_timeperiod", "match_escalation",
                    "match_escalation_throttle", "match_sl", "match_host_event",
                    "match_service_event", "match_ec", "match_notification_comment"
                ]),
            ],
            render="form",
            form_narrow=True,
            validate=self._validate_notification_rule,
        )

    def _notification_script_choices_with_parameters(self):
        choices = []
        for script_name, title in watolib.notification_script_choices():
            if script_name in notification_parameter_registry:
                vs = notification_parameter_registry[script_name]().spec
            else:
                vs = ListOfStrings(
                    title=_("Call with the following parameters:"),
                    help=
                    _("The given parameters are available in scripts as NOTIFY_PARAMETER_1, NOTIFY_PARAMETER_2, etc."
                     ),
                    valuespec=TextUnicode(size=24),
                    orientation="horizontal",
                )

            vs_alternative = Alternative(
                style="dropdown",
                elements=[
                    vs,
                    FixedValue(None,
                               totext=_("previous notifications of this type are cancelled"),
                               title=_("Cancel previous notifications")),
                ],
            )

            choices.append((script_name, title, vs_alternative))
        return choices

    def _validate_notification_rule(self, rule, varprefix):
        if "bulk" in rule and rule["notify_plugin"][1] is None:
            raise MKUserError(
                varprefix + "_p_bulk_USE",
                _("It does not make sense to add a bulk configuration for cancelling rules."))

        if "bulk" in rule or "bulk_period" in rule:
            if rule["notify_plugin"][0]:
                info = watolib.load_notification_scripts()[rule["notify_plugin"][0]]
                if not info["bulk"]:
                    raise MKUserError(
                        varprefix + "_p_notify_plugin",
                        _("The notification script %s does not allow bulking.") % info["title"])
            else:
                raise MKUserError(
                    varprefix + "_p_notify_plugin",
                    _("Legacy ASCII Emails do not support bulking. You can either disable notification "
                      "bulking or choose another notification plugin which allows bulking."))

    @abc.abstractmethod
    def _user_id(self):
        raise NotImplementedError()

    @abc.abstractmethod
    def _back_mode(self):
        raise NotImplementedError()

    def title(self):
        if self._new:
            if self._user_id():
                return _("Create new notification rule for user %s") % self._user_id()
            return _("Create new notification rule")

        if self._user_id():
            return _("Edit notification rule %d of user %s") % (self._edit_nr, self._user_id())
        return _("Edit notification rule %d") % self._edit_nr

    def buttons(self):
        html.context_button(
            _("All Rules"),
            watolib.folder_preserving_link([("mode", "notifications"),
                                            ("userid", self._user_id())]), "back")

    def action(self):
        if not html.check_transaction():
            return self._back_mode()

        vs = self._valuespec()
        self._rule = vs.from_html_vars("rule")
        if self._user_id():
            self._rule["contact_users"] = [self._user_id()]  # Force selection of our user

        vs.validate_value(self._rule, "rule")

        if self._user_id():
            # User rules are always allow_disable
            # The parameter is set just after the validation, since the allow_disable
            # key isn't in the valuespec. Curiously, the validation does not fail
            # even the allow_disable key is set before the validate_value...
            self._rule["allow_disable"] = True

        if self._new and self._clone_nr >= 0:
            self._rules[self._clone_nr:self._clone_nr] = [self._rule]
        elif self._new:
            self._rules[0:0] = [self._rule]
        else:
            self._rules[self._edit_nr] = self._rule

        if self._user_id():
            userdb.save_users(self._users)
        else:
            save_notification_rules(self._rules)

        if self._new:
            log_what = "new-notification-rule"
            if self._user_id():
                log_text = _("Created new notification rule for user %s") % self._user_id()
            else:
                log_text = _("Created new notification rule")
        else:
            log_what = "edit-notification-rule"
            if self._user_id():
                log_text = _("Changed notification rule %d of user %s") % (self._edit_nr,
                                                                           self._user_id())
            else:
                log_text = _("Changed notification rule %d") % self._edit_nr
        self._add_change(log_what, log_text)

        return self._back_mode()

    def page(self):
        if self._start_async_repl:
            cmk.gui.wato.user_profile.user_profile_async_replication_dialog(
                sites=_get_notification_sync_sites())
            return

        html.begin_form("rule", method="POST")
        vs = self._valuespec()
        vs.render_input("rule", self._rule)
        vs.set_focus("rule")
        forms.end()
        html.button("save", _("Save"))
        html.hidden_fields()
        html.end_form()


@mode_registry.register
class ModeEditNotificationRule(EditNotificationRuleMode):
    @classmethod
    def name(cls):
        return "notification_rule"

    @classmethod
    def permissions(cls):
        return ["notifications"]

    def _user_id(self):
        return html.get_unicode_input("user")

    def _back_mode(self):
        if self._user_id():
            return "user_notifications"
        return "notifications"


@mode_registry.register
class ModeEditPersonalNotificationRule(EditNotificationRuleMode):
    @classmethod
    def name(cls):
        return "notification_rule_p"

    @classmethod
    def permissions(cls):
        return None

    def __init__(self):
        super(ModeEditPersonalNotificationRule, self).__init__()
        config.user.need_permission("general.edit_notifications")

    def _user_id(self):
        return config.user.id

    def _add_change(self, log_what, log_text):
        if config.has_wato_slave_sites():
            self._start_async_repl = True
            watolib.log_audit(None, log_what, log_text)
        else:
            super(ModeEditPersonalNotificationRule, self)._add_change(log_what, log_text)

    def _back_mode(self):
        if config.has_wato_slave_sites():
            return
        return "user_notifications_p"

    def title(self):
        if self._new:
            return _("Create new notification rule")
        return _("Edit notification rule %d") % self._edit_nr

    def buttons(self):
        html.context_button(_("All Rules"),
                            watolib.folder_preserving_link([("mode", "user_notifications_p")]),
                            "back")
