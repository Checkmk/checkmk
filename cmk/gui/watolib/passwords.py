#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from typing import Literal

from cmk.gui import userdb
from cmk.gui.exceptions import MKUserError
from cmk.gui.i18n import _
from cmk.gui.logged_in import LoggedInUser, user
from cmk.utils.password_store import PasswordConfig

from .config_domain_name import (
    ConfigDomainName,
    CORE,
    PasswordChange,
    SerializedSettings,
)
from .groups_io import load_contact_group_information
from .password_store import PasswordStore
from .pending_changes import Change, ChangeScope, PendingChanges


class PasswordChangeEffectRegistry:
    def __init__(self) -> None:
        self.affected_domains_add: Sequence[ConfigDomainName] = []
        self.affected_domains_edit: Sequence[ConfigDomainName] = []
        self.affected_domains_delete: Sequence[ConfigDomainName] = []

    def register(
        self,
        affected_domains_add: Sequence[ConfigDomainName],
        affected_domains_edit: Sequence[ConfigDomainName],
        affected_domains_delete: Sequence[ConfigDomainName],
    ) -> None:
        self.affected_domains_add = affected_domains_add
        self.affected_domains_edit = affected_domains_edit
        self.affected_domains_delete = affected_domains_delete


password_change_effect_registry = PasswordChangeEffectRegistry()


def register_password_change_effect() -> None:
    password_change_effect_registry.register(
        affected_domains_add=[CORE],
        affected_domains_edit=[CORE],
        affected_domains_delete=[CORE],
    )


def contact_group_choices(only_own: bool = False) -> list[tuple[str, str]]:
    contact_groups = load_contact_group_information()

    if only_own:
        assert user.id is not None
        user_groups = userdb.contactgroups_of_user(user.id)
    else:
        user_groups = []

    return [(c, g["alias"]) for c, g in contact_groups.items() if not only_own or c in user_groups]


def sorted_contact_group_choices(only_own: bool = False) -> list[tuple[str, str]]:
    return sorted(contact_group_choices(only_own), key=lambda x: x[1])


def _domain_settings(
    domains: Sequence[ConfigDomainName],
    *,
    change_type: Literal["ADD", "EDIT", "DELETE"],
    password_id: str,
) -> dict[ConfigDomainName, SerializedSettings]:
    return {
        domain: SerializedSettings(
            changed_passwords=[PasswordChange(change_type=change_type, password_id=password_id)]
        )
        for domain in domains
    }


def save_password(
    ident: str,
    config: PasswordConfig,
    *,
    new_password: bool,
    pprint_value: bool,
    pending_changes: PendingChanges,
) -> None:
    password_store = PasswordStore()
    entries = password_store.load_for_modification()
    entries[ident] = config
    password_store.save(entries, pprint_value)
    if new_password:
        domains = password_change_effect_registry.affected_domains_add
        pending_changes.add(
            Change(
                action_name="add-password",
                text=f"Added the password {ident}",
                domains=domains,
                domain_settings=_domain_settings(domains, change_type="ADD", password_id=ident),
            ),
            ChangeScope.all_activation_sites(),
        )
    else:
        domains = password_change_effect_registry.affected_domains_edit
        pending_changes.add(
            Change(
                action_name="edit-password",
                text=f"Edited the password '{ident}'",
                domains=domains,
                domain_settings=_domain_settings(domains, change_type="EDIT", password_id=ident),
            ),
            ChangeScope.all_activation_sites(),
        )


def remove_password(
    ident: str,
    *,
    acting_user: LoggedInUser,
    pprint_value: bool,
    pending_changes: PendingChanges,
) -> None:
    password_store = PasswordStore()
    entries = password_store.load_for_modification()
    editable_entries = password_store.filter_editable_entries(entries, acting_user)
    if ident not in editable_entries:
        raise MKUserError(
            ident,
            _(
                "The password cannot be deleted because the user does not have the permission to edit it."
            ),
        )

    _e = entries.pop(ident)
    password_store.save(entries, pprint_value)
    domains = password_change_effect_registry.affected_domains_delete
    pending_changes.add(
        Change(
            action_name="delete-password",
            text=f"Removed the password '{ident}'",
            domains=domains,
            domain_settings=_domain_settings(domains, change_type="DELETE", password_id=ident),
        ),
        ChangeScope.all_activation_sites(),
    )


def password_exists(ident: str, acting_user: LoggedInUser) -> bool:
    return ident in load_passwords(acting_user)


def load_passwords(acting_user: LoggedInUser) -> dict[str, PasswordConfig]:
    password_store = PasswordStore()
    return password_store.filter_usable_entries(password_store.load_for_reading(), acting_user)


def load_password(acting_user: LoggedInUser, password_id: str) -> PasswordConfig:
    return load_passwords(acting_user)[password_id]


def load_passwords_to_modify(acting_user: LoggedInUser) -> dict[str, PasswordConfig]:
    password_store = PasswordStore()
    return password_store.filter_editable_entries(
        password_store.load_for_modification(), acting_user
    )


def load_password_to_modify(acting_user: LoggedInUser, ident: str) -> PasswordConfig:
    passwords = load_passwords_to_modify(acting_user)
    return passwords[ident]
