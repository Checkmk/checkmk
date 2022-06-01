#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from contextlib import contextmanager
from typing import Mapping

from pytest_mock import MockerFixture

from cmk.gui.exceptions import MKUserError
from cmk.gui.type_defs import UserRole
from cmk.gui.watolib import userroles
from cmk.gui.watolib.userroles import RoleID


@contextmanager
def should_raise_a_mkusererror():
    try:
        yield
    except MKUserError:
        pass
    else:
        raise AssertionError("An MKUserError should have been raised and it wasn't!")


def test_cant_delete_default_user_roles(mocker: MockerFixture):
    default_roles: Mapping[RoleID, UserRole] = userroles.get_all_roles()
    mocker.patch("cmk.gui.globals.transactions.transaction_valid", return_value=True)

    for roleid in default_roles.keys():
        with should_raise_a_mkusererror():
            userroles.delete_role(roleid)


def test_deleting_cloned_user_roles():
    userroles.clone_role(RoleID("admin"))

    all_roles: Mapping[RoleID, UserRole] = userroles.get_all_roles()
    assert len(all_roles) == 4
    userroles.delete_role(RoleID("adminx"))
    roles_after_deletion: Mapping[RoleID, UserRole] = userroles.get_all_roles()
    assert len(roles_after_deletion) == 3


def test_cloning_user_roles():
    default_roles: Mapping[RoleID, UserRole] = userroles.get_all_roles()

    for roleid in default_roles.keys():
        userroles.clone_role(roleid)

    all_roles: Mapping[RoleID, UserRole] = userroles.get_all_roles()
    assert len(all_roles) == 6
    assert {roleid for roleid in all_roles.keys() if roleid.endswith("x")} == {
        "adminx",
        "guestx",
        "userx",
    }


def test_get_default_user_roles():
    default_roles: Mapping[RoleID, UserRole] = userroles.get_all_roles()
    assert {role.name for role in default_roles.values()} == {"admin", "guest", "user"}


def test_get_non_existent_user_roles():
    with should_raise_a_mkusererror():
        userroles.get_role(RoleID("roleid_that_doesnt_exist"))
    assert userroles.role_exists(RoleID("roleid_that_doesnt_exist")) is False
