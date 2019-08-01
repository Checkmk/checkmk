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
import time

# This is needed for at least CentOS 5.5
# TODO: Drop this until all supported platforms have newer versions available.
# It it not 100% sure if we need this before the OpenSSL import, but we play
# safe here and tell pylint about that.
# pylint: disable=wrong-import-position
os.environ["CRYPTOGRAPHY_ALLOW_OPENSSL_098"] = "1"
from OpenSSL import crypto

import cmk.utils.render
import cmk.utils.store as store

from cmk.gui.table import table_element
import cmk.gui.config as config
from cmk.gui.i18n import _
from cmk.gui.globals import html
from cmk.gui.valuespec import (
    Dictionary,
    Password,
    TextAreaUnicode,
    FileUpload,
    CascadingDropdown,
    TextUnicode,
)
from cmk.gui.exceptions import MKUserError


class KeypairStore(object):
    def __init__(self, path, attr):
        self._path = path
        self._attr = attr
        super(KeypairStore, self).__init__()

    def load(self):
        filename = self._path
        if not os.path.exists(filename):
            return {}

        variables = {self._attr: {}}
        exec (open(filename).read(), variables, variables)
        return variables[self._attr]

    def save(self, keys):
        store.mkdir(os.path.dirname(self._path))
        store.save_mk_file(self._path, "%s.update(%s)" % (self._attr, pprint.pformat(keys)))

    def choices(self):
        choices = []
        for key in self.load().itervalues():
            cert = crypto.load_certificate(crypto.FILETYPE_PEM, key["certificate"])
            digest = cert.digest("md5")
            choices.append((digest, key["alias"]))

        return sorted(choices, key=lambda x: x[1])

    def get_key_by_digest(self, digest):
        for key_id, key in self.load().items():
            other_cert = crypto.load_certificate(crypto.FILETYPE_PEM, key["certificate"])
            other_digest = other_cert.digest("md5")
            if other_digest == digest:
                return key_id, key
        raise KeyError()


class PageKeyManagement(object):
    edit_mode = "edit_key"
    upload_mode = "upload_key"
    download_mode = "download_key"

    def __init__(self):
        self.keys = self.load()
        super(PageKeyManagement, self).__init__()

    def title(self):
        raise NotImplementedError()

    def load(self):
        raise NotImplementedError()

    def save(self, keys):
        raise NotImplementedError()

    def buttons(self):
        self._back_button()
        if self._may_edit_config():
            html.context_button(_("Create Key"),
                                html.makeuri_contextless([("mode", self.edit_mode)]), "new")
            html.context_button(_("Upload Key"),
                                html.makeuri_contextless([("mode", self.upload_mode)]), "new")

    def _may_edit_config(self):
        return True

    def _back_button(self):
        raise NotImplementedError()

    def action(self):
        if self._may_edit_config() and html.request.has_var("_delete"):
            key_id = int(html.request.var("_delete"))
            if key_id not in self.keys:
                return

            key = self.keys[key_id]

            if self._key_in_use(key_id, key):
                raise MKUserError("", _("This key is still used."))

            message = self._delete_confirm_msg()
            if key["owner"] != config.user.id:
                message += _(
                    "<br><b>Note</b>: this key has created by user <b>%s</b>") % key["owner"]
            c = html.confirm(message, add_header=self.title())
            if c:
                self.delete(key_id)
                self.save(self.keys)

            elif c is False:
                return ""

    def delete(self, key_id):
        del self.keys[key_id]

    def _delete_confirm_msg(self):
        raise NotImplementedError()

    def _key_in_use(self, key_id, key):
        raise NotImplementedError()

    def _table_title(self):
        raise NotImplementedError()

    def page(self):
        with table_element(title=self._table_title(), searchable=False, sortable=False) as table:

            for key_id, key in sorted(self.keys.items()):
                cert = crypto.load_certificate(crypto.FILETYPE_PEM, key["certificate"])

                table.row()
                table.cell(_("Actions"), css="buttons")
                if self._may_edit_config():
                    delete_url = html.makeactionuri([("_delete", key_id)])
                    html.icon_button(delete_url, _("Delete this key"), "delete")
                download_url = html.makeuri_contextless([("mode", self.download_mode),
                                                         ("key", key_id)])
                html.icon_button(download_url, _("Download this key"), "download")
                table.cell(_("Description"), html.render_text(key["alias"]))
                table.cell(_("Created"), cmk.utils.render.date(key["date"]))
                table.cell(_("By"), html.render_text(key["owner"]))
                table.cell(_("Digest (MD5)"), html.render_text(cert.digest("md5")))


