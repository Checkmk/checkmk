#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Manage roles and permissions

In order to make getting started easier - Check_MK Multisite comes with three
builtin-roles: admin, user and guest. These roles have predefined permissions.
The builtin roles cannot be deleted. Users listed in admin_users in
multisite.mk automatically get the role admin - even if no such user or contact
has been configured yet. By that way an initial login - e.g. as omdamin - is
possible. The admin role cannot be removed from that user as long as he is
listed in admin_users. Also the variables guest_users, users and default_user_
role still work. That way Multisite is fully operable without WATO and also
backwards compatible.  In WATO you can create further roles and also edit the
permissions of the existing roles. Users can be assigned to builtin and custom
roles.  This modes manages the creation of custom roles and the permissions
configuration of all roles.
"""

import re
from typing import Collection, Dict, Optional, Type

import cmk.gui.forms as forms
import cmk.gui.userdb as userdb
import cmk.gui.watolib.changes as _changes
import cmk.gui.watolib.groups as groups
from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.config import builtin_role_ids
from cmk.gui.exceptions import MKUserError
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.page_menu import (
    make_simple_form_page_menu,
    make_simple_link,
    PageMenu,
    PageMenuDropdown,
    PageMenuEntry,
    PageMenuSearch,
    PageMenuTopic,
)
from cmk.gui.permissions import (
    load_dynamic_permissions,
    permission_registry,
    permission_section_registry,
)
from cmk.gui.plugins.wato.utils import (
    get_search_expression,
    make_confirm_link,
    mode_registry,
    mode_url,
    redirect,
    WatoMode,
)
from cmk.gui.site_config import get_login_sites
from cmk.gui.table import Foldable, table_element
from cmk.gui.type_defs import ActionResult, Choices, PermissionName, UserRole
from cmk.gui.utils.html import HTML
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.watolib import userroles
from cmk.gui.watolib.hosts_and_folders import folder_preserving_link, make_action_link
from cmk.gui.watolib.userroles import RoleID


@mode_registry.register
class ModeRoles(WatoMode):
    @classmethod
    def name(cls) -> str:
        return "roles"

    @classmethod
    def permissions(cls) -> Collection[PermissionName]:
        return ["users"]

    def title(self) -> str:
        return _("Roles & permissions")

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
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
                                    icon_name="matrix",
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
        return menu

    def action(self) -> ActionResult:
        if not transactions.check_transaction():
            return redirect(self.mode_url())

        if request.var("_delete"):
            role_id = RoleID(request.get_ascii_input_mandatory("_delete"))
            userroles.delete_role(role_id)
            _changes.add_change(
                "edit-roles", _("Deleted role '%s'") % role_id, sites=get_login_sites()
            )

        elif request.var("_clone"):
            role_id = RoleID(request.get_ascii_input_mandatory("_clone"))
            userroles.clone_role(role_id)
            _changes.add_change(
                "edit-roles", _("Created new role '%s'") % role_id, sites=get_login_sites()
            )

        return redirect(self.mode_url())

    def page(self) -> None:
        with table_element("roles") as table:

            users = userdb.load_users()
            for role in sorted(userroles.get_all_roles().values(), key=lambda a: (a.alias, a.name)):
                table.row()

                # Actions
                table.cell(_("Actions"), css=["buttons"])
                edit_url = folder_preserving_link([("mode", "edit_role"), ("edit", role.name)])
                clone_url = make_action_link([("mode", "roles"), ("_clone", role.name)])
                delete_url = make_confirm_link(
                    url=make_action_link([("mode", "roles"), ("_delete", role.name)]),
                    message=_("Do you really want to delete the role %s?") % role.name,
                )
                html.icon_button(edit_url, _("Properties"), "edit")
                html.icon_button(clone_url, _("Clone"), "clone")
                if not role.builtin:
                    html.icon_button(delete_url, _("Delete this role"), "delete")

                # ID
                table.cell(_("Name"), role.name)

                # Alias
                table.cell(_("Alias"), role.alias)

                # Type
                table.cell(_("Type"), _("builtin") if role.builtin else _("custom"))

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
                    HTML(", ").join(
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


@mode_registry.register
class ModeEditRole(WatoMode):
    @classmethod
    def name(cls) -> str:
        return "edit_role"

    @classmethod
    def permissions(cls) -> Collection[PermissionName]:
        return ["users"]

    @classmethod
    def parent_mode(cls) -> Optional[Type[WatoMode]]:
        return ModeRoles

    def __init__(self) -> None:
        super().__init__()

        # Make sure that all dynamic permissions are available (e.g. those for custom
        # views)
        load_dynamic_permissions()

    def _from_vars(self):
        self._role_id = RoleID(request.get_ascii_input_mandatory("edit"))
        self._role: UserRole = userroles.get_role(self._role_id)

    def title(self) -> str:
        return _("Edit role %s") % self._role_id

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        menu = make_simple_form_page_menu(
            _("Role"), breadcrumb, form_name="role", button_name="_save"
        )
        menu.inpage_search = PageMenuSearch()
        return menu

    def action(self) -> ActionResult:  # pylint: disable=too-many-branches
        if html.form_submitted("search"):
            return None

        # alias
        alias = request.get_str_input_mandatory("alias")
        unique, info = groups.is_alias_used("roles", self._role_id, alias)
        if not unique:
            assert info is not None
            raise MKUserError("alias", info)

        # id
        new_id = RoleID(request.get_ascii_input_mandatory("id"))
        if not new_id:
            raise MKUserError("id", "You have to provide a ID.")
        if not re.match("^[-a-z0-9A-Z_]*$", new_id):
            raise MKUserError(
                "id", _("Invalid role ID. Only the characters a-z, A-Z, 0-9, _ and - are allowed.")
            )
        if new_id != self._role_id:
            if userroles.role_exists(new_id):
                raise MKUserError("id", _("The ID is already used by another role"))

        self._role.name = new_id
        self._role.alias = alias

        # based on
        if not self._role.builtin:
            basedon = request.get_ascii_input_mandatory("basedon")
            if basedon not in builtin_role_ids:
                raise MKUserError(
                    "basedon", _("Invalid value for based on. Must be id of builtin rule.")
                )
            self._role.basedon = basedon

        # Permissions
        for var_name, value in request.itervars(prefix="perm_"):
            try:
                perm = permission_registry[var_name[5:]]
            except KeyError:
                continue

            if value == "yes":
                self._role.permissions[perm.name] = True
            elif value == "no":
                self._role.permissions[perm.name] = False
            elif value == "default":
                try:
                    del self._role.permissions[perm.name]
                except KeyError:
                    pass  # Already at defaults

        all_roles: Dict[RoleID, UserRole] = userroles.get_all_roles()
        del all_roles[self._role_id]
        self._role_id = RoleID(self._role.name)
        all_roles[self._role_id] = self._role

        if not self._role.builtin:
            userroles.rename_user_role(self._role_id, new_id)
        userroles.save_all_roles(all_roles)

        _changes.add_change(
            "edit-roles", _("Modified user role '%s'") % new_id, sites=get_login_sites()
        )
        return redirect(mode_url("roles"))

    def page(self) -> None:
        search = get_search_expression()

        html.begin_form("role", method="POST")

        # ID
        forms.header(_("Basic properties"), css="wide")
        forms.section(_("Internal ID"), simple=self._role.builtin, is_required=True)

        if self._role.builtin:
            html.write_text("%s (%s)" % (self._role_id, _("builtin role")))
            html.hidden_field("id", self._role_id)
        else:
            html.text_input("id", self._role_id)
            html.set_focus("id")

        # Alias
        forms.section(_("Alias"))
        html.help(_("An alias or description of the role"))
        html.text_input("alias", self._role.alias, size=50)

        # Based on
        if not self._role.builtin:
            forms.section(_("Based on role"))
            html.help(
                _(
                    "Each user defined role is based on one of the builtin roles. "
                    "When created it will start with all permissions of that role. When due to a software "
                    "update or installation of an addons new permissions appear, the user role will get or "
                    "not get those new permissions based on the default settings of the builtin role it's "
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
                "When you leave the permissions at &quot;default&quot; then they get their "
                "settings from the factory defaults (for builtin roles) or from the "
                "factory default of their base role (for user define roles). Factory defaults "
                "may change due to software updates. When choosing another base role, all "
                "permissions that are on default will reflect the new base role."
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
        html.end_form()


@mode_registry.register
class ModeRoleMatrix(WatoMode):
    @classmethod
    def name(cls) -> str:
        return "role_matrix"

    @classmethod
    def permissions(cls) -> Collection[PermissionName]:
        return ["users"]

    @classmethod
    def parent_mode(cls) -> Optional[Type[WatoMode]]:
        return ModeRoles

    def title(self) -> str:
        return _("Permission matrix")

    def page(self) -> None:
        for section in permission_section_registry.get_sorted_sections():
            with table_element(
                section.name,
                section.title,
                foldable=Foldable.FOLDABLE_SAVE_STATE,
            ) as table:

                permission_list = permission_registry.get_sorted_permissions(section)

                if not permission_list:
                    table.row()
                    table.cell(_("Permission"), _("No entries"), css=["wide"])
                    continue

                for perm in permission_list:
                    table.row()
                    table.cell(_("Permission"), perm.title, css=["wide"])

                    html.help(perm.description)

                    for role in sorted(
                        userroles.get_all_roles().values(), key=lambda a: (a.alias, a.name)
                    ):
                        base_on_id = role.basedon if role.basedon is not None else role.name
                        pvalue = role.permissions.get(perm.name)
                        if pvalue is None:
                            if base_on_id in perm.defaults:
                                icon_name: Optional[str] = "perm_yes_default"
                            else:
                                icon_name = None
                        else:
                            icon_name = "perm_%s" % (pvalue and "yes" or "no")

                        table.cell(role.name, css=["center"])
                        if icon_name:
                            html.icon(icon_name)

        html.close_table()
