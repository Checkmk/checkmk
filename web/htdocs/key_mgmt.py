#!/usr/bin/python
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

import os
import pprint
from OpenSSL import crypto

import table
import config
from valuespec import *
from lib import make_nagios_directory, create_user_file


class KeypairStore(object):
    def __init__(self, path, attr):
        self._path = path
        self._attr = attr
        super(KeypairStore, self).__init__()


    def load(self):
        filename = self._path
        if not os.path.exists(filename):
            return {}

        variables = { self._attr : {} }
        execfile(filename, variables, variables)
        return variables[self._attr]


    def save(self, keys):
        make_nagios_directory(os.path.dirname(self._path))
        out = create_user_file(self._path, "w")
        out.write("# Written by WATO\n# encoding: utf-8\n\n")
        out.write("%s.update(%s)\n\n" % (self._attr, pprint.pformat(keys)))


    def choices(self):
        return sorted([ (ident, key["alias"]) for ident, key in self.load().items() ],
                        key=lambda k: k[1])




class PageKeyManagement(object):
    edit_mode = "edit_key"

    def __init__(self):
        self.keys = self.load()
        super(PageKeyManagement, self).__init__()


    def load(self):
        raise NotImplementedError()


    def save(self):
        raise NotImplementedError()


    def buttons(self):
        self._back_button()
        html.context_button(_("Create Key"), html.makeuri_contextless(
                                      [("mode", self.edit_mode)]), "new")


    def _back_button(self):
        raise NotImplementedError()


    def action(self):
        if html.has_var("_delete"):
            key_id = int(html.var("_delete"))
            if key_id not in self.keys:
                return

            key = self.keys[key_id]

            if self._key_in_use(key_id, key):
                raise MKUserError("", _("This key is still used."))

            message = self._delete_confirm_msg()
            if key["owner"] != config.user_id:
                message += _("<br><b>Note</b>: this key has created by user <b>%s</b>") % key["owner"]
            c = html.confirm(message, add_header=self.title())
            if c:
                self.delete(key_id)
                self.save(self.keys)

            elif c == False:
                return ""


    def delete(self, key_id):
        del self.keys[key_id]


    def _delete_confirm_msg(self):
        raise NotImplementedError()


    def _key_in_use(self, key):
        raise NotImplementedError()


    def page(self):
        table.begin(title = self._table_title())

        for key_id, key in sorted(self.keys.items()):
            table.row()
            table.cell(_("Actions"), css="buttons")
            delete_url = html.makeactionuri([("_delete", key_id)])
            html.icon_button(delete_url, _("Delete this key"), "delete")
            table.cell(_("Description"), key["alias"])
            table.cell(_("Created"), date_human_readable(key["date"]))
            table.cell(_("By"), key["owner"])
        table.end()



class PageEditKey(object):
    back_mode = "keys"

    def load(self):
        raise NotImplementedError()


    def save(self):
        raise NotImplementedError()


    def buttons(self):
        html.context_button(_("Back"), html.makeuri_contextless(
                                            [("mode", self.back_mode)]), "back")


    def action(self):
        if html.check_transaction():
            value = self._vs_key().from_html_vars("key")
            self._vs_key().validate_value(value, "key")
            self._create_key(value)
            return self.back_mode


    def _create_key(self, value):
        keys = self.load()

        new_id = 1
        for key_id in keys:
            new_id = max(new_id, key_id + 1)

        keys[new_id] = self._generate_key(value["alias"], value["passphrase"])
        self.save(keys)


    def _generate_key(self, alias, passphrase):
        pkey = crypto.PKey()
        pkey.generate_key(crypto.TYPE_RSA, 2048)

        # create a self-signed cert
        cert = crypto.X509()
        cert.get_subject().O = "Check_MK Site %s" % defaults.omd_site
        cert.get_subject().CN = config.user_id
        cert.set_serial_number(1)
        cert.gmtime_adj_notBefore(0)
        cert.gmtime_adj_notAfter(30*365*24*60*60) # valid for 30 years.
        cert.set_issuer(cert.get_subject())
        cert.set_pubkey(pkey)
        cert.sign(pkey, 'sha1')

        return {
            "certificate" : crypto.dump_certificate(crypto.FILETYPE_PEM, cert),
            "private_key" : crypto.dump_privatekey(crypto.FILETYPE_PEM, pkey, "AES256", passphrase),
            "alias"       : alias,
            "owner"       : config.user_id,
            "date"        : time.time(),
        }


    def page(self):
        # Currently only "new" is supported
        html.begin_form("key", method="POST")
        html.prevent_password_auto_completion()
        self._vs_key().render_input("key", {})
        html.button("create", _("Create"))
        self._vs_key().set_focus("key")
        html.hidden_fields()
        html.end_form()


    def _vs_key(self):
        return Dictionary(
            title = _("Properties"),
            elements = [
                ( "alias",
                  TextUnicode(
                      title = _("Description or comment"),
                      size = 64,
                      allow_empty = False,
                )),
                ( "passphrase",
                  Password(
                      title = _("Passphrase"),
                      help = self._passphrase_help(),
                      allow_empty = False,
                )),
            ],
            optional_keys = False,
            render = "form",
        )


    def _passphrase_help(self):
        raise NotImplementedError()