class PageEditKey(object):
    back_mode = "keys"

    def load(self):
        raise NotImplementedError()

    def save(self, keys):
        raise NotImplementedError()

    def buttons(self):
        html.context_button(_("Back"), html.makeuri_contextless([("mode", self.back_mode)]), "back")

    def action(self):
        if html.check_transaction():
            value = self._vs_key().from_html_vars("key")
            # Remove the secret key from known URL vars. Otherwise later constructed URLs
            # which use the current page context will contain the passphrase which could
            # leak the secret information
            html.request.del_var("key_p_passphrase")
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

        cert = create_self_signed_cert(pkey)
        return {
            "certificate": crypto.dump_certificate(crypto.FILETYPE_PEM, cert),
            "private_key": crypto.dump_privatekey(crypto.FILETYPE_PEM, pkey, "AES256", passphrase),
            "alias": alias,
            "owner": config.user.id,
            "date": time.time(),
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
            title=_("Properties"),
            elements=[
                ("alias", TextUnicode(
                    title=_("Description or comment"),
                    size=64,
                    allow_empty=False,
                )),
                ("passphrase",
                 Password(
                     title=_("Passphrase"),
                     help=self._passphrase_help(),
                     allow_empty=False,
                     is_stored_plain=False,
                 )),
            ],
            optional_keys=False,
            render="form",
        )

    def _passphrase_help(self):
        raise NotImplementedError()


class PageUploadKey(object):
    back_mode = "keys"

    def load(self):
        raise NotImplementedError()

    def save(self, keys):
        raise NotImplementedError()

    def buttons(self):
        html.context_button(_("Back"), html.makeuri_contextless([("mode", self.back_mode)]), "back")

    def action(self):
        if html.check_transaction():
            value = self._vs_key().from_html_vars("key")
            html.request.del_var("key_p_passphrase")
            self._vs_key().validate_value(value, "key")

            key_file = self._get_uploaded(value, "key_file")
            if not key_file:
                raise MKUserError(None, _("You need to provide a key file."))

            if not key_file.startswith("-----BEGIN ENCRYPTED PRIVATE KEY-----\n") \
               or "-----END ENCRYPTED PRIVATE KEY-----\n" not in key_file \
               or "-----BEGIN CERTIFICATE-----\n" not in key_file \
               or not key_file.endswith("-----END CERTIFICATE-----\n"):
                raise MKUserError(None, _("The file does not look like a valid key file."))

            self._upload_key(key_file, value)
            return self.back_mode

    def _get_uploaded(self, cert_spec, key):
        if key in cert_spec:
            if cert_spec[key][0] == "upload":
                return cert_spec[key][1][2]
            return cert_spec[key][1]

    def _upload_key(self, key_file, value):
        keys = self.load()

        new_id = 1
        for key_id in keys:
            new_id = max(new_id, key_id + 1)

        certificate = crypto.load_certificate(crypto.FILETYPE_PEM, key_file)

        this_digest = certificate.digest("md5")
        for key_id, key in keys.items():
            other_cert = crypto.load_certificate(crypto.FILETYPE_PEM, key["certificate"])
            other_digest = other_cert.digest("md5")
            if other_digest == this_digest:
                raise MKUserError(
                    None,
                    _("The key / certificate already exists (Key: %d, "
                      "Description: %s)") % (key_id, key["alias"]))

        # Use time from certificate
        def parse_asn1_generalized_time(timestr):
            return time.strptime(timestr, "%Y%m%d%H%M%SZ")

        created = time.mktime(parse_asn1_generalized_time(certificate.get_notBefore()))

        # Check for valid passphrase
        decrypt_private_key(key_file, value["passphrase"])

        # Split PEM for storing separated
        parts = key_file.split("-----END ENCRYPTED PRIVATE KEY-----\n", 1)
        key_pem = parts[0] + "-----END ENCRYPTED PRIVATE KEY-----\n"
        cert_pem = parts[1]

        key = {
            "certificate": cert_pem,
            "private_key": key_pem,
            "alias": value["alias"],
            "owner": config.user.id,
            "date": created,
        }

        keys[new_id] = key
        self.save(keys)

    def page(self):
        html.begin_form("key", method="POST")
        html.prevent_password_auto_completion()
        self._vs_key().render_input("key", {})
        html.button("upload", _("Upload"))
        self._vs_key().set_focus("key")
        html.hidden_fields()
        html.end_form()

    def _vs_key(self):
        return Dictionary(
            title=_("Properties"),
            elements=[
                ("alias", TextUnicode(
                    title=_("Description or comment"),
                    size=64,
                    allow_empty=False,
                )),
                ("passphrase",
                 Password(
                     title=_("Passphrase"),
                     help=self._passphrase_help(),
                     allow_empty=False,
                     is_stored_plain=False,
                 )),
                ("key_file",
                 CascadingDropdown(title=_("Key"),
                                   choices=[
                                       ("upload", _("Upload CRT/PEM File"), FileUpload()),
                                       ("text", _("Paste PEM Content"), TextAreaUnicode()),
                                   ])),
            ],
            optional_keys=False,
            render="form",
        )

    def _passphrase_help(self):
        raise NotImplementedError()


