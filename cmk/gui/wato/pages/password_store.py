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

import cmk.gui.config as config
import cmk.gui.userdb as userdb
from cmk.gui.i18n import _
from cmk.gui.globals import html
from cmk.gui.valuespec import (
    FixedValue,
    PasswordSpec,
    Alternative,
    DropdownChoice,
    DualListChoice,
)

from cmk.gui.watolib.groups import load_group_information
from cmk.gui.watolib.password_store import PasswordStore
from cmk.gui.plugins.wato import (
    ConfigDomainCore,
    SimpleModeType,
    SimpleListMode,
    SimpleEditMode,
    mode_registry,
)


class PasswordStoreModeType(SimpleModeType):
    def type_name(self):
        return "password"

    def name_singular(self):
        return _("password")

    def is_site_specific(self):
        return False

    def can_be_disabled(self):
        return False

    def affected_config_domains(self):
        return [ConfigDomainCore]


@mode_registry.register
class ModePasswords(SimpleListMode):
    @classmethod
    def name(cls):
        return "passwords"

    @classmethod
    def permissions(cls):
        return ["passwords"]

    def __init__(self):
        super(ModePasswords, self).__init__(
            mode_type=PasswordStoreModeType(),
            store=PasswordStore(),
        )
        self._contact_groups = load_group_information().get("contact", {})

    def title(self):
        return _("Passwords")

    def _table_title(self):
        return _("Passwords")

    def _delete_confirm_message(self):
        return " ".join([
            _("The password may be used in checks. If you delete the password, "
              "the checks won't be able to authenticate with this password anymore."),
            super(ModePasswords, self)._delete_confirm_message()
        ])

    def page(self):
        html.p(
            _("This password management module stores the passwords you use in your checks and "
              "special agents in a central place. Please note that this password store is no "
              "kind of password safe. Your passwords will not be encrypted."))
        html.p(
            _("All the passwords you store in your monitoring configuration, "
              "including this password store, are needed in plain text to contact remote systems "
              "for monitoring. So all those passwords have to be stored readable by the monitoring."
             ))
        super(ModePasswords, self).page()

    def _show_entry_cells(self, table, ident, entry):
        table.cell(_("Title"), html.render_text(entry["title"]))
        table.cell(_("Editable by"))
        if entry["owned_by"] is None:
            html.write_text(
                _("Administrators (having the permission "
                  "\"Write access to all passwords\")"))
        else:
            html.write_text(self._contact_group_alias(entry["owned_by"]))
        table.cell(_("Shared with"))
        if not entry["shared_with"]:
            html.write_text(_("Not shared"))
        else:
            html.write_text(", ".join([self._contact_group_alias(g) for g in entry["shared_with"]]))

    def _contact_group_alias(self, name):
        return self._contact_groups.get(name, {"alias": name})["alias"]


@mode_registry.register
class ModeEditPassword(SimpleEditMode):
    @classmethod
    def name(cls):
        return "edit_password"

    @classmethod
    def permissions(cls):
        return ["passwords"]

    def __init__(self):
        super(ModeEditPassword, self).__init__(
            mode_type=PasswordStoreModeType(),
            store=PasswordStore(),
        )

    def _vs_individual_elements(self):
        if config.user.may("wato.edit_all_passwords"):
            admin_element = [
                FixedValue(
                    None,
                    title=_("Administrators"),
                    totext=_("Administrators (having the permission "
                             "\"Write access to all passwords\")"),
                )
            ]
        else:
            admin_element = []

        return [
            ("password", PasswordSpec(
                title=_("Password"),
                allow_empty=False,
            )),
            ("owned_by",
             Alternative(
                 title=_("Editable by"),
                 help=_("Each password is owned by a group of users which are able to edit, "
                        "delete and use existing passwords."),
                 style="dropdown",
                 elements=admin_element + [
                     DropdownChoice(
                         title=_("Members of the contact group:"),
                         choices=lambda: self._contact_group_choices(only_own=True),
                         invalid_choice="complain",
                         empty_text=_(
                             "You need to be member of at least one contact group to be able to "
                             "create a password."),
                         invalid_choice_title=_("Group not existant or not member"),
                         invalid_choice_error=_("The choosen group is either not existant "
                                                "anymore or you are not a member of this "
                                                "group. Please choose another one."),
                     ),
                 ])),
            ("shared_with",
             DualListChoice(
                 title=_("Share with"),
                 help=_("By default only the members of the owner contact group are permitted "
                        "to use a a configured password. It is possible to share a password with "
                        "other groups of users to make them able to use a password in checks."),
                 choices=self._contact_group_choices,
                 autoheight=False,
             )),
        ]

    def _contact_group_choices(self, only_own=False):
        contact_groups = load_group_information().get("contact", {})

        if only_own:
            user_groups = userdb.contactgroups_of_user(config.user.id)
        else:
            user_groups = []

        entries = [
            (c, g['alias']) for c, g in contact_groups.items() if not only_own or c in user_groups
        ]
        return sorted(entries, key=lambda x: x[1])
