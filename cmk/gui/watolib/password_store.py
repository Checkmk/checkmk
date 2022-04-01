#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path
from typing import Mapping

from cmk.utils import password_store, store
from cmk.utils.password_store import Password

import cmk.gui.userdb as userdb
from cmk.gui.logged_in import user
from cmk.gui.watolib.simple_config_file import WatoSimpleConfigFile
from cmk.gui.watolib.utils import wato_root_dir


class PasswordStore(WatoSimpleConfigFile[Password]):
    def __init__(self) -> None:
        super().__init__(
            config_file_path=Path(wato_root_dir()) / "passwords.mk",
            config_variable="stored_passwords",
        )

    def filter_usable_entries(self, entries: dict[str, Password]) -> dict[str, Password]:
        if user.may("wato.edit_all_passwords"):
            return entries

        assert user.id is not None
        user_groups = set(userdb.contactgroups_of_user(user.id))

        passwords = self.filter_editable_entries(entries)
        passwords.update(
            {k: v for k, v in entries.items() if set(v["shared_with"]).intersection(user_groups)}
        )
        return passwords

    def filter_editable_entries(self, entries: dict[str, Password]) -> dict[str, Password]:
        if user.may("wato.edit_all_passwords"):
            return entries

        assert user.id is not None
        user_groups = userdb.contactgroups_of_user(user.id)
        return {k: v for k, v in entries.items() if v["owned_by"] in user_groups}

    def _load_file(self, lock: bool = False) -> dict[str, Password]:
        """The actual passwords are stored in a separate file for special treatment

        Have a look at `cmk.utils.password_store` for further information"""
        return join_password_specs(
            store.load_from_mk_file(
                self._config_file_path,
                key=self._config_variable,
                default={},
                lock=lock,
            ),
            password_store.load(),
        )

    def save(self, cfg: Mapping[str, Password]) -> None:
        """The actual passwords are stored in a separate file for special treatment

        Have a look at `cmk.utils.password_store` for further information"""
        meta_data, passwords = split_password_specs(cfg)
        super().save(meta_data)
        password_store.save(passwords)


def join_password_specs(
    meta_data: Mapping[str, Password], passwords: Mapping[str, str]
) -> dict[str, Password]:
    """Join passwords with meta data"""
    joined: dict[str, Password] = {}
    for password_id, password_spec in meta_data.items():
        joined[password_id] = password_spec.copy()
        joined[password_id]["password"] = passwords.get(password_id, "")
    return joined


def split_password_specs(
    joined: Mapping[str, Password]
) -> tuple[dict[str, Password], dict[str, str]]:
    """Separate passwords from meta data"""
    meta_data, passwords = {}, {}
    for password_id, joined_password in joined.items():
        meta_data[password_id] = joined_password.copy()
        passwords[password_id] = meta_data[password_id]["password"]
        meta_data[password_id]["password"] = ""
    return meta_data, passwords


def passwordstore_choices() -> list[tuple[str, str]]:
    pw_store = PasswordStore()
    return [
        (ident, pw["title"])
        for ident, pw in pw_store.filter_usable_entries(pw_store.load_for_reading()).items()
    ]
