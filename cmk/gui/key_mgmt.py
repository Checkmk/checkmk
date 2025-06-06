#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pprint
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Literal

from dateutil.relativedelta import relativedelta

from livestatus import SiteId

import cmk.utils.render
import cmk.utils.store as store
from cmk.utils.crypto import HashAlgorithm
from cmk.utils.crypto.certificate import (
    CertificateWithPrivateKey,
    InvalidPEMError,
    WrongPasswordError,
)
from cmk.utils.crypto.password import Password as PasswordType
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
from cmk.gui.utils.csrf_token import check_csrf_token
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.utils.urls import make_confirm_delete_link, makeactionuri, makeuri_contextless
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
        with store.locked(self._path):
            store.save_mk_file(
                self._path, f"{self._attr}.update({pprint.pformat(self._unparse(keys))})"
            )

    def _parse(self, raw_keys: Mapping[int, dict[str, Any]]) -> dict[int, Key]:
        return {key_id: Key.parse_obj(raw_key) for key_id, raw_key in raw_keys.items()}

    def _unparse(self, keys: Mapping[int, Key]) -> dict[int, dict[str, Any]]:
        return {key_id: key.dict() for key_id, key in keys.items()}

    def choices(self) -> list[tuple[str, str]]:
        choices = []
        for key in self.load().values():
            choices.append((key.fingerprint(HashAlgorithm.MD5), key.alias))
        return sorted(choices, key=lambda x: x[1])

    def get_key_by_digest(self, digest: str) -> tuple[int, Key]:
        for key_id, key in self.load().items():
            if key.fingerprint(HashAlgorithm.MD5) == digest:
                return key_id, key
        raise KeyError()

    def add(self, key: Key) -> None:
        keys = self.load()
        new_id = max(keys, default=0) + 1

        this_digest = key.fingerprint(HashAlgorithm.MD5)
        for key_id, stored_key in keys.items():
            if stored_key.fingerprint(HashAlgorithm.MD5) == this_digest:
                raise MKUserError(
                    None,
                    _("The key pair already exists (Key: %d, Description: %s)")
                    % (key_id, stored_key.alias),
                )

        keys[new_id] = key
        self.save(keys)


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
        check_csrf_token()

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

    def _delete_confirm_title(self, nr: int) -> str:
        raise NotImplementedError()

    def _key_in_use(self, key_id: int, key: Key) -> bool:
        raise NotImplementedError()

    def _table_title(self) -> str:
        raise NotImplementedError()

    def page(self) -> None:
        with table_element(title=self._table_title(), searchable=False, sortable=False) as table:

            for nr, (key_id, key) in enumerate(sorted(self.key_store.load().items())):
                table.row()
                table.cell("#", css=["narrow nowrap"])
                html.write_text(nr)
                table.cell(_("Actions"), css=["buttons"])
                if self._may_edit_config():
                    message = self._delete_confirm_msg()
                    if key.owner != user.id:
                        message += (
                            _("<br><br><b>Note</b>: this key was created by user <b>%s</b>")
                            % key.owner
                        )

                    delete_url = make_confirm_delete_link(
                        url=makeactionuri(request, transactions, [("_delete", key_id)]),
                        title=self._delete_confirm_title(nr),
                        suffix=key.alias,
                        message=message,
                        warning=True,
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
                table.cell(_("Digest (MD5)"), key.fingerprint(HashAlgorithm.MD5))
                table.cell(_("Key ID"), key_id)


class PageEditKey:
    back_mode: str

    def __init__(self, key_store: KeypairStore, passphrase_min_len: int | None = None) -> None:
        self._minlen = passphrase_min_len
        self.key_store = key_store

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        return make_simple_form_page_menu(
            _("Key"), breadcrumb, form_name="key", button_name="_save", save_title=_("Create")
        )

    def action(self) -> ActionResult:
        check_csrf_token()

        if transactions.check_transaction():
            value = self._vs_key().from_html_vars("key")
            # Remove the secret key from known URL vars. Otherwise later constructed URLs
            # which use the current page context will contain the passphrase which could
            # leak the secret information
            request.del_var("key_p_passphrase")
            self._vs_key().validate_value(value, "key")
            self._create_key(value["alias"], PasswordType(value["passphrase"]))
            # FIXME: This leads to a circular import otherwise. This module (cmk.gui.key_mgmt) is
            #  clearly outside of either cmk.gui.plugins.wato and cmk.gui.cee.plugins.wato so this
            #  is obviously a very simple module-layer violation. This whole module should either
            #    * be moved into cmk.gui.cee.plugins.wato
            #    * or cmk.gui.cee.plugins.wato.module_registry should be moved up
            #  Either way, this is outside my scope right now and shall be fixed.
            from cmk.gui.plugins.wato.utils.base_modes import mode_url

            return HTTPRedirect(mode_url(self.back_mode))
        return None

    def _create_key(self, alias: str, passphrase: PasswordType) -> None:
        keys = self.key_store.load()

        new_id = 1
        for key_id in keys:
            new_id = max(new_id, key_id + 1)

        assert user.id is not None
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
                        password_meter=True,
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
        check_csrf_token()

        if transactions.check_transaction():
            value = self._vs_key().from_html_vars("key")
            request.del_var("key_p_passphrase")
            self._vs_key().validate_value(value, "key")

            key_file = self._get_uploaded(value["key_file"])
            if not key_file:
                raise MKUserError(None, _("You need to provide a key file."))

            try:
                self._upload_key(key_file, value["alias"], PasswordType(value["passphrase"]))
            except InvalidPEMError:
                raise MKUserError(None, _("The file does not look like a valid key file."))

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
        cert_spec: (tuple[Literal["upload"], tuple[str, str, bytes]] | tuple[Literal["text"], str]),
    ) -> str:
        if cert_spec[0] == "upload":
            return cert_spec[1][2].decode("ascii")
        return cert_spec[1]

    def _upload_key(self, key_file: str, alias: str, passphrase: PasswordType) -> None:
        # This will raise various ValueErrors, if the cert is not valid, if the passphrase is wrong, etc.
        try:
            key_pair = CertificateWithPrivateKey.load_combined_file_content(key_file, passphrase)
        except WrongPasswordError:
            raise MKUserError("key_p_passphrase", "Invalid pass phrase")

        key = Key(
            certificate=key_pair.certificate.dump_pem().str,
            private_key=key_pair.private_key.dump_pem(passphrase).str,
            alias=alias,
            owner=user.ident,
            date=key_pair.certificate.not_valid_before.timestamp(),
            not_downloaded=False,
        )
        self.key_store.add(key)

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
                        password_meter=True,
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
        check_csrf_token()

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

            value = self._vs_key().from_html_vars("key")
            self._vs_key().validate_value(value, "key")

            try:
                keys[key_id].to_certificate_with_private_key(PasswordType(value["passphrase"]))
            except (WrongPasswordError, ValueError):
                raise MKUserError("key_p_passphrase", _("Invalid pass phrase"))

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


def generate_key(alias: str, passphrase: PasswordType, user_id: UserId, site_id: SiteId) -> Key:
    key_pair = CertificateWithPrivateKey.generate_self_signed(
        common_name=alias,
        organizational_unit_name=user_id,
        expiry=relativedelta(years=10),
    )
    return Key(
        certificate=key_pair.certificate.dump_pem().str,
        private_key=key_pair.private_key.dump_pem(password=passphrase).str,
        alias=alias,
        owner=user_id,
        date=time.time(),
        not_downloaded=True,
    )