class PageDownloadKey(object):
    back_mode = "keys"

    def load(self):
        raise NotImplementedError()

    def save(self, keys):
        raise NotImplementedError()

    def buttons(self):
        html.context_button(_("Back"), html.makeuri_contextless([("mode", self.back_mode)]), "back")

    def action(self):
        if html.check_transaction():
            keys = self.load()

            try:
                key_id = int(html.request.var("key"))
            except ValueError:
                raise MKUserError(None, _("You need to provide a valid key id."))

            if key_id not in keys:
                raise MKUserError(None, _("You need to provide a valid key id."))

            private_key = keys[key_id]["private_key"]

            value = self._vs_key().from_html_vars("key")
            self._vs_key().validate_value(value, "key")
            decrypt_private_key(private_key, value["passphrase"])

            self._send_download(keys, key_id)
            return False

    def _send_download(self, keys, key_id):
        key = keys[key_id]
        html.response.headers["Content-Disposition"] = "Attachment; filename=%s" % self._file_name(
            key_id, key)
        html.response.headers["Content-type"] = "application/x-pem-file"
        html.write(key["private_key"])
        html.write(key["certificate"])

    def _file_name(self, key_id, key):
        raise NotImplementedError()

    def page(self):
        html.write(
            "<p>%s</p>" %
            _("To be able to download the key, you need to unlock the key by entering the "
              "passphrase. This is only done to verify that you are allowed to download the key. "
              "The key will be downloaded in encrypted form."))
        html.begin_form("key", method="POST")
        html.prevent_password_auto_completion()
        self._vs_key().render_input("key", {})
        html.button("upload", _("Download"))
        self._vs_key().set_focus("key")
        html.hidden_fields()
        html.end_form()

    def _vs_key(self):
        return Dictionary(
            title=_("Properties"),
            elements=[
                ("passphrase",
                 Password(
                     title=_("Passphrase"),
                     allow_empty=False,
                     is_stored_plain=False,
                 )),
            ],
            optional_keys=False,
            render="form",
        )


def create_self_signed_cert(pkey):
    cert = crypto.X509()
    cert.get_subject().O = "Check_MK Site %s" % config.omd_site()
    cert.get_subject().CN = config.user.id or "### Check_MK ###"
    cert.set_serial_number(1)
    cert.gmtime_adj_notBefore(0)
    cert.gmtime_adj_notAfter(30 * 365 * 24 * 60 * 60)  # valid for 30 years.
    cert.set_issuer(cert.get_subject())
    cert.set_pubkey(pkey)
    cert.sign(pkey, 'sha1')

    return cert


def decrypt_private_key(encrypted_private_key, passphrase):
    try:
        return crypto.load_privatekey(crypto.FILETYPE_PEM, encrypted_private_key, passphrase)
    except crypto.Error:
        raise MKUserError("key_p_passphrase", _("Invalid pass phrase"))
