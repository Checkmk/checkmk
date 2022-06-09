#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Modes for managing users and contacts"""

import base64
import time
import traceback
from typing import cast, Iterator, List, Optional, overload, Tuple, Type, Union

import cmk.utils.render as render
import cmk.utils.version as cmk_version
from cmk.utils.type_defs import timeperiod_spec_alias, UserId

import cmk.gui.background_job as background_job
import cmk.gui.forms as forms
import cmk.gui.gui_background_job as gui_background_job
import cmk.gui.plugins.userdb.utils as userdb_utils
import cmk.gui.userdb as userdb
import cmk.gui.watolib as watolib
from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.config import active_config
from cmk.gui.exceptions import MKUserError
from cmk.gui.groups import load_contact_group_information
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _, _u, get_language_alias, get_languages
from cmk.gui.log import logger
from cmk.gui.logged_in import user
from cmk.gui.page_menu import (
    make_checkbox_selection_json_text,
    make_checkbox_selection_topic,
    make_confirmed_form_submit_link,
    make_simple_form_page_menu,
    make_simple_link,
    PageMenu,
    PageMenuDropdown,
    PageMenuEntry,
    PageMenuSearch,
    PageMenuTopic,
)
from cmk.gui.plugins.userdb.htpasswd import hash_password
from cmk.gui.plugins.userdb.utils import get_connection, UserAttribute
from cmk.gui.plugins.wato.utils import (
    flash,
    make_confirm_link,
    mode_registry,
    mode_url,
    redirect,
    WatoMode,
)
from cmk.gui.table import table_element
from cmk.gui.type_defs import ActionResult, Choices, PermissionName, UserSpec
from cmk.gui.user_sites import get_configured_site_choices
from cmk.gui.utils.escaping import escape_to_html
from cmk.gui.utils.html import HTML
from cmk.gui.utils.ntop import get_ntop_connection_mandatory, is_ntop_available
from cmk.gui.utils.roles import user_may
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.utils.urls import makeactionuri, makeuri, makeuri_contextless
from cmk.gui.valuespec import Alternative, DualListChoice, EmailAddress, FixedValue, UserID
from cmk.gui.watolib.audit_log_url import make_object_audit_log_url
from cmk.gui.watolib.global_settings import rulebased_notifications_enabled
from cmk.gui.watolib.hosts_and_folders import folder_preserving_link, make_action_link
from cmk.gui.watolib.user_scripts import load_notification_scripts
from cmk.gui.watolib.users import (
    delete_users,
    edit_users,
    get_vs_flexible_notifications,
    get_vs_user_idle_timeout,
    make_user_object_ref,
)

if cmk_version.is_managed_edition():
    import cmk.gui.cme.managed as managed  # pylint: disable=no-name-in-module
else:
    managed = None  # type: ignore[assignment]


