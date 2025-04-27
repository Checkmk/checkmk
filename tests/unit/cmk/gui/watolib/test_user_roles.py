#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from contextlib import contextmanager

from pytest import MonkeyPatch

import cmk.ccc.version as cmk_version

from cmk.utils import paths

import cmk.gui.utils.transaction_manager
from cmk.gui.exceptions import MKUserError
from cmk.gui.userdb import UserRole
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


def test_cant_delete_default_user_roles(monkeypatch: MonkeyPatch, request_context: None) -> None:
    default_roles: Mapping[RoleID, UserRole] = userroles.get_all_roles()
    with monkeypatch.context() as m:
        m.setattr(
            cmk.gui.utils.transaction_manager.transactions,
            "transaction_valid",
            lambda: True,
        )
        for roleid in default_roles.keys():
            with should_raise_a_mkusererror():
                userroles.delete_role(roleid, pprint_value=False)


def test_deleting_cloned_user_roles(request_context: None) -> None:
    userroles.clone_role(RoleID("admin"), pprint_value=False)

    all_roles: Mapping[RoleID, UserRole] = userroles.get_all_roles()
    assert (
        len(all_roles) == 5 if cmk_version.edition(paths.omd_root) is cmk_version.Edition.CCE else 4
    )
    userroles.delete_role(RoleID("adminx"), pprint_value=False)
    roles_after_deletion: Mapping[RoleID, UserRole] = userroles.get_all_roles()
    assert (
        len(roles_after_deletion) == 4
        if cmk_version.edition(paths.omd_root) is cmk_version.Edition.CCE
        else 3
    )


def test_cloning_user_roles(request_context: None) -> None:
    default_roles: Mapping[RoleID, UserRole] = userroles.get_all_roles()

    for roleid in default_roles.keys():
        userroles.clone_role(roleid, pprint_value=False)

    all_roles: Mapping[RoleID, UserRole] = userroles.get_all_roles()
    assert (
        len(all_roles) == 8 if cmk_version.edition(paths.omd_root) is cmk_version.Edition.CCE else 6
    )
    assert {roleid for roleid in all_roles.keys() if roleid.endswith("x")} == {
        "adminx",
        "guestx",
        "userx",
        "agent_registrationx",
        "no_permissionsx",
    }


def test_get_default_user_roles(request_context: None) -> None:
    default_roles: Mapping[RoleID, UserRole] = userroles.get_all_roles()
    assert {role.name for role in default_roles.values()} == {
        "admin",
        "guest",
        "user",
        "agent_registration",
        "no_permissions",
    }


def test_get_non_existent_user_roles(request_context: None) -> None:
    with should_raise_a_mkusererror():
        userroles.get_role(RoleID("roleid_that_doesnt_exist"))
    assert userroles.role_exists(RoleID("roleid_that_doesnt_exist")) is False
