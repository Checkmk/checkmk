#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Dict, Union, Optional, List

import cmk.gui.config as config
import cmk.gui.userdb as userdb

from cmk.gui.watolib.password_store import PasswordStore
from cmk.gui.watolib.groups import load_contact_group_information

PASSWORD = Dict[str, Union[Optional[str], List[str]]]


def contact_group_choices(only_own=False):
    contact_groups = load_contact_group_information()

    if only_own:
        assert config.user.id is not None
        user_groups = userdb.contactgroups_of_user(config.user.id)
    else:
        user_groups = []

    entries = [
        (c, g['alias']) for c, g in contact_groups.items() if not only_own or c in user_groups
    ]
    return entries


def sorted_contact_group_choices(only_own=False):
    return sorted(contact_group_choices(only_own), key=lambda x: x[1])


def save_password(ident: str, details: PASSWORD):
    password_store = PasswordStore()
    entries = password_store.load_for_modification()
    entries[ident] = details
    password_store.save(entries)


def password_exists(ident: str) -> bool:
    return ident in load_passwords()


def load_passwords() -> Dict[str, PASSWORD]:
    password_store = PasswordStore()
    return password_store.load_for_reading()


def load_passwords_to_modify() -> Dict[str, PASSWORD]:
    password_store = PasswordStore()
    return password_store.load_for_modification()


def load_password_to_modify(ident: str) -> PASSWORD:
    passwords = load_passwords_to_modify()
    return passwords[ident]