@mode_registry.register
class ModeUsers(WatoMode):
    @classmethod
    def name(cls) -> str:
        return "users"

    @classmethod
    def permissions(cls) -> list[PermissionName]:
        return ["users"]

    def __init__(self) -> None:
        super().__init__()
        self._job = userdb.UserSyncBackgroundJob()
        self._job_snapshot = userdb.UserSyncBackgroundJob().get_status_snapshot()

    def title(self) -> str:
        return _("Users")

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        # Remove the last breadcrumb entry here to avoid the breadcrumb "Users > Users"
        del breadcrumb[-1]
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
                                        folder_preserving_link([("mode", "edit_user")])
                                    ),
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
                                            "Do you really want to delete the selected users?"
                                        ),
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
                            title=_("User messages"),
                            entries=list(self._page_menu_entries_user_messages()),
                        ),
                        make_checkbox_selection_topic(self.name()),
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

    def _page_menu_entries_synchronized_users(self) -> Iterator[PageMenuEntry]:
        if userdb.sync_possible():
            if not self._job_snapshot.is_active():
                yield PageMenuEntry(
                    title=_("Synchronize users"),
                    icon_name="replicate",
                    item=make_simple_link(makeactionuri(request, transactions, [("_sync", 1)])),
                )

                yield PageMenuEntry(
                    title=_("Last synchronization result"),
                    icon_name="background_job_details",
                    item=make_simple_link(self._job.detail_url()),
                )

    def _page_menu_entries_user_messages(self) -> Iterator[PageMenuEntry]:
        if user.may("general.message"):
            yield PageMenuEntry(
                title=_("Send user messages"),
                icon_name="message",
                item=make_simple_link("message.py"),
            )

    def _page_menu_entries_related(self) -> Iterator[PageMenuEntry]:
        if user.may("wato.custom_attributes"):
            yield PageMenuEntry(
                title=_("Custom attributes"),
                icon_name="custom_attr",
                item=make_simple_link(folder_preserving_link([("mode", "user_attrs")])),
            )

        yield PageMenuEntry(
            title=_("LDAP & Active Directory"),
            icon_name="ldap",
            item=make_simple_link(folder_preserving_link([("mode", "ldap_config")])),
        )

    def action(self) -> ActionResult:
        if not transactions.check_transaction():
            return redirect(self.mode_url())

        if request.var("_delete"):
            delete_users([request.get_str_input("_delete")])
            return redirect(self.mode_url())

        if request.var("_sync"):
            try:

                job = userdb.UserSyncBackgroundJob()
                job.set_function(
                    job.do_sync,
                    add_to_changelog=True,
                    enforce_sync=True,
                    load_users_func=userdb.load_users,
                    save_users_func=userdb.save_users,
                )

                try:
                    job.start()
                except background_job.BackgroundJobAlreadyRunning as e:
                    raise MKUserError(
                        None, _("Another synchronization job is already running: %s") % e
                    )

                self._job_snapshot = job.get_status_snapshot()
            except Exception:
                logger.exception("error syncing users")
                raise MKUserError(None, traceback.format_exc().replace("\n", "<br>\n"))
            return redirect(self.mode_url())

        if request.var("_bulk_delete_users"):
            self._bulk_delete_users_after_confirm()
            return redirect(self.mode_url())

        action_handler = gui_background_job.ActionHandler(self.breadcrumb())
        action_handler.handle_actions()
        if action_handler.did_acknowledge_job():
            self._job_snapshot = userdb.UserSyncBackgroundJob().get_status_snapshot()
            flash(_("Synchronization job acknowledged"))
            return redirect(self.mode_url())

        return None

    def _bulk_delete_users_after_confirm(self):
        selected_users = []
        users = userdb.load_users()
        for varname, _value in request.itervars(prefix="_c_user_"):
            if html.get_checkbox(varname):
                user_id = base64.b64decode(varname.split("_c_user_")[-1].encode("utf-8")).decode(
                    "utf-8"
                )
                if user_id in users:
                    selected_users.append(user_id)

        if selected_users:
            delete_users(selected_users)

    def page(self) -> None:
        if not self._job_snapshot.exists():
            # Skip if snapshot doesnt exists
            pass

        elif self._job_snapshot.is_active():
            # Still running
            html.show_message(
                HTML(_("User synchronization currently running: ")) + self._job_details_link()
            )
            url = makeuri(request, [])
            html.immediate_browser_redirect(2, url)

        elif (
            self._job_snapshot.state() == gui_background_job.background_job.JobStatusStates.FINISHED
            and not self._job_snapshot.acknowledged_by()
        ):
            # Just finished, auto-acknowledge
            userdb.UserSyncBackgroundJob().acknowledge(user.id)
            # html.show_message(_("User synchronization successful"))

        elif not self._job_snapshot.acknowledged_by() and self._job_snapshot.has_exception():
            # Finished, but not OK - show info message with links to details
            html.show_warning(
                HTML(_("Last user synchronization ran into an exception: "))
                + self._job_details_link()
            )

        self._show_user_list()

    def _job_details_link(self):
        return HTMLWriter.render_a("%s" % self._job.get_title(), href=self._job.detail_url())

    def _job_details_url(self):
        return makeuri_contextless(
            request,
            [
                ("mode", "background_job_details"),
                ("back_url", makeuri_contextless(request, [("mode", "users")])),
                ("job_id", self._job_snapshot.get_job_id()),
            ],
            filename="wato.py",
        )

    def _show_job_info(self):
        if self._job_snapshot.is_active():
            html.h3(_("Current status of synchronization process"))
            html.browser_reload = 0.8
        else:
            html.h3(_("Result of last synchronization process"))

        job_manager = gui_background_job.GUIBackgroundJobManager()
        job_manager.show_job_details_from_snapshot(job_snapshot=self._job_snapshot)
        html.br()

    def _show_user_list(self) -> None:
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
            online_threshold = time.time() - active_config.user_online_maxage
            for uid, user_spec in sorted(entries, key=lambda x: x[1].get("alias", x[0]).lower()):
                table.row()

                # Checkboxes
                table.cell(
                    html.render_input(
                        "_toggle_group",
                        type_="button",
                        class_="checkgroup",
                        onclick="cmk.selection.toggle_all_rows(this.form, %s, %s);"
                        % make_checkbox_selection_json_text(),
                        value="X",
                    ),
                    sortable=False,
                    css=["checkbox"],
                )

                if uid != user.id:
                    html.checkbox("_c_user_%s" % base64.b64encode(uid.encode("utf-8")).decode())

                user_connection_id = user_spec.get("connector")
                connection = get_connection(user_connection_id)

                # Buttons
                table.cell(_("Actions"), css=["buttons"])
                if connection:  # only show edit buttons when the connector is available and enabled
                    edit_url = folder_preserving_link([("mode", "edit_user"), ("edit", uid)])
                    html.icon_button(edit_url, _("Properties"), "edit")

                    clone_url = folder_preserving_link([("mode", "edit_user"), ("clone", uid)])
                    html.icon_button(clone_url, _("Create a copy of this user"), "clone")

                delete_url = make_confirm_link(
                    url=make_action_link([("mode", "users"), ("_delete", uid)]),
                    message=_("Do you really want to delete the user %s?") % uid,
                )
                html.icon_button(delete_url, _("Delete"), "delete")

                if rulebased_notifications_enabled():
                    notifications_url = folder_preserving_link(
                        [("mode", "user_notifications"), ("user", uid)]
                    )
                    html.icon_button(
                        notifications_url,
                        _("Custom notification table of this user"),
                        "notifications",
                    )

                # ID
                table.cell(_("ID"), uid)

                # Online/Offline
                if user.may("wato.show_last_user_activity"):
                    last_seen = userdb.get_last_activity(user_spec)
                    if last_seen >= online_threshold:
                        title = _("Online")
                        img_txt = "online"
                    elif last_seen != 0:
                        title = _("Offline")
                        img_txt = "offline"
                    elif last_seen == 0:
                        title = _("Never logged in")
                        img_txt = "inactive"

                    title += " (%s %s)" % (render.date(last_seen), render.time_of_day(last_seen))
                    table.cell(_("Act."))
                    html.icon(img_txt, title)

                    table.cell(_("Last seen"))
                    if last_seen != 0:
                        html.write_text(
                            "%s %s" % (render.date(last_seen), render.time_of_day(last_seen))
                        )
                    else:
                        html.write_text(_("Never logged in"))

                if cmk_version.is_managed_edition():
                    table.cell(_("Customer"), managed.get_customer_name(user_spec))

                # Connection
                if connection:
                    table.cell(
                        _("Connection"), "%s (%s)" % (connection.short_title(), user_connection_id)
                    )
                    locked_attributes = userdb.locked_attributes(user_connection_id)
                else:
                    table.cell(
                        _("Connection"),
                        "%s (%s) (%s)" % (_("UNKNOWN"), user_connection_id, _("disabled")),
                        css=["error"],
                    )
                    locked_attributes = []

                # Authentication
                if "automation_secret" in user_spec:
                    auth_method: Union[str, HTML] = _("Automation")
                elif user_spec.get("password") or "password" in locked_attributes:
                    auth_method = _("Password")
                    if _is_two_factor_enabled(user_spec):
                        auth_method += " (+2FA)"
                else:
                    auth_method = HTMLWriter.render_i(_("none"))
                table.cell(_("Authentication"), auth_method)

                table.cell(_("State"), sortable=False)
                if user_spec.get("locked", False):
                    html.icon("user_locked", _("The login is currently locked"))

                if "disable_notifications" in user_spec and isinstance(
                    user_spec["disable_notifications"], bool
                ):
                    disable_notifications_opts = {"disable": user_spec["disable_notifications"]}
                else:
                    disable_notifications_opts = user_spec.get("disable_notifications", {})

                if disable_notifications_opts.get("disable", False):
                    html.icon("notif_disabled", _("Notifications are disabled"))

                # Full name / Alias
                table.cell(_("Alias"), user_spec.get("alias", ""))

                # Email
                table.cell(_("Email"), user_spec.get("email", ""))

                # Roles
                table.cell(_("Roles"))
                if user_spec.get("roles", []):
                    role_links = [
                        (
                            folder_preserving_link([("mode", "edit_role"), ("edit", role)]),
                            roles[role].get("alias"),
                        )
                        for role in user_spec["roles"]
                    ]
                    html.write_html(
                        HTML(", ").join(
                            HTMLWriter.render_a(alias, href=link) for (link, alias) in role_links
                        )
                    )

                # contact groups
                table.cell(_("Contact groups"))
                cgs = user_spec.get("contactgroups", [])
                if cgs:
                    cg_aliases = [
                        contact_groups[c]["alias"] if c in contact_groups else c for c in cgs
                    ]
                    cg_urls = [
                        folder_preserving_link([("mode", "edit_contact_group"), ("edit", c)])
                        for c in cgs
                    ]
                    html.write_html(
                        HTML(", ").join(
                            HTMLWriter.render_a(content, href=url)
                            for (content, url) in zip(cg_aliases, cg_urls)
                        )
                    )
                else:
                    html.i(_("none"))

                # table.cell(_("Sites"))
                # html.write_text(vs_authorized_sites().value_to_html(user_spec.get("authorized_sites",
                #                                                vs_authorized_sites().default_value())))

                # notifications
                if not rulebased_notifications_enabled():
                    table.cell(_("Notifications"))
                    if not cgs:
                        html.i(_("not a contact"))
                    elif not user_spec.get("notifications_enabled", True):
                        html.write_text(_("disabled"))
                    elif (
                        user_spec.get("host_notification_options", "") == ""
                        and user_spec.get("service_notification_options", "") == ""
                    ):
                        html.write_text(_("all events disabled"))
                    else:
                        tp = user_spec.get("notification_period", "24X7")
                        tp_code = HTML()
                        if tp not in timeperiods:
                            tp_code = escape_to_html(tp + _(" (invalid)"))
                        elif tp not in watolib.timeperiods.builtin_timeperiods():
                            url = folder_preserving_link(
                                [("mode", "edit_timeperiod"), ("edit", tp)]
                            )
                            tp_code = HTMLWriter.render_a(
                                timeperiod_spec_alias(timeperiods[tp], tp), href=url
                            )
                        else:
                            tp_code = escape_to_html(timeperiod_spec_alias(timeperiods[tp], tp))
                        html.write_html(tp_code)

                # the visible custom attributes
                for name, attr in visible_custom_attrs:
                    vs = attr.valuespec()
                    vs_title = vs.title()
                    table.cell(_u(vs_title) if isinstance(vs_title, str) else vs_title)
                    html.write_text(vs.value_to_html(user_spec.get(name, vs.default_value())))

        html.hidden_fields()
        html.end_form()

        if not load_contact_group_information():
            url = "wato.py?mode=contact_groups"
            html.open_div(class_="info")
            html.write_text(
                _(
                    "Note: you haven't defined any contact groups yet. If you <a href='%s'>"
                    "create some contact groups</a> you can assign users to them und thus "
                    "make them monitoring contacts. Only monitoring contacts can receive "
                    "notifications."
                )
                % url
            )
            html.write_text(
                " you can assign users to them und thus "
                "make them monitoring contacts. Only monitoring contacts can receive "
                "notifications."
            )
            html.close_div()


