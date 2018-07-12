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
import cmk.gui.watolib as watolib
import cmk.gui.userdb as userdb
import cmk.gui.table as table
# TODO: Does this import make sense here? only forms.end() is used. Why?
import cmk.gui.forms as forms
from cmk.gui.i18n import _
from cmk.gui.globals import html
from cmk.gui.exceptions import MKUserError
from cmk.gui.valuespec import (
    Dictionary,
    ID,
    FixedValue,
    TextUnicode,
    PasswordSpec,
    Alternative,
    DropdownChoice,
    DualListChoice,
)

from cmk.gui.plugins.wato import (
    WatoMode,
    global_buttons,
    wato_confirm,
    add_change,
    make_action_link,
)

class ModePasswords(WatoMode, watolib.PasswordStore):
    @classmethod
    def name(cls):
        return "passwords"


    @classmethod
    def permissions(cls):
        return ["passwords"]


    def __init__(self):
        super(ModePasswords, self).__init__()
        self._contact_groups = userdb.load_group_information().get("contact", {})


    def title(self):
        return _("Passwords")


    def buttons(self):
        global_buttons()
        html.context_button(_("New password"), html.makeuri_contextless([("mode", "edit_password")]), "new")


    def action(self):
        if not html.transaction_valid():
            return

        confirm = wato_confirm(_("Confirm deletion of password"),
                        _("The password may be used in checks. If you delete the password, the "
                          "checks won't be able to authenticate with this password anymore."
                          "<br><br>Do you really want to delete this password?"))
        if confirm == False:
            return False

        elif confirm:
            html.check_transaction() # invalidate transid

            passwords = self._load_for_modification()

            ident = html.var("_delete")
            if ident not in passwords:
                raise MKUserError("ident", _("This password does not exist."))

            add_change("delete-password", _("Removed the password '%s'") % ident)
            del passwords[ident]
            self._save(passwords)

            return None, _("The password has been deleted.")


    def page(self):
        html.p(_("This password management module stores the passwords you use in your checks and "
                 "special agents in a central place. Please note that this password store is no "
                 "kind of password safe. Your passwords will not be encrypted."))
        html.p(_("All the passwords you store in your monitoring configuration, "
                 "including this password store, are needed in plain text to contact remote systems "
                 "for monitoring. So all those passwords have to be stored readable by the monitoring."))


        passwords = self._owned_passwords()
        table.begin("passwords", _("Passwords"))
        for ident, password in sorted(passwords.items(), key=lambda e: e[1]["title"]):
            table.row()
            self._password_row(ident, password)

        table.end()


    def _password_row(self, ident, password):
        table.cell(_("Actions"), css="buttons")
        edit_url = html.makeuri_contextless([("mode", "edit_password"), ("ident", ident)])
        html.icon_button(edit_url, _("Edit this password"), "edit")
        delete_url = make_action_link([("mode", "passwords"), ("_delete", ident)])
        html.icon_button(delete_url, _("Delete this password"), "delete")

        table.cell(_("Title"), html.render_text(password["title"]))
        table.cell(_("Editable by"))
        if password["owned_by"] == None:
            html.write_text(_("Administrators (having the permission "
                              "\"Write access to all passwords\")"))
        else:
            html.write_text(self._contact_group_alias(password["owned_by"]))
        table.cell(_("Shared with"))
        if not password["shared_with"]:
            html.write_text(_("Not shared"))
        else:
            html.write_text(", ".join([ self._contact_group_alias(g) for g in password["shared_with"]]))


    def _contact_group_alias(self, name):
        return self._contact_groups.get(name, {"alias": name})["alias"]



