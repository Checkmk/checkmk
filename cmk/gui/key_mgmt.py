#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pprint
import time
from pathlib import Path
from typing import Any, Literal, Mapping, Optional, Union

from OpenSSL import crypto

from livestatus import SiteId

import cmk.utils.render
import cmk.utils.store as store
from cmk.utils.site import omd_site
from cmk.utils.type_defs import UserId

from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.exceptions import FinalizeRequest, HTTPRedirect, MKUserError
from cmk.gui.htmllib.html import html
from cmk.gui.http import request, response
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.page_menu import (
    make_simple_form_page_menu,
    make_simple_link,
    PageMenu,
    PageMenuDropdown,
    PageMenuEntry,
    PageMenuTopic,
)
from cmk.gui.table import table_element
from cmk.gui.type_defs import ActionResult, Key
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.utils.urls import make_confirm_link, makeactionuri, makeuri_contextless
from cmk.gui.valuespec import (
    CascadingDropdown,
    Dictionary,
    FileUpload,
    Password,
    TextAreaUnicode,
    TextInput,
)


class KeypairStore:
    def __init__(self, path: str, attr: str) -> None:
        self._path = Path(path)
        self._attr = attr
        super().__init__()

    def load(self) -> dict[int, Key]:
        if not self._path.exists():
            return {}

        variables: dict[str, dict[int, dict[str, Any]]] = {self._attr: {}}
        with self._path.open("rb") as f:
            exec(f.read(), variables, variables)
        return self._parse(variables[self._attr])

    def save(self, keys: Mapping[int, Key]) -> None:
        store.makedirs(self._path.parent)
        store.save_mk_file(
            self._path, "%s.update(%s)" % (self._attr, pprint.pformat(self._unparse(keys)))
        )

    def _parse(self, raw_keys: Mapping[int, dict[str, Any]]) -> dict[int, Key]:
        return {key_id: Key.parse_obj(raw_key) for key_id, raw_key in raw_keys.items()}

    def _unparse(self, keys: Mapping[int, Key]) -> dict[int, dict[str, Any]]:
        return {key_id: key.dict() for key_id, key in keys.items()}

    def choices(self) -> list[tuple[str, str]]:
        choices = []
        for key in self.load().values():
            cert = crypto.load_certificate(crypto.FILETYPE_PEM, key.certificate.encode("ascii"))
            digest = cert.digest("md5").decode("ascii")
            choices.append((digest, key.alias))

        return sorted(choices, key=lambda x: x[1])

    def get_key_by_digest(self, digest: str) -> tuple[int, Key]:
        for key_id, key in self.load().items():
            other_cert = crypto.load_certificate(
                crypto.FILETYPE_PEM, key.certificate.encode("ascii")
            )
            other_digest = other_cert.digest("md5").decode("ascii")
            if other_digest == digest:
                return key_id, key
        raise KeyError()


