#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from cmk.utils.password_store import Password

import cmk.gui.userdb as userdb
from cmk.gui.globals import user
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


def passwordstore_choices() -> list[tuple[str, str]]:
    pw_store = PasswordStore()
    return [
        (ident, pw["title"])
        for ident, pw in pw_store.filter_usable_entries(pw_store.load_for_reading()).items()
    ]