# TODO: Create separate ModeCreateUser()
# TODO: Move CME specific stuff to CME related class
# TODO: Refactor action / page to use less hand crafted logic (valuespecs instead?)
@mode_registry.register
class ModeEditUser(WatoMode):
    @classmethod
    def name(cls) -> str:
        return "edit_user"

    @classmethod
    def permissions(cls) -> list[PermissionName]:
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

    def __init__(self) -> None:
        super().__init__()

        # Load data that is referenced - in order to display dropdown
        # boxes and to check for validity.
        self._contact_groups = load_contact_group_information()
        self._timeperiods = watolib.timeperiods.load_timeperiods()
        self._roles = userdb_utils.load_roles()

        if cmk_version.is_managed_edition():
            self._vs_customer = managed.vs_customer()

    def _from_vars(self):
        # TODO: Should we turn the both fields below into Optional[UserId]?
        self._user_id = request.get_str_input("edit")  # missing -> new user
        # This is needed for the breadcrumb computation:
        # When linking from user notification rules page the request variable is "user"
        # instead of "edit". We should also change that variable to "user" on this page,
        # then we can simply use self._user_id.
        if not self._user_id and request.has_var("user"):
            self._user_id = request.get_str_input_mandatory("user")

        self._cloneid = request.get_str_input("clone")  # Only needed in 'new' mode
        # TODO: Nuke the field below? It effectively hides facts about _user_id for mypy.
        self._is_new_user = self._user_id is None
        self._users = userdb.load_users(lock=transactions.is_transaction())
        new_user = userdb.new_user_template("htpasswd")
        if self._user_id is not None:
            self._user = self._users.get(UserId(self._user_id), new_user)
        elif self._cloneid:
            self._user = self._users.get(UserId(self._cloneid), new_user)
        else:
            self._user = new_user
        self._locked_attributes = userdb.locked_attributes(self._user.get("connector"))

    def title(self) -> str:
        if self._is_new_user:
            return _("Add user")
        return _("Edit user %s") % self._user_id

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        menu = make_simple_form_page_menu(
            _("User"), breadcrumb, form_name="user", button_name="_save"
        )

        action_dropdown = menu.dropdowns[0]
        action_dropdown.topics.append(
            PageMenuTopic(
                title=_("This user"),
                entries=list(self._page_menu_entries_this_user()),
            )
        )

        return menu

    def _page_menu_entries_this_user(self) -> Iterator[PageMenuEntry]:
        if self._rbn_enabled and not self._is_new_user:
            yield PageMenuEntry(
                title=_("Notification rules"),
                icon_name="topic_events",
                item=make_simple_link(
                    folder_preserving_link(
                        [("mode", "user_notifications"), ("user", self._user_id)]
                    )
                ),
            )

        if user.may("wato.auditlog") and not self._is_new_user:
            assert self._user_id is not None
            yield PageMenuEntry(
                title=_("Audit log"),
                icon_name="auditlog",
                item=make_simple_link(
                    make_object_audit_log_url(make_user_object_ref(UserId(self._user_id)))
                ),
            )

        if not self._is_new_user:
            yield PageMenuEntry(
                title=_("Disable two-factor authentication"),
                icon_name="2fa",
                item=make_simple_link(
                    make_confirm_link(
                        url=make_action_link(
                            [
                                ("mode", "edit_user"),
                                ("user", self._user_id),
                                ("_disable_two_factor", "1"),
                            ]
                        ),
                        message=_(
                            "Do you really want to disable the two-factor authentication of %s?"
                        )
                        % self._user_id,
                    )
                ),
                is_enabled=_is_two_factor_enabled(self._user),
            )

    def action(self) -> ActionResult:
        if not transactions.check_transaction():
            return redirect(mode_url("users"))

        if self._user_id is not None and request.has_var("_disable_two_factor"):
            userdb.disable_two_factor_authentication(UserId(self._user_id))
            return redirect(mode_url("users"))

        if self._user_id is None:  # same as self._is_new_user
            self._user_id = UserID(allow_empty=False).from_html_vars("user_id")
            user_attrs: UserSpec = {}
        else:
            self._user_id = request.get_str_input_mandatory("edit").strip()
            user_attrs = self._users[UserId(self._user_id)].copy()

        # Full name
        user_attrs["alias"] = request.get_str_input_mandatory("alias").strip()

        # Connector
        user_attrs["connector"] = self._user.get("connector")

        # Locking
        user_attrs["locked"] = html.get_checkbox("locked")
        increase_serial = False

        if (
            UserId(self._user_id) in self._users
            and user_attrs["locked"]
            and self._users[UserId(self._user_id)]["locked"] != user_attrs["locked"]
        ):
            increase_serial = True  # when user is being locked now, increase the auth serial

        # Authentication: Password or Secret
        auth_method = request.var("authmethod")
        if auth_method == "secret":
            secret = request.get_str_input_mandatory("_auth_secret", "").strip()
            if secret:
                user_attrs["automation_secret"] = secret
                user_attrs["password"] = hash_password(secret)
                increase_serial = True  # password changed, reflect in auth serial
            elif "automation_secret" not in user_attrs and "password" in user_attrs:
                del user_attrs["password"]

        else:
            password = request.get_str_input_mandatory("_password_" + self._pw_suffix(), "").strip()
            password2 = request.get_str_input_mandatory(
                "_password2_" + self._pw_suffix(), ""
            ).strip()

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

        idle_timeout = get_vs_user_idle_timeout().from_html_vars("idle_timeout")
        user_attrs["idle_timeout"] = idle_timeout
        if idle_timeout is None:
            del user_attrs["idle_timeout"]

        # Pager
        user_attrs["pager"] = request.get_str_input_mandatory("pager", "").strip()

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

        # ntopng
        if is_ntop_available():
            ntop_connection = get_ntop_connection_mandatory()
            # ntop_username_attribute will be the name of the custom attribute or false
            # see corresponding WATO rule
            ntop_username_attribute = ntop_connection.get("use_custom_attribute_as_ntop_username")
            if ntop_username_attribute:
                # TODO: Dynamically fiddling around with a TypedDict is a bit questionable
                user_attrs[ntop_username_attribute] = request.get_str_input_mandatory(  # type: ignore[literal-required]
                    ntop_username_attribute
                )

        # Roles
        user_attrs["roles"] = [
            role for role in self._roles.keys() if html.get_checkbox("role_" + role)
        ]

        # Language configuration
        language = request.get_ascii_input_mandatory("language", "")
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

            ntp = request.var("notification_period")
            user_attrs["notification_period"] = (
                ntp if ntp is not None and ntp in self._timeperiods else "24X7"
            )

            user_attrs["host_notification_options"] = "".join(
                [opt for opt in "durfs" if html.get_checkbox("host_" + opt)]
            )
            user_attrs["service_notification_options"] = "".join(
                [opt for opt in "wucrfs" if html.get_checkbox("service_" + opt)]
            )

            value = get_vs_flexible_notifications().from_html_vars("notification_method")
            user_attrs["notification_method"] = value
        else:
            user_attrs["fallback_contact"] = html.get_checkbox("fallback_contact")

        # Custom user attributes
        for name, attr in userdb.get_user_attributes():
            value = attr.valuespec().from_html_vars("ua_" + name)
            # TODO: Dynamically fiddling around with a TypedDict is a bit questionable
            user_attrs[name] = value  # type: ignore[literal-required]

        # Generate user "object" to update
        user_object = {self._user_id: {"attributes": user_attrs, "is_new_user": self._is_new_user}}
        # The following call validates and updated the users
        edit_users(user_object)
        return redirect(mode_url("users"))

    def page(self) -> None:
        # Let exceptions from loading notification scripts happen now
        load_notification_scripts()

        html.begin_form("user", method="POST")
        html.prevent_password_auto_completion()

        forms.header(_("Identity"))

        # ID
        forms.section(_("Username"), simple=not self._is_new_user, is_required=True)
        if self._is_new_user:
            vs_user_id = UserID(allow_empty=False)

        else:
            vs_user_id = FixedValue(value=self._user_id)
        vs_user_id.render_input("user_id", self._user_id)

        def lockable_input(name: str, dflt: Optional[str]) -> None:
            # TODO: The cast is a big fat lie: value can be None, but things somehow seem to "work" even then. :-/
            value = cast(str, self._user.get(name, dflt))
            if self._is_locked(name):
                html.write_text(value)
                html.hidden_field(name, value)
            else:
                html.text_input(name, value, size=50)

        # Full name
        forms.section(_("Full name"), is_required=True)
        lockable_input("alias", self._user_id)
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
            _(
                "The email address is optional and is needed "
                "if the user is a monitoring contact and receives notifications "
                "via Email."
            )
        )

        forms.section(_("Pager address"))
        lockable_input("pager", "")
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
            html.write_text(vs_sites.value_to_html(authorized_sites))
        html.help(vs_sites.help())

        custom_user_attr_topics = userdb_utils.get_user_attributes_by_topic()

        self._show_custom_user_attributes(custom_user_attr_topics.get("ident", []))

        # ntopng
        if is_ntop_available():
            ntop_connection = get_ntop_connection_mandatory()
            # ntop_username_attribute will be the name of the custom attribute or false
            # see corresponding WATO rule
            ntop_username_attribute = ntop_connection.get("use_custom_attribute_as_ntop_username")
            if ntop_username_attribute:
                forms.section(_("ntopng Username"))
                lockable_input(ntop_username_attribute, "")
                html.help(
                    _(
                        "The corresponding username in ntopng of the current checkmk user. "
                        "It is used, in case the user mapping to ntopng is configured to use this "
                        "custom attribute"
                    )
                )

        forms.header(_("Security"))
        forms.section(_("Authentication"))

        is_automation = self._user.get("automation_secret", None) is not None
        html.radiobutton(
            "authmethod", "password", not is_automation, _("Normal user login with password")
        )
        html.open_ul()
        html.open_table()
        html.open_tr()
        html.td(_("password:"))
        html.open_td()

        if not self._is_locked("password"):
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
            if self._is_new_user or (
                user_may(uid, "general.edit_profile") and user_may(uid, "general.change_password")
            ):
                html.checkbox(
                    "enforce_pw_change",
                    bool(self._user.get("enforce_pw_change")),
                    label=_("Change password at next login or access"),
                )
            else:
                html.write_text(
                    _("Not permitted to change the password. Change can not be enforced.")
                )
        else:
            html.i(_("The password can not be changed (It is locked by the user connector)."))
            html.hidden_field("_password", "")
            html.hidden_field("_password2", "")

        html.close_td()
        html.close_tr()
        html.close_table()
        html.close_ul()

        html.radiobutton(
            "authmethod", "secret", is_automation, _("Automation secret for machine accounts")
        )

        html.open_ul()
        html.text_input(
            "_auth_secret",
            "",
            size=30,
            id_="automation_secret",
            placeholder="******" if "automation_secret" in self._user else "",
        )
        html.write_text(" ")
        html.open_b(style=["position: relative", "top: 4px;"])
        html.write_text(" &nbsp;")
        html.icon_button(
            "javascript:cmk.wato.randomize_secret('automation_secret', 20);",
            _("Create random secret"),
            "random",
        )
        html.close_b()
        html.close_ul()

        html.help(
            _(
                "If you want the user to be able to login "
                "then specify a password here. Users without a login make sense "
                "if they are monitoring contacts that are just used for "
                "notifications. The repetition of the password is optional. "
                "<br>For accounts used by automation processes (such as fetching "
                "data from views for further procession), set the method to "
                "<u>secret</u>. The secret will be stored in a local file. Processes "
                "with read access to that file will be able to use Multisite as "
                "a webservice without any further configuration."
            )
        )

        # Locking
        forms.section(_("Disable password"), simple=True)
        if not self._is_locked("locked"):
            html.checkbox(
                "locked",
                bool(self._user.get("locked")),
                label=_("disable the login to this account"),
            )
        else:
            html.write_text(
                _("Login disabled") if self._user.get("locked", False) else _("Login possible")
            )
            html.hidden_field("locked", "1" if self._user.get("locked", False) else "")
        html.help(
            _(
                "Disabling the password will prevent a user from logging in while "
                "retaining the original password. Notifications are not affected "
                "by this setting."
            )
        )

        forms.section(_("Idle timeout"))
        idle_timeout = self._user.get("idle_timeout")
        if not self._is_locked("idle_timeout"):
            get_vs_user_idle_timeout().render_input("idle_timeout", idle_timeout)
        else:
            html.write_text(idle_timeout)
            html.hidden_field("idle_timeout", idle_timeout)

        # Roles
        forms.section(_("Roles"))
        is_member_of_at_least_one = False
        for role_id, role in sorted(self._roles.items(), key=lambda x: (x[1]["alias"], x[0])):
            if not self._is_locked("roles"):
                html.checkbox("role_" + role_id, role_id in self._user.get("roles", []))
                url = folder_preserving_link([("mode", "edit_role"), ("edit", role_id)])
                html.a(role["alias"], href=url)
                html.br()
            else:
                is_member = role_id in self._user.get("roles", [])
                if is_member:
                    is_member_of_at_least_one = True
                    url = folder_preserving_link([("mode", "edit_role"), ("edit", role_id)])
                    html.a(role["alias"], href=url)
                    html.br()

                html.hidden_field("role_" + role_id, "1" if is_member else "")
        if self._is_locked("roles") and not is_member_of_at_least_one:
            html.i(_("No roles assigned."))
        self._show_custom_user_attributes(custom_user_attr_topics.get("security", []))

        # Contact groups
        forms.header(_("Contact Groups"), isopen=False)
        forms.section()
        groups_page_url = folder_preserving_link([("mode", "contact_groups")])
        hosts_assign_url = folder_preserving_link(
            [
                ("mode", "edit_ruleset"),
                ("varname", "host_contactgroups"),
            ]
        )
        services_assign_url = folder_preserving_link(
            [
                ("mode", "edit_ruleset"),
                ("varname", "service_contactgroups"),
            ]
        )

        if not self._contact_groups:
            html.write_text(
                _("Please first create some <a href='%s'>contact groups</a>") % groups_page_url
            )
        else:
            entries = sorted(
                [(group["alias"] or c, c) for c, group in self._contact_groups.items()]
            )
            is_member_of_at_least_one = False
            for alias, gid in entries:
                is_member = gid in self._user.get("contactgroups", [])

                if not self._is_locked("contactgroups"):
                    html.checkbox("cg_" + gid, gid in self._user.get("contactgroups", []))
                else:
                    if is_member:
                        is_member_of_at_least_one = True
                    html.hidden_field("cg_" + gid, "1" if is_member else "")

                if not self._is_locked("contactgroups") or is_member:
                    url = folder_preserving_link([("mode", "edit_contact_group"), ("edit", gid)])
                    html.a(alias, href=url)
                    html.br()

            if self._is_locked("contactgroups") and not is_member_of_at_least_one:
                html.i(_("No contact groups assigned."))

        html.help(
            _(
                "Contact groups are used to assign monitoring "
                "objects to users. If you haven't defined any contact groups yet, "
                "then first <a href='%s'>do so</a>. "
                "Hosts and services can be assigned to contact groups using this "
                "<a href='%s'>rule for hosts</a> and this "
                "<a href='%s'>rule for services</a>.<br><br>"
                "If you do not put the user into any contact group "
                "then no monitoring contact will be created for the user."
            )
            % (groups_page_url, hosts_assign_url, services_assign_url)
        )

        forms.header(_("Notifications"), isopen=False)
        if not self._rbn_enabled():
            forms.section(_("Enabling"), simple=True)
            html.checkbox(
                "notifications_enabled",
                bool(self._user.get("notifications_enabled")),
                label=_("enable notifications"),
            )
            html.help(
                _("Notifications are sent out " "when the status of a host or service changes.")
            )

            # Notification period
            forms.section(_("Notification time period"))
            user_np = self._user.get("notification_period", "24X7")
            if not isinstance(user_np, str):
                raise Exception("invalid notification period %r" % (user_np,))
            choices: Choices = [
                (id_, "%s" % (tp["alias"])) for (id_, tp) in self._timeperiods.items()
            ]
            html.dropdown("notification_period", choices, deflt=user_np, ordered=True)
            html.help(
                _(
                    "Only during this time period the "
                    "user will get notifications about host or service alerts."
                )
            )

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
                },
            }

            forms.section(_("Notification Options"))
            # TODO: Remove this "what" nonsense
            for title, what, opts in [
                (_("Host events"), "host", "durfs"),
                (_("Service events"), "service", "wucrfs"),
            ]:
                html.write_text("%s:" % title)
                html.open_ul()

                user_opts = (
                    self._user.get("host_notification_options", opts)
                    if what == "host"
                    else self._user.get("service_notification_options", opts)
                )
                for opt in opts:
                    opt_name = notification_option_names[what].get(
                        opt, notification_option_names["both"].get(opt)
                    )
                    html.checkbox(what + "_" + opt, opt in user_opts, label=opt_name)
                    html.br()
                html.close_ul()

            html.help(
                _(
                    "Here you specify which types of alerts "
                    "will be notified to this contact. Note: these settings will only be saved "
                    "and used if the user is member of a contact group."
                )
            )

            forms.section(_("Notification Method"))
            get_vs_flexible_notifications().render_input(
                "notification_method", self._user.get("notification_method")
            )

        else:
            forms.section(_("Fallback notifications"), simple=True)

            html.checkbox(
                "fallback_contact",
                bool(self._user.get("fallback_contact")),
                label=_("Receive fallback notifications"),
            )

            html.help(
                _(
                    "In case none of your notification rules handles a certain event a notification "
                    "will be sent to this contact. This makes sure that in that case at least <i>someone</i> "
                    "gets notified. Furthermore this contact will be used for notifications to any host or service "
                    "that is not known to the monitoring. This can happen when you forward notifications "
                    "from the Event Console.<br><br>Notification fallback can also configured in the global "
                    'setting <a href="wato.py?mode=edit_configvar&varname=notification_fallback_email">'
                    "Fallback email address for notifications</a>."
                )
            )

        self._show_custom_user_attributes(custom_user_attr_topics.get("notify", []))

        forms.header(_("Personal settings"), isopen=False)
        select_language(self._user)
        self._show_custom_user_attributes(custom_user_attr_topics.get("personal", []))
        forms.header(_("Interface settings"), isopen=False)
        self._show_custom_user_attributes(custom_user_attr_topics.get("interface", []))

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
            return "new"
        assert self._user_id is not None
        return base64.b64encode(self._user_id.encode("utf-8")).decode("ascii")

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
                    value=None,
                    title=_("All sites"),
                    totext=_("May see all sites"),
                ),
                DualListChoice(
                    title=_("Specific sites"),
                    choices=get_configured_site_choices,
                ),
            ],
        )

    def _show_custom_user_attributes(self, custom_attr: List[Tuple[str, UserAttribute]]) -> None:
        for name, attr in custom_attr:
            vs = attr.valuespec()
            vs_title = vs.title()
            forms.section(_u(vs_title) if isinstance(vs_title, str) else vs_title)
            if not self._is_locked(name):
                vs.render_input("ua_" + name, self._user.get(name, vs.default_value()))
            else:
                html.write_text(vs.value_to_html(self._user.get(name, vs.default_value())))
                # Render hidden to have the values kept after saving
                html.open_div(style="display:none")
                vs.render_input("ua_" + name, self._user.get(name, vs.default_value()))
                html.close_div()
            vs_help = vs.help()
            html.help(_u(vs_help) if isinstance(vs_help, str) else vs_help)


def select_language(user_spec: UserSpec) -> None:
    languages: Choices = [l for l in get_languages() if l[0] not in active_config.hide_languages]
    if not languages:
        return

    current_language = user_spec.get("language")
    if current_language is None:
        current_language = "_default_"

    languages.insert(
        0,
        (
            "_default_",
            _("Use the default language (%s)") % get_language_alias(active_config.default_language),
        ),
    )

    forms.section(_("Language"))
    html.dropdown("language", languages, deflt=current_language)
    html.help(
        _(
            "Configure the language of the user interface. Feel free to contribute to the "
            "translations on %s."
        )
        % HTMLWriter.render_a(
            "Weblate",
            "https://translate.checkmk.com",
            target="_blank",
        )
    )


def _is_two_factor_enabled(user_spec: UserSpec) -> bool:
    return user_spec.get("two_factor_credentials", {}).get("webauthn_credentials") is not None