class PageKeyManagement:
    edit_mode = "edit_key"
    upload_mode = "upload_key"
    download_mode = "download_key"

    def __init__(self, key_store: KeypairStore) -> None:
        super().__init__()
        self.key_store = key_store

    def title(self) -> str:
        raise NotImplementedError()

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        if not self._may_edit_config():
            return PageMenu(dropdowns=[], breadcrumb=breadcrumb)

        return PageMenu(
            dropdowns=[
                PageMenuDropdown(
                    name="keys",
                    title=_("Keys"),
                    topics=[
                        PageMenuTopic(
                            title=_("Add key"),
                            entries=[
                                PageMenuEntry(
                                    title=_("Add key"),
                                    icon_name="new",
                                    item=make_simple_link(
                                        makeuri_contextless(request, [("mode", self.edit_mode)])
                                    ),
                                    is_shortcut=True,
                                    is_suggested=True,
                                ),
                                PageMenuEntry(
                                    title=_("Upload key"),
                                    icon_name="upload",
                                    item=make_simple_link(
                                        makeuri_contextless(request, [("mode", self.upload_mode)])
                                    ),
                                    is_shortcut=True,
                                    is_suggested=True,
                                ),
                            ],
                        ),
                    ],
                ),
            ],
            breadcrumb=breadcrumb,
        )

    def _may_edit_config(self) -> bool:
        return True

    def action(self) -> ActionResult:
        if self._may_edit_config() and request.has_var("_delete"):
            key_id_as_str = request.var("_delete")
            if key_id_as_str is None:
                raise Exception("cannot happen")
            key_id = int(key_id_as_str)
            keys = self.key_store.load()
            if key_id not in keys:
                return None

            key = keys[key_id]

            if self._key_in_use(key_id, key):
                raise MKUserError("", _("This key is still used."))

            del keys[key_id]
            self._log_delete_action(key_id, key)
            self.key_store.save(keys)
        return None

    def _log_delete_action(self, key_id: int, key: Key) -> None:
        pass

    def _delete_confirm_msg(self) -> str:
        raise NotImplementedError()

    def _key_in_use(self, key_id: int, key: Key) -> bool:
        raise NotImplementedError()

    def _table_title(self) -> str:
        raise NotImplementedError()

    def page(self) -> None:
        with table_element(title=self._table_title(), searchable=False, sortable=False) as table:

            for key_id, key in sorted(self.key_store.load().items()):
                cert = crypto.load_certificate(crypto.FILETYPE_PEM, key.certificate.encode("ascii"))

                table.row()
                table.cell(_("Actions"), css=["buttons"])
                if self._may_edit_config():
                    message = self._delete_confirm_msg()
                    if key.owner != user.id:
                        message += (
                            _("<br><b>Note</b>: this key has created by user <b>%s</b>") % key.owner
                        )

                    delete_url = make_confirm_link(
                        url=makeactionuri(request, transactions, [("_delete", key_id)]),
                        message=message,
                    )
                    html.icon_button(delete_url, _("Delete this key"), "delete")
                download_url = makeuri_contextless(
                    request,
                    [("mode", self.download_mode), ("key", key_id)],
                )
                html.icon_button(download_url, _("Download this key"), "download")
                table.cell(_("Description"), key.alias)
                table.cell(_("Created"), cmk.utils.render.date(key.date))
                table.cell(_("By"), key.owner)
                table.cell(_("Digest (MD5)"), cert.digest("md5").decode("ascii"))


class PageEditKey:
    back_mode: str

    def __init__(self, key_store: KeypairStore, passphrase_min_len: Optional[int] = None) -> None:
        self._minlen = passphrase_min_len
        self.key_store = key_store

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        return make_simple_form_page_menu(
            _("Key"), breadcrumb, form_name="key", button_name="_save", save_title=_("Create")
        )

    def action(self) -> ActionResult:
        if transactions.check_transaction():
            value = self._vs_key().from_html_vars("key")
            # Remove the secret key from known URL vars. Otherwise later constructed URLs
            # which use the current page context will contain the passphrase which could
            # leak the secret information
            request.del_var("key_p_passphrase")
            self._vs_key().validate_value(value, "key")
            self._create_key(value["alias"], value["passphrase"])
            # FIXME: This leads to a circular import otherwise. This module (cmk.gui.key_mgmt) is
            #  clearly outside of either cmk.gui.plugins.wato and cmk.gui.cee.plugins.wato so this
            #  is obviously a very simple module-layer violation. This whole module should either
            #    * be moved into cmk.gui.cee.plugins.wato
            #    * or cmk.gui.cee.plugins.wato.module_registry should be moved up
            #  Either way, this is outside my scope right now and shall be fixed.
            from cmk.gui.plugins.wato.utils.base_modes import mode_url

            return HTTPRedirect(mode_url(self.back_mode))
        return None

    def _create_key(self, alias: str, passphrase: str) -> None:
        keys = self.key_store.load()

        new_id = 1
        for key_id in keys:
            new_id = max(new_id, key_id + 1)

        keys[new_id] = generate_key(alias, passphrase, user.id, omd_site())
        self.key_store.save(keys)

    def page(self) -> None:
        # Currently only "new" is supported
        html.begin_form("key", method="POST")
        html.prevent_password_auto_completion()
        self._vs_key().render_input("key", {})
        self._vs_key().set_focus("key")
        html.hidden_fields()
        html.end_form()

    def _vs_key(self) -> Dictionary:
        return Dictionary(
            title=_("Properties"),
            elements=[
                (
                    "alias",
                    TextInput(
                        title=_("Description or comment"),
                        size=64,
                        allow_empty=False,
                    ),
                ),
                (
                    "passphrase",
                    Password(
                        title=_("Passphrase"),
                        help=self._passphrase_help(),
                        allow_empty=False,
                        is_stored_plain=False,
                        minlen=self._minlen,
                    ),
                ),
            ],
            optional_keys=False,
            render="form",
        )

    def _passphrase_help(self):
        raise NotImplementedError()


