#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path
from typing import Optional, TypedDict

import cmk.gui.userdb as userdb
from cmk.gui.globals import user
from cmk.gui.watolib.simple_config_file import WatoSimpleConfigFile
from cmk.gui.watolib.utils import wato_root_dir

Password = TypedDict(
    "Password",
    {
        "title": str,
        "comment": str,
        "docu_url": str,
        "password": str,
        # Only owners can edit the password
        # None -> Administrators (having the permission "Write access to all passwords")
        # str -> Name of the contact group owning the password
        "owned_by": Optional[str],
        "shared_with": list[str],
    },
)


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
        user_groups = userdb.contactgroups_of_user(user.id)

        passwords = self.filter_editable_entries(entries)
        # TODO: This bug was uncovered by the new type hints. Will fix the issue in the next commit
        passwords.update({k: v for k, v in entries.items() if v["shared_with"] in user_groups})  # type: ignore[comparison-overlap]
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
