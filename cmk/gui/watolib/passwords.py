#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.ccc.user import UserId

from cmk.utils.password_store import Password

from cmk.gui import userdb
from cmk.gui.logged_in import user
from cmk.gui.watolib.changes import add_change
from cmk.gui.watolib.config_domains import ConfigDomainCore
from cmk.gui.watolib.groups_io import load_contact_group_information
from cmk.gui.watolib.password_store import PasswordStore


def contact_group_choices(only_own: bool = False) -> list[tuple[str, str]]:
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


def sorted_contact_group_choices(only_own: bool = False) -> list[tuple[str, str]]:
    return sorted(contact_group_choices(only_own), key=lambda x: x[1])


def save_password(
    ident: str,
    details: Password,
    *,
    new_password: bool,
    user_id: UserId | None,
    pprint_value: bool,
    use_git: bool,
) -> None:
    password_store = PasswordStore()
    entries = password_store.load_for_modification()
    entries[ident] = details
    password_store.save(entries, pprint_value)
    if new_password:
        add_change(
            action_name="add-password",
            text=f"Added the password {ident}",
            user_id=user_id,
            domains=[ConfigDomainCore()],
            sites=None,
            use_git=use_git,
        )
    else:
        add_change(
            action_name="edit-password",
            text=f"Edited the password '{ident}'",
            user_id=user_id,
            domains=[ConfigDomainCore()],
            sites=None,
            use_git=use_git,
        )


def remove_password(
    ident: str,
    *,
    user_id: UserId | None,
    pprint_value: bool,
    use_git: bool,
) -> None:
    password_store = PasswordStore()
    entries = load_passwords_to_modify()
    _ = entries.pop(ident)
    password_store.save(entries, pprint_value)
    add_change(
        action_name="delete-password",
        text=f"Removed the password '{ident}'",
        user_id=user_id,
        domains=[ConfigDomainCore()],
        sites=None,
        use_git=use_git,
    )


def password_exists(ident: str) -> bool:
    return ident in load_passwords()


def load_passwords() -> dict[str, Password]:
    password_store = PasswordStore()
    return password_store.filter_usable_entries(password_store.load_for_reading())


def load_password(password_id: str) -> Password:
    return load_passwords()[password_id]


def load_passwords_to_modify() -> dict[str, Password]:
    password_store = PasswordStore()
    return password_store.filter_editable_entries(password_store.load_for_modification())


def load_password_to_modify(ident: str) -> Password:
    passwords = load_passwords_to_modify()
    return passwords[ident]
