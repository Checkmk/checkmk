#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Manage roles and permissions

In order to make getting started easier - Checkmk Multisite comes with three
builtin-roles: admin, user and guest. These roles have predefined permissions.
The built-in roles cannot be deleted.
In Setup you can create further roles and also edit the
permissions of the existing roles. Users can be assigned to built-in and custom
roles.  This modes manages the creation of custom roles and the permissions
configuration of all roles.
"""

# mypy: disable-error-code="type-arg"

from collections.abc import Collection

import cmk.gui.watolib.changes as _changes
from cmk.gui import forms, userdb
from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.config import Config
from cmk.gui.exceptions import MKUserError
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.page_menu import (
    get_search_expression,
    make_simple_form_page_menu,
    make_simple_link,
    PageMenu,
    PageMenuDropdown,
    PageMenuEntry,
    PageMenuSearch,
    PageMenuTopic,
    show_confirm_cancel_dialog,
)
from cmk.gui.permissions import (
    load_dynamic_permissions,
    permission_registry,
    permission_section_registry,
)
from cmk.gui.site_config import get_login_sites
from cmk.gui.table import Foldable, table_element
from cmk.gui.type_defs import ActionResult, Choices, IconNames, PermissionName, StaticIcon
from cmk.gui.userdb import get_user_attributes, UserRole
from cmk.gui.utils.csrf_token import check_csrf_token
from cmk.gui.utils.html import HTML
from cmk.gui.utils.roles import builtin_role_id_from_str
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.utils.urls import (
    DocReference,
    make_confirm_delete_link,
    makeactionuri,
    makeuri_contextless,
)
from cmk.gui.watolib import userroles
from cmk.gui.watolib.hosts_and_folders import folder_preserving_link, make_action_link
from cmk.gui.watolib.mode import mode_url, ModeRegistry, redirect, WatoMode
from cmk.gui.watolib.userroles import RoleID


def register(mode_registry: ModeRegistry) -> None:
    mode_registry.register(ModeRoles)
    mode_registry.register(ModeEditRole)
    mode_registry.register(ModeRoleMatrix)
    mode_registry.register(ModeRoleTwoFactor)


class ModeRoles(WatoMode):
    @classmethod
    def name(cls) -> str:
        return "roles"

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return ["users"]

    def title(self) -> str:
        return _("Roles & permissions")

    def page_menu(self, config: Config, breadcrumb: Breadcrumb) -> PageMenu:
        menu = PageMenu(
            dropdowns=[
                PageMenuDropdown(
                    name="roles",
                    title=_("Roles"),
                    topics=[
                        PageMenuTopic(
                            title=_("Overview"),
                            entries=[
                                PageMenuEntry(
                                    title=_("Permission matrix"),
                                    icon_name=StaticIcon(IconNames.matrix),
                                    item=make_simple_link(
                                        folder_preserving_link([("mode", "role_matrix")])
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
        menu.add_doc_reference(_("Users, roles and permissions"), DocReference.WATO_USER)
        return menu

    def action(self, config: Config) -> ActionResult:
        if not transactions.check_transaction():
            return redirect(self.mode_url())

        if request.var("_delete"):
            role_id = RoleID(request.get_ascii_input_mandatory("_delete"))
            userroles.delete_role(
                role_id,
                get_user_attributes(config.wato_user_attrs),
                pprint_value=config.wato_pprint_config,
            )
            _changes.add_change(
                action_name="edit-roles",
                text=_("Deleted role '%s'") % role_id,
                user_id=user.id,
                sites=get_login_sites(config.sites),
                use_git=config.wato_use_git,
            )

        elif request.var("_clone"):
            role_id = RoleID(request.get_ascii_input_mandatory("_clone"))
            userroles.clone_role(role_id, pprint_value=config.wato_pprint_config)
            _changes.add_change(
                action_name="edit-roles",
                text=_("Created new role '%s'") % role_id,
                user_id=user.id,
                sites=get_login_sites(config.sites),
                use_git=config.wato_use_git,
            )

        return redirect(self.mode_url())

    def page(self, config: Config) -> None:
        with table_element("roles") as table:
            users = userdb.load_users()
            for nr, role in enumerate(
                sorted(userroles.get_all_roles().values(), key=lambda a: (a.alias, a.name))
            ):
                table.row()

                table.cell("#", css=["narrow nowrap"])
                html.write_text_permissive(nr)

                # Actions
                table.cell(_("Actions"), css=["buttons"])
                edit_url = folder_preserving_link([("mode", "edit_role"), ("edit", role.name)])
                clone_url = make_action_link([("mode", "roles"), ("_clone", role.name)])
                delete_url = make_confirm_delete_link(
                    url=make_action_link([("mode", "roles"), ("_delete", role.name)]),
                    title=_("Delete role #%d") % nr,
                    suffix=role.alias,
                    message=("Name: %s") % role.name,
                )
                html.icon_button(edit_url, _("Properties"), StaticIcon(IconNames.edit))
                html.icon_button(clone_url, _("Clone"), StaticIcon(IconNames.clone))
                if not role.builtin:
                    html.icon_button(
                        delete_url, _("Delete this role"), StaticIcon(IconNames.delete)
                    )

                # ID
                table.cell(_("Name"), role.name)

                # Alias
                table.cell(_("Alias"), role.alias)

                # Type
                table.cell(_("Type"), _("built-in") if role.builtin else _("custom"))

                # Two factor
                table.cell(_("Two Factor"), _("Required") if role.two_factor else _("Not required"))

                # Modifications
                table.cell(
                    _("Modifications"),
                    HTMLWriter.render_span(
                        str(len(role.permissions)),
                        title=_("That many permissions do not use the factory defaults."),
                    ),
                )

                # Users
                table.cell(
                    _("Users"),
                    HTML.without_escaping(", ").join(
                        [
                            HTMLWriter.render_a(
                                user.get("alias", user_id),
                                folder_preserving_link([("mode", "edit_user"), ("edit", user_id)]),
                            )
                            for (user_id, user) in users.items()
                            if role.name in user["roles"]
                        ]
                    ),
                )

        # Possibly we could also display the following information
        # - number of set permissions (needs loading users)
        # - number of users with this role


class ModeRoleTwoFactor(WatoMode):
    @classmethod
    def name(cls) -> str:
        return "enforce_two_factor_on_role"

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return ["users"]

    @classmethod
    def parent_mode(cls) -> type[WatoMode] | None:
        return ModeRoles

    def __init__(self) -> None:
        super().__init__()
        load_dynamic_permissions()

    def _from_vars(self) -> None:
        self._role_id = RoleID(request.get_ascii_input_mandatory("edit"))
        self._role: UserRole = userroles.get_role(self._role_id)

    def title(self) -> str:
        return _("Enforce two-factor on %s role") % self._role_id

    def page(self, config: Config) -> None:
        request.get_ascii_input_mandatory("two_factor_enforce")
        confirm_url = makeactionuri(request, transactions, [("_action", "confirm")])
        cancel_url = makeuri_contextless(
            request,
            [("mode", ModeEditRole.name()), ("edit", self._role.name)],
        )

        message = html.render_div(
            (
                html.render_span(_("Warning:"), class_="underline")
                + _(
                    " Enforcing two-factor for the %s role will terminate any current sessions for users who have this role but have not enabled any two-factor."
                )
                % self._role.name
            ),
            class_="confirm_info",
        )

        show_confirm_cancel_dialog(
            _("Enforce two-factor on all users with %s role?") % self._role.name,
            confirm_url,
            cancel_url,
            message,
            confirm_text=_("Confirm"),
        )

    def action(self, config: Config) -> ActionResult:
        check_csrf_token()
        if request.var("_action") != "confirm":
            return None
        if request.get_ascii_input_mandatory("two_factor_enforce") != "enforce":
            return None

        self._role.two_factor = True

        userroles.update_role(
            role=self._role,
            old_roleid=self._role_id,
            new_roleid=self._role_id,
            pprint_value=config.wato_pprint_config,
        )
        userroles.logout_users_with_role(self._role_id, get_user_attributes(config.wato_user_attrs))
        _changes.add_change(
            action_name="edit-roles",
            text=_("Modified user role '%s'") % self._role_id,
            user_id=user.id,
            sites=get_login_sites(config.sites),
            use_git=config.wato_use_git,
        )
        return redirect(mode_url(ModeRoles.name()))


class ModeEditRole(WatoMode):
    @classmethod
    def name(cls) -> str:
        return "edit_role"

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return ["users"]

    @classmethod
    def parent_mode(cls) -> type[WatoMode] | None:
        return ModeRoles

    def __init__(self) -> None:
        super().__init__()

        # Make sure that all dynamic permissions are available (e.g. those for custom
        # views)
        load_dynamic_permissions()

    def _from_vars(self) -> None:
        self._role_id = RoleID(request.get_ascii_input_mandatory("edit"))
        self._role: UserRole = userroles.get_role(self._role_id)

    def title(self) -> str:
        return _("Edit role %s") % self._role_id

    def page_menu(self, config: Config, breadcrumb: Breadcrumb) -> PageMenu:
        menu = make_simple_form_page_menu(
            _("Role"), breadcrumb, form_name="role", button_name="_save"
        )
        menu.inpage_search = PageMenuSearch()
        return menu

    def action(self, config: Config) -> ActionResult:
        check_csrf_token()

        if html.form_submitted("search"):
            return None

        new_alias: str = request.get_str_input_mandatory("alias")
        try:
            userroles.validate_new_alias(self._role.alias, new_alias)
        except ValueError as exc:
            raise MKUserError("alias", str(exc))

        self._role.alias = new_alias

        if not self._role.builtin:
            self._role.basedon = builtin_role_id_from_str(
                request.get_ascii_input_mandatory("basedon")
            )

        new_id = request.get_ascii_input_mandatory("id")
        try:
            userroles.validate_new_roleid(self._role_id, new_id)
        except ValueError as exc:
            raise MKUserError("id", str(exc))

        self._role.name = new_id

        if self._role.two_factor != bool(html.get_checkbox("two_factor")) and bool(
            html.get_checkbox("two_factor")
        ):
            url = redirect(
                mode_url(
                    "enforce_two_factor_on_role", edit=self._role.name, two_factor_enforce="enforce"
                )
            )
        else:
            url = redirect(mode_url("roles"))
            self._role.two_factor = bool(html.get_checkbox("two_factor"))

        userroles.update_permissions(self._role, request.itervars(prefix="perm_"))
        userroles.update_role(
            role=self._role,
            old_roleid=self._role_id,
            new_roleid=RoleID(new_id),
            pprint_value=config.wato_pprint_config,
        )
        self._role_id = RoleID(new_id)

        _changes.add_change(
            action_name="edit-roles",
            text=_("Modified user role '%s'") % new_id,
            user_id=user.id,
            sites=get_login_sites(config.sites),
            use_git=config.wato_use_git,
        )
        return url

    def page(self, config: Config) -> None:
        with html.form_context(
            "role",
            method="POST",
            confirm_on_leave=True,
        ):
            self._page_form()

    def _page_form(self) -> None:
        search = get_search_expression()

        # ID
        forms.header(_("Basic properties"), css="wide")
        forms.section(_("Internal ID"), simple=self._role.builtin, is_required=True)

        if self._role.builtin:
            html.write_text_permissive("{} ({})".format(self._role_id, _("built-in role")))
            html.hidden_field("id", self._role_id)
        else:
            html.text_input("id", self._role_id)
            html.set_focus("id")

        # Alias
        forms.section(_("Alias"))
        html.help(_("An alias or description of the role"))
        html.text_input("alias", self._role.alias, size=50)

        forms.section(_("Enforce two-factor authentication"))
        html.help(
            _(
                "If this setting is changed from disabled to enabled, all users with this role will be required to use a two-factor authentication "
                "and will be logged out of any current sessions if they have not enabled two-factor. "
                "'Enforce two-factor authentication' in the global settings will override this setting."
            )
        )
        html.checkbox(
            "two_factor",
            self._role.two_factor,
        )

        # Based on
        if not self._role.builtin:
            forms.section(_("Based on role"))
            html.help(
                _(
                    "Each user defined role is based on one of the built-in roles. "
                    "When created it will start with all permissions of that role. When due to a software "
                    "update or installation of an add-on new permissions appear, the user role will get or "
                    "not get those new permissions based on the default settings of the built-in role it's "
                    "based on."
                )
            )
            role_choices: Choices = [
                (r.name, r.alias) for r in userroles.get_all_roles().values() if r.builtin
            ]
            default = "user" if self._role.basedon is None else self._role.basedon
            html.dropdown("basedon", role_choices, deflt=default, ordered=True)

        forms.end()

        html.h2(_("Permissions"))

        # Permissions
        base_role_id = self._role_id if self._role.basedon is None else self._role.basedon
        html.help(
            _(
                'If you leave the permissions at "default", '
                "they get their settings from the factory defaults (for built-in roles) or from the "
                "factory default of their base role (for user define roles). "
                "Factory defaults may change due to software updates. "
                "When choosing another base role, all permissions that are on default will reflect "
                "the new base role."
            )
        )

        for section in permission_section_registry.get_sorted_sections():
            # Now filter by the optional search term
            filtered_perms = []
            for perm in permission_registry.get_sorted_permissions(section):
                if search and (
                    search not in perm.title.lower() and search not in perm.name.lower()
                ):
                    continue

                filtered_perms.append(perm)

            if not filtered_perms:
                continue

            forms.header(section.title, isopen=search is not None, css="wide")
            for perm in filtered_perms:
                forms.section(perm.title)

                pvalue = self._role.permissions.get(perm.name)
                def_value = base_role_id in perm.defaults

                choices: Choices = [
                    ("yes", _("yes")),
                    ("no", _("no")),
                    ("default", _("default (%s)") % (def_value and _("yes") or _("no"))),
                ]

                deflt = {True: "yes", False: "no", None: "default"}[pvalue]

                html.dropdown("perm_" + perm.name, choices, deflt=deflt, style="width: 130px;")
                html.help(perm.description)

        forms.end()
        html.hidden_fields()


class ModeRoleMatrix(WatoMode):
    @classmethod
    def name(cls) -> str:
        return "role_matrix"

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return ["users"]

    @classmethod
    def parent_mode(cls) -> type[WatoMode] | None:
        return ModeRoles

    def title(self) -> str:
        return _("Permission matrix")

    def page_menu(self, config: Config, breadcrumb: Breadcrumb) -> PageMenu:
        return PageMenu(breadcrumb=breadcrumb, inpage_search=PageMenuSearch())

    def page(self, config: Config) -> None:
        for section in permission_section_registry.get_sorted_sections():
            with table_element(
                section.name,
                section.title,
                foldable=Foldable.FOLDABLE_SAVE_STATE,
                limit=max(200, config.table_row_limit),
            ) as table:
                permission_list = permission_registry.get_sorted_permissions(section)

                if not permission_list:
                    table.row()
                    table.cell(_("Permission"), _("No entries"), css=["wide"])
                    continue

                for perm in permission_list:
                    table.row()
                    table.cell(_("Permission"), perm.title, css=["wide"])

                    html.help(
                        HTML.without_escaping("<br />").join(
                            (perm.description, _("Internal name: %s") % perm.name)
                        )
                    )

                    for role in sorted(
                        userroles.get_all_roles().values(), key=lambda a: (a.alias, a.name)
                    ):
                        base_on_id = role.basedon if role.basedon is not None else role.name
                        pvalue = role.permissions.get(perm.name)
                        if pvalue is None:
                            if base_on_id in perm.defaults:
                                icon_name: StaticIcon | None = StaticIcon(
                                    IconNames.checkmark_bg_white
                                )
                            else:
                                icon_name = None
                        else:
                            icon_name = (
                                StaticIcon(IconNames.checkmark)
                                if pvalue
                                else StaticIcon(IconNames.cross_bg_white)
                            )

                        table.cell(role.name, css=["center"])
                        if icon_name:
                            html.static_icon(icon_name)

        html.close_table()