class PageUploadKey:
    back_mode: str

    def __init__(self, key_store: KeypairStore) -> None:
        super().__init__()
        self.key_store = key_store

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        return make_simple_form_page_menu(
            _("Key"), breadcrumb, form_name="key", button_name="_save", save_title=_("Upload")
        )

    def action(self) -> ActionResult:
        if transactions.check_transaction():
            value = self._vs_key().from_html_vars("key")
            request.del_var("key_p_passphrase")
            self._vs_key().validate_value(value, "key")

            key_file = self._get_uploaded(value["key_file"])
            if not key_file:
                raise MKUserError(None, _("You need to provide a key file."))

            if (
                not key_file.startswith("-----BEGIN ENCRYPTED PRIVATE KEY-----\n")
                or "-----END ENCRYPTED PRIVATE KEY-----\n" not in key_file
                or "-----BEGIN CERTIFICATE-----\n" not in key_file
                or not key_file.endswith("-----END CERTIFICATE-----\n")
            ):
                raise MKUserError(None, _("The file does not look like a valid key file."))

            self._upload_key(key_file, value["alias"], value["passphrase"])
            # FIXME: This leads to a circular import otherwise. This module (cmk.gui.key_mgmt) is
            #  clearly outside of either cmk.gui.plugins.wato and cmk.gui.cee.plugins.wato so this
            #  is obviously a very simple module-layer violation. This whole module should either
            #    * be moved into cmk.gui.cee.plugins.wato
            #    * or cmk.gui.cee.plugins.wato.module_registry should be moved up
            #  Either way, this is outside my scope right now and shall be fixed.
            from cmk.gui.plugins.wato.utils.base_modes import mode_url

            return HTTPRedirect(mode_url(self.back_mode), code=302)
        return None

    def _get_uploaded(
        self,
        cert_spec: Union[
            tuple[Literal["upload"], tuple[str, str, bytes]], tuple[Literal["text"], str]
        ],
    ) -> str:
        if cert_spec[0] == "upload":
            return cert_spec[1][2].decode("ascii")
        return cert_spec[1]

    def _upload_key(self, key_file: str, alias: str, passphrase: str) -> None:
        keys = self.key_store.load()

        new_id = 1
        for key_id in keys:
            new_id = max(new_id, key_id + 1)

        certificate = crypto.load_certificate(crypto.FILETYPE_PEM, key_file.encode("ascii"))

        this_digest = certificate.digest("md5").decode("ascii")
        for key_id, key in keys.items():
            other_cert = crypto.load_certificate(
                crypto.FILETYPE_PEM, key.certificate.encode("ascii")
            )
            other_digest = other_cert.digest("md5").decode("ascii")
            if other_digest == this_digest:
                raise MKUserError(
                    None,
                    _("The key / certificate already exists (Key: %d, " "Description: %s)")
                    % (key_id, key.alias),
                )

        # Use time from certificate
        def parse_asn1_generalized_time(timestr: str) -> time.struct_time:
            return time.strptime(timestr, "%Y%m%d%H%M%SZ")

        not_before = certificate.get_notBefore()
        assert not_before is not None  # TODO: Why is this true?
        created = time.mktime(parse_asn1_generalized_time(not_before.decode("ascii")))

        # Check for valid passphrase
        decrypt_private_key(key_file, passphrase)

        # Split PEM for storing separated
        parts = key_file.split("-----END ENCRYPTED PRIVATE KEY-----\n", 1)
        key_pem = parts[0] + "-----END ENCRYPTED PRIVATE KEY-----\n"
        cert_pem = parts[1]

        key = Key(
            certificate=cert_pem,
            private_key=key_pem,
            alias=alias,
            owner=user.id,
            date=created,
            not_downloaded=False,
        )

        keys[new_id] = key
        self.key_store.save(keys)

    def page(self) -> None:
        html.begin_form("key", method="POST")
        html.prevent_password_auto_completion()
        self._vs_key().render_input("key", {})
        self._vs_key().set_focus("key")
        html.hidden_fields()
        html.end_form()

    def _vs_key(self) -> Dictionary:
        return Dictionary(
            title=_("Properties"),
            elements=[
                (
                    "alias",
                    TextInput(
                        title=_("Description or comment"),
                        size=64,
                        allow_empty=False,
                    ),
                ),
                (
                    "passphrase",
                    Password(
                        title=_("Passphrase"),
                        help=self._passphrase_help(),
                        allow_empty=False,
                        is_stored_plain=False,
                    ),
                ),
                (
                    "key_file",
                    CascadingDropdown(
                        title=_("Key"),
                        choices=[
                            ("upload", _("Upload CRT/PEM File"), FileUpload()),
                            ("text", _("Paste PEM Content"), TextAreaUnicode()),
                        ],
                    ),
                ),
            ],
            optional_keys=False,
            render="form",
        )

    def _passphrase_help(self) -> str:
        raise NotImplementedError()


