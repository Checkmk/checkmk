#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Modes for managing users and contacts"""

from typing import Iterator, Optional, Type, overload
import base64
import traceback
import time

from six import ensure_str

import cmk.utils.version as cmk_version
import cmk.utils.render as render
from cmk.utils.type_defs import UserId, timeperiod_spec_alias

import cmk.gui.userdb as userdb
import cmk.gui.plugins.userdb.utils as userdb_utils
import cmk.gui.config as config
import cmk.gui.watolib as watolib
import cmk.gui.escaping as escaping
from cmk.gui.table import table_element
import cmk.gui.forms as forms
import cmk.gui.background_job as background_job
import cmk.gui.gui_background_job as gui_background_job
from cmk.gui.htmllib import Choices, HTML
from cmk.gui.plugins.userdb.htpasswd import hash_password
from cmk.gui.plugins.userdb.utils import (
    cleanup_connection_id,
    get_connection,
)
from cmk.gui.log import logger
from cmk.gui.exceptions import MKUserError
from cmk.gui.i18n import _, _u, get_languages, get_language_alias
from cmk.gui.globals import html, request
from cmk.gui.valuespec import (
    UserID,
    EmailAddress,
    Alternative,
    DualListChoice,
    FixedValue,
)
from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.page_menu import (
    PageMenu,
    PageMenuDropdown,
    PageMenuTopic,
    PageMenuEntry,
    make_simple_link,
    make_simple_form_page_menu,
    make_confirmed_form_submit_link,
)
from cmk.gui.watolib.users import delete_users, edit_users
from cmk.gui.watolib.groups import load_contact_group_information
from cmk.gui.watolib.global_settings import rulebased_notifications_enabled

from cmk.gui.plugins.wato import (
    WatoMode,
    ActionResult,
    mode_registry,
    make_confirm_link,
    make_action_link,
    flash,
    redirect,
    mode_url,
)

from cmk.gui.utils.urls import makeuri, makeuri_contextless

if cmk_version.is_managed_edition():
    import cmk.gui.cme.managed as managed  # pylint: disable=no-name-in-module
else:
    managed = None  # type: ignore[assignment]


