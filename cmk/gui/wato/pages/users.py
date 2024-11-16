#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Modes for managing users and contacts"""

import base64
import time
import traceback
from collections.abc import Collection, Iterable, Iterator
from functools import partial
from typing import cast, Literal, overload

from cmk.ccc.version import Edition, edition

from cmk.utils import paths, render
from cmk.utils.user import UserId

from cmk.gui import background_job, forms, gui_background_job, userdb, weblib
from cmk.gui.breadcrumb import Breadcrumb, BreadcrumbItem
from cmk.gui.config import active_config
from cmk.gui.customer import ABCCustomerAPI, customer_api
from cmk.gui.exceptions import MKUserError
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _, _u, get_language_alias, get_languages, is_community_translation
from cmk.gui.log import logger
from cmk.gui.logged_in import user
from cmk.gui.page_menu import (
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
from cmk.gui.table import show_row_count, table_element
from cmk.gui.type_defs import ActionResult, Choices, PermissionName, UserObject, UserSpec
from cmk.gui.user_sites import get_configured_site_choices
from cmk.gui.userdb import (
    active_connections,
    ConnectorType,
    get_connection,
    get_user_attributes,
    get_user_attributes_by_topic,
    load_roles,
    new_user_template,
    UserAttribute,
    UserConnector,
)
from cmk.gui.userdb.htpasswd import hash_password
from cmk.gui.userdb.ldap_connector import LDAPUserConnector
from cmk.gui.userdb.user_sync_job import UserSyncBackgroundJob
from cmk.gui.utils.csrf_token import check_csrf_token
from cmk.gui.utils.flashed_messages import flash
from cmk.gui.utils.html import HTML
from cmk.gui.utils.ntop import get_ntop_connection_mandatory, is_ntop_available
from cmk.gui.utils.roles import user_may
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.utils.urls import (
    DocReference,
    make_confirm_delete_link,
    makeactionuri,
    makeuri,
    makeuri_contextless,
)
from cmk.gui.utils.user_security_message import SecurityNotificationEvent, send_security_message
from cmk.gui.valuespec import (
    Alternative,
    DualListChoice,
    EmailAddress,
    FixedValue,
    TextInput,
    UserID,
)
from cmk.gui.watolib.audit_log_url import make_object_audit_log_url
from cmk.gui.watolib.groups_io import load_contact_group_information
from cmk.gui.watolib.hosts_and_folders import folder_preserving_link, make_action_link
from cmk.gui.watolib.mode import mode_registry, mode_url, ModeRegistry, redirect, WatoMode
from cmk.gui.watolib.timeperiods import load_timeperiods
from cmk.gui.watolib.user_scripts import load_notification_scripts
from cmk.gui.watolib.users import (
    delete_users,
    edit_users,
    get_vs_user_idle_timeout,
    make_user_object_ref,
    user_features_registry,
    verify_password_policy,
)
from cmk.gui.watolib.utils import ldap_connections_are_configurable

from cmk.crypto.password import Password


def register(_mode_registry: ModeRegistry) -> None:
    _mode_registry.register(ModeUsers)
    _mode_registry.register(ModeEditUser)


def has_customer(
    user_cxn: UserConnector | None,
    cust_api: ABCCustomerAPI,
    user_spec: UserSpec,
) -> str | None:
    if edition(paths.omd_root) is not Edition.CME:
        return None

    if isinstance(user_cxn, LDAPUserConnector):
        if user_cxn.customer_id is not None:
            return cust_api.get_customer_name_by_id(user_cxn.customer_id)
    return cust_api.get_customer_name(user_spec)


class ModeUsers(WatoMode):
    @classmethod
    def name(cls) -> str:
        return "users"

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return ["users"]

    def __init__(self) -> None:
        super().__init__()
        self._job = UserSyncBackgroundJob()
        self._job_snapshot = UserSyncBackgroundJob().get_status_snapshot()
        self._can_create_and_delete_users = edition(paths.omd_root) != Edition.CSE

    def title(self) -> str:
        return _("Users")

    def _topic_breadcrumb_item(self) -> Iterable[BreadcrumbItem]:
        # Since we are in the users mode, we don't need to add the
        # "Users" topic to the breadcrumb. Else we get "Users > Users"
        return ()

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        topics = (
            [
                PageMenuTopic(
                    title=_("Add user"),
                    entries=[
                        PageMenuEntry(
                            title=_("Add user"),
                            icon_name="new",
                            item=make_simple_link(folder_preserving_link([("mode", "edit_user")])),
                            is_shortcut=True,
                            is_suggested=True,
                        ),
                    ],
                )
            ]
            if self._can_create_and_delete_users
            else []
        )

        topics += [
            PageMenuTopic(
                title=_("On selected users"),
                entries=list(self._page_menu_entries_on_selected_users()),
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
        ]
        menu = PageMenu(
            dropdowns=[
                PageMenuDropdown(
                    name="users",
                    title=_("Users"),
                    topics=topics,
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
        menu.add_doc_reference(_("Users, roles and permissions"), DocReference.WATO_USER)
        return menu

    def _page_menu_entries_on_selected_users(self) -> Iterator[PageMenuEntry]:
        if self._can_create_and_delete_users:
            yield PageMenuEntry(
                title=_("Delete users"),
                shortcut_title=_("Delete selected users"),
                icon_name="delete",
                item=make_confirmed_form_submit_link(
                    form_name="bulk_delete_form",
                    button_name="_bulk_delete_users",
                    title=_("Delete selected users"),
                ),
                is_shortcut=True,
                is_suggested=True,
            )

        if user.may("wato.user_migrate") and self._can_create_and_delete_users:
            yield PageMenuEntry(
                title=_("Migrate users"),
                shortcut_title=_("Migrate selected users"),
                icon_name="migrate",
                item=make_simple_link(
                    makeuri_contextless(
                        request,
                        [
                            ("selection", weblib.selection_id()),
                            ("mode", "user_migrate"),
                        ],
                    )
                ),
                is_shortcut=True,
                is_suggested=True,
                is_enabled=len(active_connections()) > 1,
                disabled_tooltip=_("There is only one active user connector available"),
            )

    def _page_menu_entries_synchronized_users(self) -> Iterator[PageMenuEntry]:
        if _sync_possible():
            if not self._job_snapshot.is_active:
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

        if ldap_connections_are_configurable():
            yield PageMenuEntry(
                title=_("LDAP & Active Directory"),
                icon_name="ldap",
                item=make_simple_link(folder_preserving_link([("mode", "ldap_config")])),
            )

        # The SAML2 config mode is only registered under non-CRE, non-CSE editions
        if mode_registry.get("saml_config") is not None:
            yield PageMenuEntry(
                title=_("SAML authentication"),
                icon_name="saml",
                item=make_simple_link(folder_preserving_link([("mode", "saml_config")])),
            )

    def action(self) -> ActionResult:
        check_csrf_token()

        if not transactions.check_transaction():
            return redirect(self.mode_url())

        if self._can_create_and_delete_users and (
            delete_user := request.get_validated_type_input(UserId, "_delete")
        ):
            delete_users([delete_user], user_features_registry.features().sites)
            return redirect(self.mode_url())

        if request.var("_sync"):
            try:
                job = UserSyncBackgroundJob()
                if (
                    result := job.start(
                        partial(
                            job.do_sync,
                            add_to_changelog=True,
                            enforce_sync=True,
                            load_users_func=userdb.load_users,
                            save_users_func=userdb.save_users,
                        ),
                        background_job.InitialStatusArgs(
                            title=job.gui_title(),
                            stoppable=False,
                            user=str(user.id) if user.id else None,
                        ),
                    )
                ).is_error():
                    raise MKUserError(None, result.error)

                self._job_snapshot = job.get_status_snapshot()
            except MKUserError:
                raise
            except Exception:
                logger.exception("error syncing users")
                raise MKUserError(None, traceback.format_exc().replace("\n", "<br>\n"))
            return redirect(self.mode_url())

        if self._can_create_and_delete_users and request.var("_bulk_delete_users"):
            self._bulk_delete_users_after_confirm()
            return redirect(self.mode_url())

        action_handler = gui_background_job.ActionHandler(self.breadcrumb())
        action_handler.handle_actions()
        if action_handler.did_acknowledge_job():
            self._job_snapshot = UserSyncBackgroundJob().get_status_snapshot()
            flash(_("Synchronization job acknowledged"))
            return redirect(self.mode_url())

        return None

    def _bulk_delete_users_after_confirm(self):
        selected_users = []
        users = userdb.load_users()
        for varname, _value in request.itervars(prefix="_c_user_"):
            if html.get_checkbox(varname):
                user_id = UserId(
                    base64.b64decode(varname.split("_c_user_")[-1].encode("utf-8")).decode("utf-8")
                )
                if user_id in users:
                    selected_users.append(user_id)

        if selected_users:
            delete_users(selected_users, user_features_registry.features().sites)

    def page(self) -> None:
        if not self._job_snapshot.exists:
            # Skip if snapshot doesnt exists
            pass

        elif self._job_snapshot.is_active:
            # Still running
            html.show_message(
                _("User synchronization currently running: ") + self._job_details_link()
            )
            url = makeuri(request, [])
            html.immediate_browser_redirect(2, url)

        elif (
            self._job_snapshot.status.state == background_job.JobStatusStates.FINISHED
            and not self._job_snapshot.acknowledged_by
        ):
            # Just finished, auto-acknowledge
            UserSyncBackgroundJob().acknowledge(user.id)
            # html.show_message(_("User synchronization successful"))

        elif not self._job_snapshot.acknowledged_by and self._job_snapshot.has_exception:
            # Finished, but not OK - show info message with links to details
            html.show_warning(
                _("Last user synchronization ran into an exception: ") + self._job_details_link()
            )

        users = userdb.load_users()
        with html.form_context("bulk_delete_form", method="POST"):
            self._show_user_list(users)
        self._show_user_list_footer(users)

    def _job_details_link(self):
        return HTMLWriter.render_a("%s" % self._job.get_title(), href=self._job.detail_url())

    def _job_details_url(self):
        return makeuri_contextless(
            request,
            [
                ("mode", "background_job_details"),
                ("back_url", makeuri_contextless(request, [("mode", "users")])),
                ("job_id", self._job_snapshot.job_id),
            ],
            filename="wato.py",
        )

    def _show_job_info(self):
        if self._job_snapshot.is_active:
            html.h3(_("Current status of synchronization process"))
            html.browser_reload = 0.8
        else:
            html.h3(_("Result of last synchronization process"))

        job_manager = gui_background_job.GUIBackgroundJobManager()
        job_manager.show_job_details_from_snapshot(job_snapshot=self._job_snapshot)
        html.br()

    def _show_user_list(  # pylint: disable=too-many-branches
        self, users: dict[UserId, UserSpec]
    ) -> None:
        visible_custom_attrs = [
            (name, attr) for name, attr in get_user_attributes() if attr.show_in_table()
        ]
        entries = list(users.items())
        roles = load_roles()
        contact_groups = load_contact_group_information()

        html.div("", id_="row_info")

        customer = customer_api()
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
                        onclick="cmk.selection.toggle_all_rows(this.form);",
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

                    if self._can_create_and_delete_users:
                        clone_url = folder_preserving_link([("mode", "edit_user"), ("clone", uid)])
                        html.icon_button(clone_url, _("Create a copy of this user"), "clone")

                user_alias = user_spec.get("alias", "")
                if self._can_create_and_delete_users:
                    delete_url = make_confirm_delete_link(
                        url=make_action_link([("mode", "users"), ("_delete", uid)]),
                        title=_("Delete user"),
                        suffix=user_alias,
                        message=_("ID: %s") % uid,
                    )
                    html.icon_button(delete_url, _("Delete"), "delete")

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
                    last_seen, auth_type = userdb.get_last_seen(user_spec)
                    if last_seen >= online_threshold:
                        title = _("Online (%s %s via %s)") % (
                            render.date(last_seen),
                            render.time_of_day(last_seen),
                            auth_type,
                        )
                        img_txt = "checkmark"
                    elif last_seen != 0:
                        title = _("Offline (%s %s via %s)") % (
                            render.date(last_seen),
                            render.time_of_day(last_seen),
                            auth_type,
                        )
                        img_txt = "cross_grey"
                    elif last_seen == 0:
                        title = _("Never")
                        img_txt = "hyphen"

                    table.cell(_("Act."))
                    html.icon(img_txt, title)

                    table.cell(_("Last seen"))
                    if last_seen != 0:
                        html.write_text_permissive(
                            f"{render.date(last_seen)} {render.time_of_day(last_seen)}"
                        )
                    else:
                        html.write_text_permissive(_("Never"))

                if cust := has_customer(
                    user_cxn=connection, cust_api=customer, user_spec=user_spec
                ):
                    table.cell(_("Customer"), cust)

                # Connection
                if connection:
                    table.cell(
                        _("Connection"), f"{connection.short_title()} ({user_connection_id})"
                    )
                    locked_attributes = userdb.locked_attributes(user_connection_id)
                else:
                    table.cell(
                        _("Connection"),
                        "{} ({}) ({})".format(_("UNKNOWN"), user_connection_id, _("disabled")),
                        css=["error"],
                    )
                    locked_attributes = []

                # Authentication
                if "automation_secret" in user_spec:
                    auth_method: str | HTML = _("Automation")
                elif user_spec.get("password") or "password" in locked_attributes:
                    auth_method = _("Password")
                    if connection and connection.type() == ConnectorType.SAML2:
                        auth_method = connection.short_title()
                    if userdb.is_two_factor_login_enabled(uid):
                        auth_method += " (+2FA)"
                else:
                    auth_method = HTMLWriter.render_i(_("none"))
                table.cell(_("Authentication"), auth_method)

                table.cell(_("State"), sortable=False)
                if user_spec["locked"]:
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
                table.cell(_("Alias"), user_alias)

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
                        HTML.without_escaping(", ").join(
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
                        HTML.without_escaping(", ").join(
                            HTMLWriter.render_a(content, href=url)
                            for (content, url) in zip(cg_aliases, cg_urls)
                        )
                    )
                else:
                    html.i(_("none"))

                # the visible custom attributes
                for name, attr in visible_custom_attrs:
                    vs = attr.valuespec()
                    vs_title = vs.title()
                    table.cell(_u(vs_title) if isinstance(vs_title, str) else vs_title)
                    html.write_text_permissive(
                        vs.value_to_html(user_spec.get(name, vs.default_value()))
                    )

        html.hidden_field("selection", weblib.selection_id())
        html.hidden_fields()

    def _show_user_list_footer(self, users: dict[UserId, UserSpec]) -> None:
        show_row_count(
            row_count=(row_count := len(users)),
            row_info=_("user") if row_count == 1 else _("users"),
            selection_id="users",
        )

        if not load_contact_group_information():
            url = "wato.py?mode=contact_groups"
            html.open_div(class_="info")
            html.write_text_permissive(
                _(
                    "Note: you haven't defined any contact groups yet. If you <a href='%s'>"
                    "create some contact groups</a> you can assign users to them und thus "
                    "make them monitoring contacts. Only monitoring contacts can receive "
                    "notifications."
                )
                % url
            )
            html.write_text_permissive(
                " you can assign users to them und thus "
                "make them monitoring contacts. Only monitoring contacts can receive "
                "notifications."
            )
            html.close_div()


# TODO: Create separate ModeCreateUser()
# TODO: Move CME specific stuff to CME related class
# TODO: Refactor action / page to use less hand crafted logic (valuespecs instead?)
class ModeEditUser(WatoMode):
    @classmethod
    def name(cls) -> str:
        return "edit_user"

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return ["users"]

    @classmethod
    def parent_mode(cls) -> type[WatoMode] | None:
        return ModeUsers

    # pylint does not understand this overloading
    @overload
    @classmethod
    def mode_url(cls, *, edit: str) -> str:  # pylint: disable=arguments-differ
        ...

    @overload
    @classmethod
    def mode_url(cls, **kwargs: str) -> str: ...

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
        self._timeperiods = load_timeperiods()
        self._roles = load_roles()
        self._user_id: UserId | None

        self._vs_customer = customer_api().vs_customer()

        self._can_edit_users = edition(paths.omd_root) != Edition.CSE

    def _from_vars(self):
        # TODO: Should we turn the both fields below into Optional[UserId]?
        try:
            self._user_id = request.get_validated_type_input(UserId, "edit", empty_is_none=True)
        except ValueError as e:
            raise MKUserError("edit", str(e)) from e
        # This is needed for the breadcrumb computation:
        # When linking from user notification rules page the request variable is "user"
        # instead of "edit". We should also change that variable to "user" on this page,
        # then we can simply use self._user_id.
        if not self._user_id and request.has_var("user"):
            try:
                self._user_id = request.get_validated_type_input_mandatory(UserId, "user")
            except ValueError as e:
                raise MKUserError("user", str(e)) from e

        try:
            # cloneid is not mandatory because it is only needed in 'new' mode
            self._cloneid = request.get_validated_type_input(UserId, "clone")
        except ValueError as e:
            raise MKUserError("clone", str(e)) from e

        # TODO: Nuke the field below? It effectively hides facts about _user_id for mypy.
        self._is_new_user: bool = self._user_id is None
        self._users = userdb.load_users(lock=transactions.is_transaction())
        new_user = new_user_template("htpasswd")

        if self._user_id is not None:
            self._user = self._users.get(self._user_id, new_user)
        elif self._cloneid:
            self._user = self._users.get(self._cloneid, new_user)
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
        if not self._is_new_user:
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
                    make_object_audit_log_url(make_user_object_ref(self._user_id))
                ),
            )

        if not self._is_new_user:
            yield PageMenuEntry(
                title=_("Remove two-factor authentication"),
                icon_name="2fa",
                item=make_simple_link(
                    make_confirm_delete_link(
                        url=make_action_link(
                            [
                                ("mode", "edit_user"),
                                ("user", self._user_id),
                                ("_disable_two_factor", "1"),
                            ]
                        ),
                        title=_("Remove two-factor authentication of %s") % self._user_id,
                    )
                ),
                is_enabled=(
                    userdb.is_two_factor_login_enabled(self._user_id)
                    if self._user_id is not None
                    else False
                ),
            )

    def action(self) -> ActionResult:  # pylint: disable=too-many-branches
        check_csrf_token()

        if not transactions.check_transaction():
            return redirect(mode_url("users"))

        if self._user_id is not None and request.has_var("_disable_two_factor"):
            userdb.disable_two_factor_authentication(self._user_id)
            return redirect(mode_url("users"))

        if self._user_id is None:  # same as self._is_new_user
            self._user_id = request.get_validated_type_input_mandatory(UserId, "user_id")
            user_attrs: UserSpec = {}
        else:
            self._user_id = request.get_validated_type_input_mandatory(UserId, "edit")
            user_attrs = self._users[self._user_id].copy()

        if self._can_edit_users:
            self._get_identity_userattrs(user_attrs)

        # We always store secrets for automation users. Also in editions that are not allowed
        # to edit users *hust* CSE *hust*
        is_automation_user = self._user.get("automation_secret", None) is not None
        if is_automation_user or self._can_edit_users:
            self._get_security_userattrs(user_attrs)

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

        user_attrs["fallback_contact"] = html.get_checkbox("fallback_contact")

        # Custom user attributes
        for name, attr in get_user_attributes():
            value = attr.valuespec().from_html_vars("ua_" + name)
            # TODO: Dynamically fiddling around with a TypedDict is a bit questionable
            user_attrs[name] = value  # type: ignore[literal-required]

        # Generate user "object" to update
        user_object: UserObject = {
            self._user_id: {
                "attributes": user_attrs,
                "is_new_user": self._is_new_user,
            }
        }
        # The following call validates and updated the users
        edit_users(user_object, user_features_registry.features().sites)
        return redirect(mode_url("users"))

    def _get_identity_userattrs(self, user_attrs: UserSpec) -> None:
        # Full name
        user_attrs["alias"] = request.get_str_input_mandatory("alias").strip()

        # Connector
        user_attrs["connector"] = self._user.get("connector")

        # Email address
        user_attrs["email"] = EmailAddress().from_html_vars("email")

        idle_timeout = get_vs_user_idle_timeout().from_html_vars("idle_timeout")
        user_attrs["idle_timeout"] = idle_timeout
        if idle_timeout is None:
            del user_attrs["idle_timeout"]

        # Pager
        user_attrs["pager"] = request.get_str_input_mandatory("pager", "").strip()

        if edition(paths.omd_root) is Edition.CME:
            customer = self._vs_customer.from_html_vars("customer")
            self._vs_customer.validate_value(customer, "customer")

            if customer != customer_api().default_customer_id():
                user_attrs["customer"] = customer
            elif "customer" in user_attrs:
                del user_attrs["customer"]

        if not self._is_locked("authorized_sites"):
            # when the authorized_sites attribute is locked, the information is rendered on the page
            # without setting its corresponding html var. On save, the value is therefore unavailable
            # to be verified, and we can leave its existing value untouched. The length of this
            # comment shows that the code is flawed.
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
            # see corresponding Setup rule
            ntop_username_attribute = ntop_connection.get("use_custom_attribute_as_ntop_username")
            if ntop_username_attribute:
                # TODO: Dynamically fiddling around with a TypedDict is a bit questionable
                user_attrs[ntop_username_attribute] = request.get_str_input_mandatory(  # type: ignore[literal-required]
                    ntop_username_attribute
                )

    def _increment_auth_serial(self, user_attrs: UserSpec) -> None:
        user_attrs["serial"] = user_attrs.get("serial", 0) + 1

    def _handle_auth_attributes(self, user_attrs: UserSpec) -> None:
        increase_serial = False

        if request.var("authmethod") == "secret":  # automation secret
            if secret := request.get_str_input_mandatory("_auth_secret", ""):
                user_attrs["automation_secret"] = secret
                user_attrs["password"] = hash_password(Password(secret))
                increase_serial = True  # password changed, reflect in auth serial

                # automation users cannot set the passwords themselves.
                user_attrs["last_pw_change"] = int(time.time())
                user_attrs.pop("enforce_pw_change", None)

            elif "automation_secret" not in user_attrs and "password" in user_attrs:
                del user_attrs["password"]

        else:  # password
            password_field_name = "_password_" + self._pw_suffix()
            password2_field_name = "_password2_" + self._pw_suffix()
            password = request.get_validated_type_input(
                Password, password_field_name, empty_is_none=True
            )
            password2 = request.get_validated_type_input(
                Password, password2_field_name, empty_is_none=True
            )

            # We compare both passwords only, if the user has supplied
            # the repeation! We are so nice to our power users...
            # Note: this validation is done before the main-validiation later on
            # It doesn't make any sense to put this block into the main validation function
            if password2 and password != password2:
                raise MKUserError(password2_field_name, _("Passwords don't match"))

            # Detect switch from automation to password
            if "automation_secret" in user_attrs:
                del user_attrs["automation_secret"]
                if "password" in user_attrs:
                    del user_attrs["password"]  # which was the hashed automation secret!

            if password:
                verify_password_policy(password, password_field_name)
                user_attrs["password"] = hash_password(password)
                user_attrs["last_pw_change"] = int(time.time())
                send_security_message(self._user_id, SecurityNotificationEvent.password_change)
                increase_serial = True  # password changed, reflect in auth serial

            # PW change enforcement
            user_attrs["enforce_pw_change"] = html.get_checkbox("enforce_pw_change")
            if user_attrs["enforce_pw_change"]:
                increase_serial = True  # invalidate all existing user sessions, enforce relogon

        # Increase serial (if needed)
        if increase_serial:
            self._increment_auth_serial(user_attrs)

    def _get_security_userattrs(self, user_attrs: UserSpec) -> None:
        # Locking
        user_attrs["locked"] = html.get_checkbox("locked") or False
        if (  # toggled for an existing user
            self._user_id in self._users
            and self._users[self._user_id]["locked"] != user_attrs["locked"]
        ):
            if user_attrs["locked"]:  # user is being locked, increase the auth serial
                self._increment_auth_serial(user_attrs)
            else:  # user is being unlocked, reset failed login attempts
                user_attrs["num_failed_logins"] = 0

        # Authentication: Password or Secret
        self._handle_auth_attributes(user_attrs)

        # Roles
        if edition(paths.omd_root) != Edition.CSE:
            user_attrs["roles"] = [
                role for role in self._roles.keys() if html.get_checkbox("role_" + role)
            ]

    def page(self) -> None:
        # Let exceptions from loading notification scripts happen now
        load_notification_scripts()

        with html.form_context("user", method="POST"):
            self._show_form()

    def _show_form(self) -> None:  # pylint: disable=too-many-branches
        html.prevent_password_auto_completion()
        custom_user_attr_topics = get_user_attributes_by_topic()
        is_automation_user = self._user.get("automation_secret", None) is not None

        if self._can_edit_users:
            self._render_identity(custom_user_attr_topics)
            self._render_security(
                {
                    "password",
                    "automation",
                    "disable_password",
                    "idle_timeout",
                    "roles",
                    "custom_user_attributes",
                },
                custom_user_attr_topics,
                is_automation_user,
            )
        elif is_automation_user:
            self._render_security(
                {
                    "automation",
                    "disable_password",
                },
                None,
                is_automation_user,
            )

        # Contact groups
        forms.header(_("Contact groups"), isopen=False)
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
            html.write_text_permissive(
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
                "that is not known to the monitoring. "
                "This can happen when you forward notifications from the Event Console. "
                "<br><br>Notification fallback can also configured in the global "
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

    def _render_identity(
        self, custom_user_attr_topics: dict[str, list[tuple[str, UserAttribute]]]
    ) -> None:
        forms.header(_("Identity"))

        # ID
        forms.section(_("Username"), simple=not self._is_new_user, is_required=True)
        if self._is_new_user:
            vs_user_id: TextInput | FixedValue = UserID(allow_empty=False, size=73)
        else:
            vs_user_id = FixedValue(value=self._user_id)
        vs_user_id.render_input("user_id", self._user_id)

        # Full name
        forms.section(_("Full name"), is_required=True)
        self._lockable_input("alias", self._user_id)
        html.help(_("Full name or alias of the user"))

        # Email address
        forms.section(_("Email address"))
        email = self._user.get("email", "")
        if not self._is_locked("email"):
            EmailAddress(size=73).render_input("email", email)
        else:
            html.write_text_permissive(email)
            html.hidden_field("email", email)

        html.help(
            _(
                "The email address is optional and is needed "
                "if the user is a monitoring contact and receives notifications "
                "via email."
            )
        )

        forms.section(_("Pager address"))
        self._lockable_input("pager", "")
        html.help(_("The pager address is optional "))

        if edition(paths.omd_root) is Edition.CME:
            forms.section(self._vs_customer.title())
            self._vs_customer.render_input("customer", customer_api().get_customer_id(self._user))

            html.help(self._vs_customer.help())

        vs_sites = self._vs_sites()
        forms.section(vs_sites.title())
        authorized_sites = self._user.get("authorized_sites", vs_sites.default_value())
        if not self._is_locked("authorized_sites"):
            vs_sites.render_input("authorized_sites", authorized_sites)
        else:
            html.write_text_permissive(vs_sites.value_to_html(authorized_sites))
        html.help(vs_sites.help())

        self._show_custom_user_attributes(custom_user_attr_topics.get("ident", []))

        # ntopng
        if is_ntop_available():
            ntop_connection = get_ntop_connection_mandatory()
            # ntop_username_attribute will be the name of the custom attribute or false
            # see corresponding Setup rule
            ntop_username_attribute = ntop_connection.get("use_custom_attribute_as_ntop_username")
            if ntop_username_attribute:
                forms.section(_("ntopng Username"))
                self._lockable_input(ntop_username_attribute, "")
                html.help(
                    _(
                        "The corresponding username in ntopng of the current checkmk user. "
                        "It is used, in case the user mapping to ntopng is configured to use this "
                        "custom attribute"
                    )
                )

    def _render_security(  # pylint: disable=too-many-branches
        self,
        options_to_render: set[
            Literal[
                "password",
                "automation",
                "disable_password",
                "idle_timeout",
                "roles",
                "custom_user_attributes",
            ]
        ],
        custom_user_attr_topics: dict[str, list[tuple[str, UserAttribute]]] | None,
        is_automation: bool,
    ) -> None:
        forms.header(_("Security"))

        if "password" in options_to_render or "automation" in options_to_render:
            forms.section(_("Authentication"))

        if "password" in options_to_render:
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
                html.password_meter()
                html.close_td()
                html.close_tr()

                html.open_tr()
                html.td(_("repeat:"))
                html.open_td()
                html.password_input("_password2_" + self._pw_suffix(), autocomplete="new-password")
                html.write_text_permissive(" (%s)" % _("optional"))
                html.close_td()
                html.close_tr()

                html.open_tr()
                html.td("%s:" % _("Enforce change"))
                html.open_td()
                # Only make password enforcement selection possible when user is allowed to change the PW
                if self._is_new_user or (
                    user_may(self._user_id, "general.edit_profile")
                    and user_may(self._user_id, "general.change_password")
                ):
                    html.checkbox(
                        "enforce_pw_change",
                        bool(self._user.get("enforce_pw_change")),
                        label=_("Change password at next login or access"),
                    )
                else:
                    html.write_text_permissive(
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

        if "automation" in options_to_render:
            html.radiobutton(
                "authmethod", "secret", is_automation, _("Automation secret for machine accounts")
            )
            html.open_ul()
            html.password_input(
                "_auth_secret",
                "",
                size=30,
                id_="automation_secret",
                placeholder="******" if "automation_secret" in self._user else "",
                autocomplete="off",
            )
            html.write_text_permissive(" ")
            html.open_b(style=["position: relative", "top: 4px;"])
            html.write_text_permissive(" &nbsp;")
            html.icon_button(
                "javascript:cmk.wato.randomize_secret('automation_secret', '%s');"
                % _("Copied secret to clipboard"),
                _("Create random secret and copy secret to clipboard"),
                "random",
            )
            html.close_b()
            html.close_ul()

        if "password" in options_to_render:
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
                    "a web service without any further configuration."
                )
            )

        if "disable_password" in options_to_render:
            # Locking
            forms.section(_("Disable password"), simple=True)
            if not self._is_locked("locked"):
                html.checkbox(
                    "locked",
                    bool(self._user["locked"]),
                    label=_("disable the login to this account"),
                )
            else:
                html.write_text_permissive(
                    _("Login disabled") if self._user["locked"] else _("Login possible")
                )
                html.hidden_field("locked", "1" if self._user["locked"] else "")
            html.help(
                _(
                    "Disabling the password will prevent a user from logging in while "
                    "retaining the original password. Notifications are not affected "
                    "by this setting."
                )
            )

        if "idle_timeout" in options_to_render:
            forms.section(_("Idle timeout"))
            idle_timeout = self._user.get("idle_timeout")
            if not self._is_locked("idle_timeout"):
                get_vs_user_idle_timeout().render_input("idle_timeout", idle_timeout)
            else:
                html.write_text_permissive(idle_timeout)
                html.hidden_field("idle_timeout", idle_timeout)

        if "roles" in options_to_render:
            # Roles
            forms.section(_("Roles"))
            is_member_of_at_least_one = False
            html.open_table()
            for role_id, role in sorted(self._roles.items(), key=lambda x: (x[1]["alias"], x[0])):
                html.open_tr()
                html.open_td()
                if not self._is_locked("roles"):
                    html.checkbox("role_" + role_id, role_id in self._user.get("roles", []))
                    url = folder_preserving_link([("mode", "edit_role"), ("edit", role_id)])
                    html.a(role["alias"], href=url)
                else:
                    is_member = role_id in self._user.get("roles", [])
                    if is_member:
                        is_member_of_at_least_one = True
                        url = folder_preserving_link([("mode", "edit_role"), ("edit", role_id)])
                        html.a(role["alias"], href=url)
                    html.hidden_field("role_" + role_id, "1" if is_member else "")
                html.close_td()
                html.close_tr()
            html.close_table()

            if self._is_locked("roles") and not is_member_of_at_least_one:
                html.i(_("No roles assigned."))

        if "custom_user_attributes" in options_to_render and custom_user_attr_topics:
            self._show_custom_user_attributes(custom_user_attr_topics.get("security", []))

    def _lockable_input(self, name: str, dflt: str | None) -> None:
        # TODO: The cast is a big fat lie: value can be None, but things somehow seem to "work" even then. :-/
        value = cast(str, self._user.get(name, dflt))
        if self._is_locked(name):
            html.write_text_permissive(value)
            html.hidden_field(name, value)
        else:
            html.text_input(name, value, size=73)

    def _pw_suffix(self) -> str:
        if self._is_new_user:
            return "new"
        assert self._user_id is not None
        return base64.b64encode(self._user_id.encode("utf-8")).decode("ascii")

    def _is_locked(self, attr: str) -> bool:
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

    def _show_custom_user_attributes(self, custom_attr: list[tuple[str, UserAttribute]]) -> None:
        for name, attr in custom_attr:
            vs = attr.valuespec()
            vs_title = vs.title()
            forms.section(_u(vs_title) if isinstance(vs_title, str) else vs_title)
            if not self._is_locked(name):
                vs.render_input("ua_" + name, self._user.get(name, vs.default_value()))
            else:
                html.write_text_permissive(
                    vs.value_to_html(self._user.get(name, vs.default_value()))
                )
                # Render hidden to have the values kept after saving
                html.open_div(style="display:none")
                vs.render_input("ua_" + name, self._user.get(name, vs.default_value()))
                html.close_div()
            vs_help = vs.help()
            html.help(_u(vs_help) if isinstance(vs_help, str) else vs_help)


def select_language(user_spec: UserSpec) -> None:
    languages: Choices = [
        (ident, alias)
        for (ident, alias) in get_languages()
        if ident not in active_config.hide_languages
    ]
    if not active_config.enable_community_translations:
        languages = [
            (ident, alias)
            for (ident, alias) in languages
            if ident and not is_community_translation(ident)
        ]
    if not languages:
        return

    current_language = user_spec.get("language", "_default_")
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
        HTMLWriter.render_div(
            _(
                "Configure the language of the user interface. Checkmk is officially supported only "
                "for English and German."
            )
        )
        + HTMLWriter.render_div(
            _(
                "Other language versions are offered for convenience only and anyone using Checkmk "
                "in a non-supported language does so at their own risk. No guarantee is given for the "
                "accuracy of the content. Checkmk accepts no liability for incorrect operation due to "
                "incorrect translations. "
            )
            + HTMLWriter.render_a(
                _("Feel free to contribute here."),
                "https://translate.checkmk.com",
                target="_blank",
            )
        )
    )


def _sync_possible() -> bool:
    """When at least one LDAP connection is defined and active a sync is possible"""
    return any(
        connection.type() == ConnectorType.LDAP
        for _connection_id, connection in active_connections()
    )
