#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Dict, List, Optional, TypedDict

import cmk.gui.userdb as userdb
from cmk.gui.globals import user
from cmk.gui.plugins.wato.utils import ConfigDomainCore
from cmk.gui.watolib.changes import add_change
from cmk.gui.watolib.groups import load_contact_group_information
from cmk.gui.watolib.password_store import PasswordStore

# Password = Dict[str, Union[Optional[str], List[str]]]
Password = TypedDict(
    "Password",
    {
        "title": str,
        "comment": str,
        "docu_url": str,
        "password": str,
        "owned_by": Optional[str],
        "shared_with": List[str],
    },
)


def contact_group_choices(only_own=False):
    contact_groups = load_contact_group_information()

    if only_own:
        assert user.id is not None
        user_groups = userdb.contactgroups_of_user(user.id)
    else:
        user_groups = []

    entries = [
        (c, g["alias"]) for c, g in contact_groups.items() if not only_own or c in user_groups
    ]
    return entries


def sorted_contact_group_choices(only_own=False):
    return sorted(contact_group_choices(only_own), key=lambda x: x[1])


def save_password(ident: str, details: Password, new_password=False):
    password_store = PasswordStore()
    entries = password_store.load_for_modification()
    entries[ident] = details
    password_store.save(entries)
    _add_change(ident, change_type="new" if new_password else "edit")


def remove_password(ident: str):
    password_store = PasswordStore()
    entries = load_passwords_to_modify()
    _ = entries.pop(ident)
    password_store.save(entries)
    _add_change(ident, change_type="delete")


def _add_change(ident, change_type):
    if change_type == "new":  # create password
        add_change(
            "add-password",
            f"Added the password {ident}",
            domains=[ConfigDomainCore],
            sites=None,
        )
    elif change_type == "edit":
        add_change(
            "edit-password",
            f"Edited the password '{ident}'",
            domains=[ConfigDomainCore],
            sites=None,
        )
    else:  # delete
        add_change(
            "delete-password",
            f"Removed the password '{ident}'",
            domains=[ConfigDomainCore],
            sites=None,
        )


def password_exists(ident: str) -> bool:
    return ident in load_passwords()


def load_passwords() -> Dict[str, Password]:
    password_store = PasswordStore()
    return password_store.load_for_reading()


def load_password(password_id: str) -> Password:
    return load_passwords()[password_id]


def load_passwords_to_modify() -> Dict[str, Password]:
    password_store = PasswordStore()
    return password_store.load_for_modification()


def load_password_to_modify(ident: str) -> Password:
    passwords = load_passwords_to_modify()
    return passwords[ident]