@mode_registry.register
class ModeUsers(WatoMode):
    @classmethod
    def name(cls):
        return "users"

    @classmethod
    def permissions(cls):
        return ["users"]

    def __init__(self):
        super(ModeUsers, self).__init__()
        self._job = userdb.UserSyncBackgroundJob()
        self._job_snapshot = userdb.UserSyncBackgroundJob().get_status_snapshot()

    def title(self):
        return _("Users")

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        return PageMenu(
            dropdowns=[
                PageMenuDropdown(
                    name="users",
                    title=_("Users"),
                    topics=[
                        PageMenuTopic(
                            title=_("Add user"),
                            entries=[
                                PageMenuEntry(
                                    title=_("Add user"),
                                    icon_name="new",
                                    item=make_simple_link(
                                        watolib.folder_preserving_link([("mode", "edit_user")])),
                                    is_shortcut=True,
                                    is_suggested=True,
                                ),
                            ],
                        ),
                        PageMenuTopic(
                            title=_("On selected users"),
                            entries=[
                                PageMenuEntry(
                                    title=_("Delete users"),
                                    shortcut_title=_("Delete selected users"),
                                    icon_name="delete",
                                    item=make_confirmed_form_submit_link(
                                        form_name="bulk_delete_form",
                                        button_name="_bulk_delete_users",
                                        message=_(
                                            "Do you really want to delete the selected users?"),
                                    ),
                                    is_shortcut=True,
                                    is_suggested=True,
                                ),
                            ],
                        ),
                        PageMenuTopic(
                            title=_("Synchronized users"),
                            entries=list(self._page_menu_entries_synchronized_users()),
                        ),
                        PageMenuTopic(
                            title=_("Notify users"),
                            entries=list(self._page_menu_entries_notify_users()),
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
        )

    def _page_menu_entries_synchronized_users(self) -> Iterator[PageMenuEntry]:
        if userdb.sync_possible():
            if not self._job_snapshot.is_active():
                yield PageMenuEntry(
                    title=_("Synchronize users"),
                    icon_name="replicate",
                    item=make_simple_link(html.makeactionuri([("_sync", 1)])),
                )

                yield PageMenuEntry(
                    title=_("Last synchronization result"),
                    icon_name="background_job_details",
                    item=make_simple_link(self._job.detail_url()),
                )

    def _page_menu_entries_notify_users(self) -> Iterator[PageMenuEntry]:
        if config.user.may("general.notify"):
            yield PageMenuEntry(
                title=_("Notify users"),
                icon_name="notification",
                item=make_simple_link("notify.py"),
            )

    def _page_menu_entries_related(self) -> Iterator[PageMenuEntry]:
        if config.user.may("wato.custom_attributes"):
            yield PageMenuEntry(
                title=_("Custom attributes"),
                icon_name="custom_attr",
                item=make_simple_link(watolib.folder_preserving_link([("mode", "user_attrs")])),
            )

        yield PageMenuEntry(
            title=_("LDAP & Active Directory"),
            icon_name="ldap",
            item=make_simple_link(watolib.folder_preserving_link([("mode", "ldap_config")])),
        )

    def action(self) -> ActionResult:
        if not html.check_transaction():
            return redirect(self.mode_url())

        if html.request.var('_delete'):
            delete_users([html.request.get_unicode_input("_delete")])

        elif html.request.var('_sync'):
            try:

                job = userdb.UserSyncBackgroundJob()
                job.set_function(job.do_sync,
                                 add_to_changelog=True,
                                 enforce_sync=True,
                                 load_users_func=userdb.load_users,
                                 save_users_func=userdb.save_users)

                try:
                    job.start()
                except background_job.BackgroundJobAlreadyRunning as e:
                    raise MKUserError(None,
                                      _("Another synchronization job is already running: %s") % e)

                self._job_snapshot = job.get_status_snapshot()
            except Exception:
                logger.exception("error syncing users")
                raise MKUserError(None, traceback.format_exc().replace('\n', '<br>\n'))

        elif html.request.var("_bulk_delete_users"):
            self._bulk_delete_users_after_confirm()

        else:
            action_handler = gui_background_job.ActionHandler(self.breadcrumb())
            action_handler.handle_actions()
            if action_handler.did_acknowledge_job():
                self._job_snapshot = userdb.UserSyncBackgroundJob().get_status_snapshot()
                flash(_("Synchronization job acknowledged"))
        return redirect(self.mode_url())

    def _bulk_delete_users_after_confirm(self):
        selected_users = []
        users = userdb.load_users()
        for varname, _value in html.request.itervars(prefix="_c_user_"):
            if html.get_checkbox(varname):
                user = base64.b64decode(
                    varname.split("_c_user_")[-1].encode("utf-8")).decode("utf-8")
                if user in users:
                    selected_users.append(user)

        if selected_users:
            delete_users(selected_users)

    def page(self):
        if not self._job_snapshot.exists():
            # Skip if snapshot doesnt exists
            pass

        elif self._job_snapshot.is_active():
            # Still running
            html.show_message(
                HTML(_("User synchronization currently running: ")) + self._job_details_link())
            url = makeuri(request, [])
            html.immediate_browser_redirect(2, url)

        elif self._job_snapshot.state() == gui_background_job.background_job.JobStatusStates.FINISHED \
             and not self._job_snapshot.acknowledged_by():
            # Just finished, auto-acknowledge
            userdb.UserSyncBackgroundJob().acknowledge(config.user.id)
            #html.show_message(_("User synchronization successful"))

        elif not self._job_snapshot.acknowledged_by() and self._job_snapshot.has_exception():
            # Finished, but not OK - show info message with links to details
            html.show_warning(
                HTML(_("Last user synchronization ran into an exception: ")) +
                self._job_details_link())

        self._show_user_list()

    def _job_details_link(self):
        return html.render_a("%s" % self._job.get_title(), href=self._job.detail_url())

    def _job_details_url(self):
        return makeuri_contextless(
            request,
            [("mode", "background_job_details"),
             ("back_url",
              makeuri_contextless(request, [("mode", "users")], filename="%s.py" % html.myfile)),
             ("job_id", self._job_snapshot.get_job_id())],
            filename="wato.py")

    def _show_job_info(self):
        if self._job_snapshot.is_active():
            html.h3(_("Current status of synchronization process"))
            html.set_browser_reload(0.8)
        else:
            html.h3(_("Result of last synchronization process"))

        job_manager = gui_background_job.GUIBackgroundJobManager()
        job_manager.show_job_details_from_snapshot(job_snapshot=self._job_snapshot)
        html.br()

    def _show_user_list(self):
        visible_custom_attrs = [
            (name, attr) for name, attr in userdb.get_user_attributes() if attr.show_in_table()
        ]

        users = userdb.load_users()

        entries = list(users.items())

        html.begin_form("bulk_delete_form", method="POST")

        roles = userdb_utils.load_roles()
        timeperiods = watolib.timeperiods.load_timeperiods()
        contact_groups = load_contact_group_information()

        with table_element("users", None, empty_text=_("No users are defined yet.")) as table:
            online_threshold = time.time() - config.user_online_maxage
            for uid, user in sorted(entries, key=lambda x: x[1].get("alias", x[0]).lower()):
                table.row()

                # Checkboxes
                table.cell(html.render_input("_toggle_group",
                                             type_="button",
                                             class_="checkgroup",
                                             onclick="cmk.selection.toggle_all_rows();",
                                             value='X'),
                           sortable=False,
                           css="checkbox")

                if uid != config.user.id:
                    html.checkbox("_c_user_%s" % ensure_str(base64.b64encode(uid.encode("utf-8"))))

                user_connection_id = cleanup_connection_id(user.get('connector'))
                connection = get_connection(user_connection_id)

                # Buttons
                table.cell(_("Actions"), css="buttons")
                if connection:  # only show edit buttons when the connector is available and enabled
                    edit_url = watolib.folder_preserving_link([("mode", "edit_user"),
                                                               ("edit", uid)])
                    html.icon_button(edit_url, _("Properties"), "edit")

                    clone_url = watolib.folder_preserving_link([("mode", "edit_user"),
                                                                ("clone", uid)])
                    html.icon_button(clone_url, _("Create a copy of this user"), "clone")

                delete_url = make_confirm_link(
                    url=make_action_link([("mode", "users"), ("_delete", uid)]),
                    message=_("Do you really want to delete the user %s?") % uid,
                )
                html.icon_button(delete_url, _("Delete"), "delete")

                notifications_url = watolib.folder_preserving_link([("mode", "user_notifications"),
                                                                    ("user", uid)])
                if rulebased_notifications_enabled():
                    html.icon_button(notifications_url, _("Custom notification table of this user"),
                                     "notifications")

                # ID
                table.cell(_("ID"), uid)

                # Online/Offline
                if config.user.may("wato.show_last_user_activity"):
                    last_seen = userdb.get_last_activity(uid, user)
                    user.get('last_seen', 0)
                    if last_seen >= online_threshold:
                        title = _('Online')
                        img_txt = 'online'
                    elif last_seen != 0:
                        title = _('Offline')
                        img_txt = 'offline'
                    elif last_seen == 0:
                        title = _('Never logged in')
                        img_txt = 'inactive'

                    title += ' (%s %s)' % (render.date(last_seen), render.time_of_day(last_seen))
                    table.cell(_("Act."))
                    html.icon(img_txt, title)

                    table.cell(_("Last seen"))
                    if last_seen != 0:
                        html.write_text("%s %s" %
                                        (render.date(last_seen), render.time_of_day(last_seen)))
                    else:
                        html.write_text(_("Never logged in"))

                if cmk_version.is_managed_edition():
                    table.cell(_("Customer"), managed.get_customer_name(user))

                # Connection
                if connection:
                    table.cell(_("Connection"),
                               '%s (%s)' % (connection.short_title(), user_connection_id))
                    locked_attributes = userdb.locked_attributes(user_connection_id)
                else:
                    table.cell(_("Connection"),
                               "%s (%s) (%s)" % (_("UNKNOWN"), user_connection_id, _("disabled")),
                               css="error")
                    locked_attributes = []

                # Authentication
                if "automation_secret" in user:
                    auth_method = _("Automation")
                elif user.get("password") or 'password' in locked_attributes:
                    auth_method = _("Password")
                else:
                    auth_method = "<i>%s</i>" % _("none")
                table.cell(_("Authentication"), auth_method)

                table.cell(_("State"))
                if user.get("locked", False):
                    html.icon('user_locked', _('The login is currently locked'))

                if "disable_notifications" in user and isinstance(user["disable_notifications"],
                                                                  bool):
                    disable_notifications_opts = {"disable": user["disable_notifications"]}
                else:
                    disable_notifications_opts = user.get("disable_notifications", {})

                if disable_notifications_opts.get("disable", False):
                    html.icon('notif_disabled', _('Notifications are disabled'))

                # Full name / Alias
                table.text_cell(_("Alias"), user.get("alias", ""))

                # Email
                table.text_cell(_("Email"), user.get("email", ""))

                # Roles
                table.cell(_("Roles"))
                if user.get("roles", []):
                    role_links = [(watolib.folder_preserving_link([("mode", "edit_role"),
                                                                   ("edit", role)]),
                                   roles[role].get("alias")) for role in user["roles"]]
                    html.write_html(
                        HTML(", ").join(
                            html.render_a(alias, href=link) for (link, alias) in role_links))

                # contact groups
                table.cell(_("Contact groups"))
                cgs = user.get("contactgroups", [])
                if cgs:
                    cg_aliases = [
                        contact_groups[c]['alias'] if c in contact_groups else c for c in cgs
                    ]
                    cg_urls = [
                        watolib.folder_preserving_link([("mode", "edit_contact_group"),
                                                        ("edit", c)]) for c in cgs
                    ]
                    html.write_html(
                        HTML(", ").join(
                            html.render_a(content, href=url)
                            for (content, url) in zip(cg_aliases, cg_urls)))
                else:
                    html.i(_("none"))

                #table.cell(_("Sites"))
                #html.write(vs_authorized_sites().value_to_text(user.get("authorized_sites",
                #                                                vs_authorized_sites().default_value())))

                # notifications
                if not rulebased_notifications_enabled():
                    table.cell(_("Notifications"))
                    if not cgs:
                        html.i(_("not a contact"))
                    elif not user.get("notifications_enabled", True):
                        html.write_text(_("disabled"))
                    elif user.get("host_notification_options", "") == "" and \
                         user.get("service_notification_options", "") == "":
                        html.write_text(_("all events disabled"))
                    else:
                        tp = user.get("notification_period", "24X7")
                        if tp not in timeperiods:
                            tp = tp + _(" (invalid)")
                        elif tp not in watolib.timeperiods.builtin_timeperiods():
                            url = watolib.folder_preserving_link([("mode", "edit_timeperiod"),
                                                                  ("edit", tp)])
                            tp = html.render_a(timeperiod_spec_alias(timeperiods[tp], tp), href=url)
                        else:
                            tp = timeperiod_spec_alias(timeperiods[tp], tp)
                        html.write(tp)

                # the visible custom attributes
                for name, attr in visible_custom_attrs:
                    vs = attr.valuespec()
                    table.cell(escaping.escape_attribute(_u(vs.title())))
                    html.write(vs.value_to_text(user.get(name, vs.default_value())))

        html.hidden_fields()
        html.end_form()

        if not load_contact_group_information():
            url = "wato.py?mode=contact_groups"
            html.open_div(class_="info")
            html.write(
                _("Note: you haven't defined any contact groups yet. If you <a href='%s'>"
                  "create some contact groups</a> you can assign users to them und thus "
                  "make them monitoring contacts. Only monitoring contacts can receive "
                  "notifications.") % url)
            html.write(" you can assign users to them und thus "
                       "make them monitoring contacts. Only monitoring contacts can receive "
                       "notifications.")
            html.close_div()


# TODO: Create separate ModeCreateUser()
# TODO: Move CME specific stuff to CME related class
# TODO: Refactor action / page to use less hand crafted logic (valuespecs instead?)
@mode_registry.register
class ModeEditUser(WatoMode):
    @classmethod
    def name(cls):
        return "edit_user"

    @classmethod
    def permissions(cls):
        return ["users"]

    @classmethod
    def parent_mode(cls) -> Optional[Type[WatoMode]]:
        return ModeUsers

    # pylint does not understand this overloading
    @overload
    @classmethod
    def mode_url(cls, *, edit: str) -> str:  # pylint: disable=arguments-differ
        ...

    @overload
    @classmethod
    def mode_url(cls, **kwargs: str) -> str:
        ...

    @classmethod
    def mode_url(cls, **kwargs: str) -> str:
        return super().mode_url(**kwargs)

    def _breadcrumb_url(self) -> str:
        assert self._user_id is not None
        return self.mode_url(edit=self._user_id)

    def __init__(self):
        super(ModeEditUser, self).__init__()

        # Load data that is referenced - in order to display dropdown
        # boxes and to check for validity.
        self._contact_groups = load_contact_group_information()
        self._timeperiods = watolib.timeperiods.load_timeperiods()
        self._roles = userdb_utils.load_roles()

        if cmk_version.is_managed_edition():
            self._vs_customer = managed.vs_customer()

    def _from_vars(self):
        # TODO: Should we turn the both fields below into Optional[UserId]?
        self._user_id = html.request.get_unicode_input("edit")  # missing -> new user
        # This is needed for the breadcrumb computation:
        # When linking from user notification rules page the request variable is "user"
        # instead of "edit". We should also change that variable to "user" on this page,
        # then we can simply use self._user_id.
        if not self._user_id and html.request.has_var("user"):
            self._user_id = html.request.get_str_input_mandatory("user")

        self._cloneid = html.request.get_unicode_input("clone")  # Only needed in 'new' mode
        # TODO: Nuke the field below? It effectively hides facts about _user_id for mypy.
        self._is_new_user = self._user_id is None
        self._users = userdb.load_users(lock=html.is_transaction())
        new_user = userdb.new_user_template('htpasswd')
        if self._user_id is not None:
            self._user = self._users.get(UserId(self._user_id), new_user)
        elif self._cloneid:
            self._user = self._users.get(UserId(self._cloneid), new_user)
        else:
            self._user = new_user
        self._locked_attributes = userdb.locked_attributes(self._user.get('connector'))

    def title(self):
        if self._is_new_user:
            return _("Add user")
        return _("Edit user %s") % self._user_id

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        menu = make_simple_form_page_menu(breadcrumb, form_name="user", button_name="save")

        menu.dropdowns.insert(
            1,
            PageMenuDropdown(
                name="related",
                title=_("Related"),
                topics=[
                    PageMenuTopic(
                        title=_("Setup"),
                        entries=list(self._page_menu_entries_related()),
                    ),
                ],
            ))

        return menu

    def _page_menu_entries_related(self) -> Iterator[PageMenuEntry]:
        if self._rbn_enabled and not self._is_new_user:
            yield PageMenuEntry(
                title=_("Notifications"),
                icon_name="notifications",
                item=make_simple_link(
                    watolib.folder_preserving_link([("mode", "user_notifications"),
                                                    ("user", self._user_id)])),
            )

    def action(self) -> ActionResult:
        if not html.check_transaction():
            return redirect(mode_url("users"))

        if self._user_id is None:  # same as self._is_new_user
            self._user_id = UserID(allow_empty=False).from_html_vars("user_id")
            user_attrs = {}
        else:
            self._user_id = html.request.get_unicode_input_mandatory("edit").strip()
            user_attrs = self._users[UserId(self._user_id)]

        # Full name
        user_attrs["alias"] = html.request.get_unicode_input_mandatory("alias").strip()

        # Locking
        user_attrs["locked"] = html.get_checkbox("locked")
        increase_serial = False

        if (UserId(self._user_id) in self._users and
                self._users[UserId(self._user_id)]["locked"] != user_attrs["locked"] and
                user_attrs["locked"]):
            increase_serial = True  # when user is being locked now, increase the auth serial

        # Authentication: Password or Secret
        auth_method = html.request.var("authmethod")
        if auth_method == "secret":
            secret = html.request.get_str_input_mandatory("_auth_secret", "").strip()
            user_attrs["automation_secret"] = secret
            user_attrs["password"] = hash_password(secret)
            increase_serial = True  # password changed, reflect in auth serial

        else:
            password = html.request.get_str_input_mandatory("_password_" + self._pw_suffix(),
                                                            '').strip()
            password2 = html.request.get_str_input_mandatory("_password2_" + self._pw_suffix(),
                                                             '').strip()

            # We compare both passwords only, if the user has supplied
            # the repeation! We are so nice to our power users...
            # Note: this validation is done before the main-validiation later on
            # It doesn't make any sense to put this block into the main validation function
            if password2 and password != password2:
                raise MKUserError("_password2", _("The both passwords do not match."))

            # Detect switch back from automation to password
            if "automation_secret" in user_attrs:
                del user_attrs["automation_secret"]
                if "password" in user_attrs:
                    del user_attrs["password"]  # which was the encrypted automation password!

            if password:
                user_attrs["password"] = hash_password(password)
                user_attrs["last_pw_change"] = int(time.time())
                increase_serial = True  # password changed, reflect in auth serial

            # PW change enforcement
            user_attrs["enforce_pw_change"] = html.get_checkbox("enforce_pw_change")
            if user_attrs["enforce_pw_change"]:
                increase_serial = True  # invalidate all existing user sessions, enforce relogon

        # Increase serial (if needed)
        if increase_serial:
            user_attrs["serial"] = user_attrs.get("serial", 0) + 1

        # Email address
        user_attrs["email"] = EmailAddress().from_html_vars("email")

        idle_timeout = watolib.get_vs_user_idle_timeout().from_html_vars("idle_timeout")
        user_attrs["idle_timeout"] = idle_timeout
        if idle_timeout is not None:
            user_attrs["idle_timeout"] = idle_timeout
        elif idle_timeout is None and "idle_timeout" in user_attrs:
            del user_attrs["idle_timeout"]

        # Pager
        user_attrs["pager"] = html.request.get_str_input_mandatory("pager", '').strip()

        if cmk_version.is_managed_edition():
            customer = self._vs_customer.from_html_vars("customer")
            self._vs_customer.validate_value(customer, "customer")

            if customer != managed.default_customer_id():
                user_attrs["customer"] = customer
            elif "customer" in user_attrs:
                del user_attrs["customer"]

        vs_sites = self._vs_sites()
        authorized_sites = vs_sites.from_html_vars("authorized_sites")
        vs_sites.validate_value(authorized_sites, "authorized_sites")

        if authorized_sites is not None:
            user_attrs["authorized_sites"] = authorized_sites
        elif "authorized_sites" in user_attrs:
            del user_attrs["authorized_sites"]

        # Roles
        user_attrs["roles"] = [
            role for role in self._roles.keys() if html.get_checkbox("role_" + role)
        ]

        # Language configuration
        language = html.request.get_ascii_input_mandatory("language", "")
        if language != "_default_":
            user_attrs["language"] = language
        elif "language" in user_attrs:
            del user_attrs["language"]

        # Contact groups
        cgs = []
        for c in self._contact_groups:
            if html.get_checkbox("cg_" + c):
                cgs.append(c)
        user_attrs["contactgroups"] = cgs

        # Notification settings are only active if we do *not* have
        # rule based notifications!
        if not self._rbn_enabled():
            # Notifications
            user_attrs["notifications_enabled"] = html.get_checkbox("notifications_enabled")

            ntp = html.request.var("notification_period")
            if ntp not in self._timeperiods:
                ntp = "24X7"
            user_attrs["notification_period"] = ntp

            for what, opts in [("host", "durfs"), ("service", "wucrfs")]:
                user_attrs[what + "_notification_options"] = "".join(
                    [opt for opt in opts if html.get_checkbox(what + "_" + opt)])

            value = watolib.get_vs_flexible_notifications().from_html_vars("notification_method")
            user_attrs["notification_method"] = value
        else:
            user_attrs["fallback_contact"] = html.get_checkbox("fallback_contact")

        # Custom user attributes
        for name, attr in userdb.get_user_attributes():
            value = attr.valuespec().from_html_vars('ua_' + name)
            user_attrs[name] = value

        # Generate user "object" to update
        user_object = {self._user_id: {"attributes": user_attrs, "is_new_user": self._is_new_user}}
        # The following call validates and updated the users
        edit_users(user_object)
        return redirect(mode_url("users"))

    def page(self):
        # Let exceptions from loading notification scripts happen now
        watolib.load_notification_scripts()

        html.begin_form("user", method="POST")
        html.prevent_password_auto_completion()

        forms.header(_("Identity"))

        # ID
        forms.section(_("Username"), simple=not self._is_new_user)
        if self._is_new_user:
            vs_user_id = UserID(allow_empty=False)

        else:
            vs_user_id = FixedValue(self._user_id)
        vs_user_id.render_input("user_id", self._user_id)

        def lockable_input(name, dflt):
            if not self._is_locked(name):
                html.text_input(name, self._user.get(name, dflt), size=50)
            else:
                html.write_text(self._user.get(name, dflt))
                html.hidden_field(name, self._user.get(name, dflt))

        # Full name
        forms.section(_("Full name"))
        lockable_input('alias', self._user_id)
        html.help(_("Full name or alias of the user"))

        # Email address
        forms.section(_("Email address"))
        email = self._user.get("email", "")
        if not self._is_locked("email"):
            EmailAddress().render_input("email", email)
        else:
            html.write_text(email)
            html.hidden_field("email", email)

        html.help(
            _("The email address is optional and is needed "
              "if the user is a monitoring contact and receives notifications "
              "via Email."))

        forms.section(_("Pager address"))
        lockable_input('pager', '')
        html.help(_("The pager address is optional "))

        if cmk_version.is_managed_edition():
            forms.section(self._vs_customer.title())
            self._vs_customer.render_input("customer", managed.get_customer_id(self._user))

            html.help(self._vs_customer.help())

        vs_sites = self._vs_sites()
        forms.section(vs_sites.title())
        authorized_sites = self._user.get("authorized_sites", vs_sites.default_value())
        if not self._is_locked("authorized_sites"):
            vs_sites.render_input("authorized_sites", authorized_sites)
        else:
            html.write_html(vs_sites.value_to_text(authorized_sites))
        html.help(vs_sites.help())

        custom_user_attr_topics = userdb_utils.get_user_attributes_by_topic()

        self._show_custom_user_attributes(custom_user_attr_topics.get('ident', []))

        forms.header(_("Security"))
        forms.section(_("Authentication"))

        is_automation = self._user.get("automation_secret", None) is not None
        html.radiobutton("authmethod", "password", not is_automation,
                         _("Normal user login with password"))
        html.open_ul()
        html.open_table()
        html.open_tr()
        html.td(_("password:"))
        html.open_td()

        if not self._is_locked('password'):
            html.password_input("_password_" + self._pw_suffix(), autocomplete="new-password")
            html.close_td()
            html.close_tr()

            html.open_tr()
            html.td(_("repeat:"))
            html.open_td()
            html.password_input("_password2_" + self._pw_suffix(), autocomplete="new-password")
            html.write_text(" (%s)" % _("optional"))
            html.close_td()
            html.close_tr()

            html.open_tr()
            html.td("%s:" % _("Enforce change"))
            html.open_td()
            # Only make password enforcement selection possible when user is allowed to change the PW
            uid = None if self._user_id is None else UserId(self._user_id)
            if (self._is_new_user or (config.user_may(uid, 'general.edit_profile') and
                                      config.user_may(uid, 'general.change_password'))):
                html.checkbox("enforce_pw_change",
                              self._user.get("enforce_pw_change", False),
                              label=_("Change password at next login or access"))
            else:
                html.write_text(
                    _("Not permitted to change the password. Change can not be enforced."))
        else:
            html.i(_('The password can not be changed (It is locked by the user connector).'))
            html.hidden_field('_password', '')
            html.hidden_field('_password2', '')

        html.close_td()
        html.close_tr()
        html.close_table()
        html.close_ul()

        html.radiobutton("authmethod", "secret", is_automation,
                         _("Automation secret for machine accounts"))

        html.open_ul()
        html.text_input("_auth_secret",
                        self._user.get("automation_secret", ""),
                        size=30,
                        id_="automation_secret")
        html.write_text(" ")
        html.open_b(style=["position: relative", "top: 4px;"])
        html.write(" &nbsp;")
        html.icon_button("javascript:cmk.wato.randomize_secret('automation_secret', 20);",
                         _("Create random secret"), "random")
        html.close_b()
        html.close_ul()

        html.help(
            _("If you want the user to be able to login "
              "then specify a password here. Users without a login make sense "
              "if they are monitoring contacts that are just used for "
              "notifications. The repetition of the password is optional. "
              "<br>For accounts used by automation processes (such as fetching "
              "data from views for further procession), set the method to "
              "<u>secret</u>. The secret will be stored in a local file. Processes "
              "with read access to that file will be able to use Multisite as "
              "a webservice without any further configuration."))

        # Locking
        forms.section(_("Disable password"), simple=True)
        if not self._is_locked('locked'):
            html.checkbox("locked",
                          self._user.get("locked", False),
                          label=_("disable the login to this account"))
        else:
            html.write_text(
                _('Login disabled') if self._user.get("locked", False) else _('Login possible'))
            html.hidden_field('locked', '1' if self._user.get("locked", False) else '')
        html.help(
            _("Disabling the password will prevent a user from logging in while "
              "retaining the original password. Notifications are not affected "
              "by this setting."))

        forms.section(_("Idle timeout"))
        idle_timeout = self._user.get("idle_timeout")
        if not self._is_locked("idle_timeout"):
            watolib.get_vs_user_idle_timeout().render_input("idle_timeout", idle_timeout)
        else:
            html.write_text(idle_timeout)
            html.hidden_field("idle_timeout", idle_timeout)

        # Roles
        forms.section(_("Roles"))
        is_member_of_at_least_one = False
        for role_id, role in sorted(self._roles.items(), key=lambda x: (x[1]["alias"], x[0])):
            if not self._is_locked("roles"):
                html.checkbox("role_" + role_id, role_id in self._user.get("roles", []))
                url = watolib.folder_preserving_link([("mode", "edit_role"), ("edit", role_id)])
                html.a(role["alias"], href=url)
                html.br()
            else:
                is_member = role_id in self._user.get("roles", [])
                if is_member:
                    is_member_of_at_least_one = True
                    url = watolib.folder_preserving_link([("mode", "edit_role"), ("edit", role_id)])
                    html.a(role["alias"], href=url)
                    html.br()

                html.hidden_field("role_" + role_id, '1' if is_member else '')
        if self._is_locked('roles') and not is_member_of_at_least_one:
            html.i(_('No roles assigned.'))
        self._show_custom_user_attributes(custom_user_attr_topics.get('security', []))

        # Contact groups
        forms.header(_("Contact Groups"), isopen=False)
        forms.section()
        groups_page_url = watolib.folder_preserving_link([("mode", "contact_groups")])
        group_assign_url = watolib.folder_preserving_link([("mode", "rulesets"),
                                                           ("group", "grouping")])
        if not self._contact_groups:
            html.write(
                _("Please first create some <a href='%s'>contact groups</a>") % groups_page_url)
        else:
            entries = sorted([(group['alias'] or c, c) for c, group in self._contact_groups.items()
                             ])
            is_member_of_at_least_one = False
            for alias, gid in entries:
                is_member = gid in self._user.get("contactgroups", [])

                if not self._is_locked('contactgroups'):
                    html.checkbox("cg_" + gid, gid in self._user.get("contactgroups", []))
                else:
                    if is_member:
                        is_member_of_at_least_one = True
                    html.hidden_field("cg_" + gid, '1' if is_member else '')

                if not self._is_locked('contactgroups') or is_member:
                    url = watolib.folder_preserving_link([("mode", "edit_contact_group"),
                                                          ("edit", gid)])
                    html.a(alias, href=url)
                    html.br()

            if self._is_locked('contactgroups') and not is_member_of_at_least_one:
                html.i(_('No contact groups assigned.'))

        html.help(
            _("Contact groups are used to assign monitoring "
              "objects to users. If you haven't defined any contact groups yet, "
              "then first <a href='%s'>do so</a>. Hosts and services can be "
              "assigned to contact groups using <a href='%s'>rules</a>.<br><br>"
              "If you do not put the user into any contact group "
              "then no monitoring contact will be created for the user.") %
            (groups_page_url, group_assign_url))

        forms.header(_("Notifications"), isopen=False)
        if not self._rbn_enabled():
            forms.section(_("Enabling"), simple=True)
            html.checkbox("notifications_enabled",
                          self._user.get("notifications_enabled", False),
                          label=_("enable notifications"))
            html.help(
                _("Notifications are sent out "
                  "when the status of a host or service changes."))

            # Notification period
            forms.section(_("Notification time period"))
            user_np = self._user.get("notification_period")
            if not isinstance(user_np, str):
                raise Exception("invalid notification period %r" % (user_np,))
            choices: Choices = [
                (id_, "%s" % (tp["alias"])) for (id_, tp) in self._timeperiods.items()
            ]
            html.dropdown("notification_period", choices, deflt=user_np, ordered=True)
            html.help(
                _("Only during this time period the "
                  "user will get notifications about host or service alerts."))

            # Notification options
            notification_option_names = {  # defined here: _() must be executed always!
                "host": {
                    "d": _("Host goes down"),
                    "u": _("Host gets unreachble"),
                    "r": _("Host goes up again"),
                },
                "service": {
                    "w": _("Service goes into warning state"),
                    "u": _("Service goes into unknown state"),
                    "c": _("Service goes into critical state"),
                    "r": _("Service recovers to OK"),
                },
                "both": {
                    "f": _("Start or end of flapping state"),
                    "s": _("Start or end of a scheduled downtime"),
                }
            }

            forms.section(_("Notification Options"))
            for title, what, opts in [(_("Host events"), "host", "durfs"),
                                      (_("Service events"), "service", "wucrfs")]:
                html.write_text("%s:" % title)
                html.open_ul()

                user_opts = self._user.get(what + "_notification_options", opts)
                for opt in opts:
                    opt_name = notification_option_names[what].get(
                        opt, notification_option_names["both"].get(opt))
                    html.checkbox(what + "_" + opt, opt in user_opts, label=opt_name)
                    html.br()
                html.close_ul()

            html.help(
                _("Here you specify which types of alerts "
                  "will be notified to this contact. Note: these settings will only be saved "
                  "and used if the user is member of a contact group."))

            forms.section(_("Notification Method"))
            watolib.get_vs_flexible_notifications().render_input(
                "notification_method", self._user.get("notification_method"))

        else:
            forms.section(_("Fallback notifications"), simple=True)

            html.checkbox("fallback_contact",
                          self._user.get("fallback_contact", False),
                          label=_("Receive fallback notifications"))

            html.help(
                _("In case none of your notification rules handles a certain event a notification "
                  "will be sent to this contact. This makes sure that in that case at least <i>someone</i> "
                  "gets notified. Furthermore this contact will be used for notifications to any host or service "
                  "that is not known to the monitoring. This can happen when you forward notifications "
                  "from the Event Console.<br><br>Notification fallback can also configured in the global "
                  "setting <a href=\"wato.py?mode=edit_configvar&varname=notification_fallback_email\">"
                  "Fallback email address for notifications</a>."))

        self._show_custom_user_attributes(custom_user_attr_topics.get('notify', []))

        forms.header(_("Personal settings"), isopen=False)
        select_language(self._user)
        self._show_custom_user_attributes(custom_user_attr_topics.get('personal', []))
        forms.header(_("Interface settings"), isopen=False)
        self._show_custom_user_attributes(custom_user_attr_topics.get('interface', []))

        # Later we could add custom macros here, which then could be used
        # for notifications. On the other hand, if we implement some check_mk
        # --notify, we could directly access the data in the account with the need
        # to store values in the monitoring core. We'll see what future brings.
        forms.end()
        if self._is_new_user:
            html.set_focus("user_id")
        else:
            html.set_focus("alias")
        html.hidden_fields()
        html.end_form()

    def _rbn_enabled(self):
        # Check if rule based notifications are enabled (via WATO)
        return rulebased_notifications_enabled()

    def _pw_suffix(self) -> str:
        if self._is_new_user:
            return 'new'
        # mypy complaines that None has no attribute "encode" and
        # "bytes", expected "str"
        assert self._user_id is not None
        return str(base64.b64encode(self._user_id.encode("utf-8")))

    def _is_locked(self, attr):
        """Returns true if an attribute is locked and should be read only. Is only
        checked when modifying an existing user"""
        return not self._is_new_user and attr in self._locked_attributes

    def _vs_sites(self):
        return Alternative(
            title=_("Authorized sites"),
            help=_("The sites the user is authorized to see in the GUI."),
            default_value=None,
            elements=[
                FixedValue(
                    None,
                    title=_("All sites"),
                    totext=_("May see all sites"),
                ),
                DualListChoice(
                    title=_("Specific sites"),
                    choices=config.site_choices,
                ),
            ],
        )

    def _show_custom_user_attributes(self, custom_attr):
        for name, attr in custom_attr:
            vs = attr.valuespec()
            forms.section(_u(vs.title()))
            if not self._is_locked(name):
                vs.render_input("ua_" + name, self._user.get(name, vs.default_value()))
            else:
                html.write(vs.value_to_text(self._user.get(name, vs.default_value())))
                # Render hidden to have the values kept after saving
                html.open_div(style="display:none")
                vs.render_input("ua_" + name, self._user.get(name, vs.default_value()))
                html.close_div()
            html.help(_u(vs.help()))


def select_language(user):
    languages: Choices = [l for l in get_languages() if not config.hide_language(l[0])]
    if not languages:
        return

    current_language = user.get("language")
    if current_language is None:
        current_language = "_default_"

    languages.insert(0, ("_default_", _("Use the default language (%s)") %
                         get_language_alias(config.default_language)))

    forms.section(_("Language"))
    html.dropdown("language", languages, deflt=current_language)
    html.help(_('Configure the language to be used by the user in the user interface here.'))