class PageDownloadKey:
    back_mode: str

    def __init__(self, key_store: KeypairStore) -> None:
        super().__init__()
        self.key_store = key_store

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        return make_simple_form_page_menu(
            _("Key"), breadcrumb, form_name="key", button_name="_save", save_title=_("Download")
        )

    def action(self) -> ActionResult:
        if transactions.check_transaction():
            keys = self.key_store.load()

            try:
                key_id_str = request.var("key")
                if key_id_str is None:
                    raise Exception("cannot happen")  # is this really the case?
                key_id = int(key_id_str)
            except ValueError:
                raise MKUserError(None, _("You need to provide a valid key id."))

            if key_id not in keys:
                raise MKUserError(None, _("You need to provide a valid key id."))

            private_key = keys[key_id].private_key

            value = self._vs_key().from_html_vars("key")
            self._vs_key().validate_value(value, "key")
            decrypt_private_key(private_key, value["passphrase"])

            self._send_download(keys, key_id)
            return FinalizeRequest(code=200)
        return None

    def _send_download(self, keys: dict[int, Key], key_id: int) -> None:
        key = keys[key_id]
        response.headers["Content-Disposition"] = "Attachment; filename=%s" % self._file_name(
            key_id, key
        )
        response.headers["Content-type"] = "application/x-pem-file"
        response.set_data(key.private_key + key.certificate)

    def _file_name(self, key_id: int, key: Key) -> str:
        raise NotImplementedError()

    def page(self) -> None:
        html.p(
            _(
                "To be able to download the key, you need to unlock the key by entering the "
                "passphrase. This is only done to verify that you are allowed to download the key. "
                "The key will be downloaded in encrypted form."
            )
        )
        html.begin_form("key", method="POST")
        html.prevent_password_auto_completion()
        self._vs_key().render_input("key", {})
        self._vs_key().set_focus("key")
        html.hidden_fields()
        html.end_form()

    def _vs_key(self) -> Dictionary:
        return Dictionary(
            title=_("Properties"),
            elements=[
                (
                    "passphrase",
                    Password(
                        title=_("Passphrase"),
                        allow_empty=False,
                        is_stored_plain=False,
                    ),
                ),
            ],
            optional_keys=False,
            render="form",
        )


def generate_key(alias: str, passphrase: str, user_id: Optional[UserId], site_id: SiteId) -> Key:
    pkey = crypto.PKey()
    pkey.generate_key(crypto.TYPE_RSA, 2048)

    cert = create_self_signed_cert(pkey, user_id, site_id)
    return Key(
        certificate=crypto.dump_certificate(crypto.FILETYPE_PEM, cert).decode("ascii"),
        private_key=crypto.dump_privatekey(
            crypto.FILETYPE_PEM, pkey, "AES256", passphrase.encode("utf-8")
        ).decode("ascii"),
        alias=alias,
        owner=user_id,
        date=time.time(),
        not_downloaded=True,
    )


def create_self_signed_cert(
    pkey: crypto.PKey, user_id: Optional[UserId], site_id: SiteId
) -> crypto.X509:
    cert = crypto.X509()
    cert.get_subject().O = f"Check_MK Site {site_id}"
    cert.get_subject().CN = user_id or "### Check_MK ###"
    cert.set_serial_number(1)
    cert.gmtime_adj_notBefore(0)
    cert.gmtime_adj_notAfter(30 * 365 * 24 * 60 * 60)  # valid for 30 years.
    cert.set_issuer(cert.get_subject())
    cert.set_pubkey(pkey)
    cert.sign(pkey, "sha1")

    return cert


def decrypt_private_key(encrypted_private_key: str, passphrase: str) -> crypto.PKey:
    try:
        return crypto.load_privatekey(
            crypto.FILETYPE_PEM, encrypted_private_key, passphrase.encode("utf-8")
        )
    except crypto.Error:
        raise MKUserError("key_p_passphrase", _("Invalid pass phrase"))
