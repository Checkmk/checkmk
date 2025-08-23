#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import get_args

import pytest
from pytest import MonkeyPatch

from cmk.gui.config import active_config, builtin_role_ids
from cmk.gui.role_types import BuiltInUserRole, BuiltInUserRoleID, CustomUserRole
from cmk.gui.userdb import UserRolesConfigFile


def test_buildin_role_ids_var_is_complete() -> None:
    assert set(get_args(BuiltInUserRoleID)) == set(builtin_role_ids)


@pytest.mark.usefixtures("request_context")
def test_role_file_validation(monkeypatch: MonkeyPatch) -> None:
    with monkeypatch.context() as m:
        m.setattr(active_config, "roles", {})

    raw: dict[str, BuiltInUserRole | CustomUserRole] = {
        "user": BuiltInUserRole(
            {"alias": "Normal monitoring user", "permissions": {}, "builtin": True}
        ),
        "admin": BuiltInUserRole({"alias": "Administrator", "permissions": {}, "builtin": True}),
        "guest": BuiltInUserRole({"alias": "Guest user", "permissions": {}, "builtin": True}),
        "agent_registration": BuiltInUserRole(
            {
                "alias": "Agent registration user",
                "permissions": {},
                "builtin": True,
            }
        ),
        "no_permissions": BuiltInUserRole(
            {"alias": "no_permissions", "permissions": {}, "builtin": True}
        ),
        "customguest": CustomUserRole(
            {
                "builtin": False,
                "basedon": "guest",
                "alias": "customguest",
                "permissions": {
                    "bi.see_all": False,
                    "view.allhosts": True,
                    "view.allservices": False,
                    "view.servicedesc": False,
                },
            }
        ),
    }

    roles_config_file = UserRolesConfigFile()
    roles_config_file.save(raw, pprint_value=False)

    roles_config_file.read_file_and_validate()