class ModeEditPassword(WatoMode, watolib.PasswordStore):
    @classmethod
    def name(cls):
        return "edit_password"


    @classmethod
    def permissions(cls):
        return ["passwords"]


    def __init__(self):
        super(ModeEditPassword, self).__init__()
        ident = html.var("ident")

        if ident != None:
            try:
                password = self._owned_passwords()[ident]
            except KeyError:
                raise MKUserError("ident", _("This password does not exist."))

            self._new   = False
            self._ident = ident
            self._cfg   = password
            self._title = _("Edit password: %s") % password["title"]
        else:
            self._new   = True
            self._ident = None
            self._cfg   = {}
            self._title = _("New password")


    def title(self):
        return self._title


    def buttons(self):
        html.context_button(_("Back"), html.makeuri_contextless([("mode", "passwords")]), "back")


    def valuespec(self):
        return Dictionary(
            title         = _("Password"),
            elements      = self._vs_elements(),
            optional_keys = ["contact_groups"],
            render        = "form", )


    def _vs_elements(self):
        if self._new:
            ident_attr = [
                ("ident", ID(
                    title = _("Unique ID"),
                    help = _("The ID must be a unique text. It will be used as an internal key "
                             "when objects refer to this password."),
                    allow_empty = False,
                    size = 12,
                )),
            ]
        else:
            ident_attr = [
                ("ident", FixedValue(self._ident,
                    title = _("Unique ID"),
                )),
            ]

        if config.user.may("wato.edit_all_passwords"):
            admin_element = [
                FixedValue(None,
                    title = _("Administrators"),
                    totext = _("Administrators (having the permission "
                               "\"Write access to all passwords\")"),
                )
            ]
        else:
            admin_element = []

        return ident_attr + [
            ("title", TextUnicode(
                title = _("Title"),
                allow_empty = False,
                size = 64,
            )),
            ("password", PasswordSpec(
                title = _("Password"),
                allow_empty = False,
                hidden = True,
            )),
            ("owned_by", Alternative(
                title = _("Editable by"),
                help  = _("Each password is owned by a group of users which are able to edit, "
                          "delete and use existing passwords."),
                style = "dropdown",
                elements = admin_element + [
                    DropdownChoice(
                        title = _("Members of the contact group:"),
                        choices = lambda: self.__contact_group_choices(only_own=True),
                        invalid_choice = "complain",
                        empty_text = _("You need to be member of at least one contact group to be able to "
                                       "create a password."),
                        invalid_choice_title = _("Group not existant or not member"),
                        invalid_choice_error = _("The choosen group is either not existant "
                                                 "anymore or you are not a member of this "
                                                 "group. Please choose another one."),
                    ),
                ]
            )),
            ("shared_with", DualListChoice(
                title = _("Share with"),
                help  = _("By default only the members of the owner contact group are permitted "
                          "to use a a configured password. It is possible to share a password with "
                          "other groups of users to make them able to use a password in checks."),
                choices = self.__contact_group_choices,
                autoheight = False,
            )),
        ]


    def __contact_group_choices(self, only_own=False):
        contact_groups = userdb.load_group_information().get("contact", {})

        if only_own:
            user_groups = userdb.contactgroups_of_user(config.user.id)
        else:
            user_groups = []

        entries = [ (c, g['alias']) for c, g in contact_groups.items()
                    if not only_own or c in user_groups ]
        return sorted(entries)


    def action(self):
        if html.transaction_valid():
            vs = self.valuespec()

            config = vs.from_html_vars("_edit")
            vs.validate_value(config, "_edit")

            if "ident" in config:
                self._ident = config.pop("ident")
            self._cfg = config

            passwords = self._load_for_modification()

            if self._new and self._ident in passwords:
                raise MKUserError(None, _("This ID is already in use. Please choose another one."))

            passwords[self._ident] = self._cfg

            if self._new:
                add_change("add-password", _("Added the password '%s'") % self._ident)
            else:
                add_change("edit-password", _("Edited the password '%s'") % self._ident)

            self._save(passwords)

        return "passwords"


    def page(self):
        html.begin_form("edit", method="POST")
        html.prevent_password_auto_completion()

        vs = self.valuespec()

        vs.render_input("_edit", self._cfg)
        vs.set_focus("_edit")
        forms.end()

        html.button("save", _("Save"))
        html.hidden_fields()
        html.end_form()
