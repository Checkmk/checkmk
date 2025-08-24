#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass, field
from typing import override

from cmk.ccc import store
from cmk.gui import hooks
from cmk.gui.config import builtin_role_ids
from cmk.gui.i18n import _
from cmk.gui.role_types import BuiltInUserRole, BuiltInUserRoleID, CustomUserRole
from cmk.gui.type_defs import RoleName
from cmk.gui.watolib.simple_config_file import ConfigFileRegistry, WatoSingleConfigFile
from cmk.gui.watolib.utils import multisite_dir

RoleSpec = BuiltInUserRole | CustomUserRole
Roles = dict[str, RoleSpec]


def _get_builtin_roles() -> dict[RoleName, BuiltInUserRole]:
    """Returns a role dictionary containing the bultin default roles"""
    builtin_role_names = {
        "admin": _("Administrator"),
        "user": _("Normal monitoring user"),
        "guest": _("Guest user"),
        "agent_registration": _("Agent registration user"),
        "no_permissions": _("Empty template for least privilege roles"),
    }

    return {
        rid: BuiltInUserRole(
            alias=builtin_role_names.get(rid, rid),
            permissions={},
            builtin=True,
        )
        for rid in builtin_role_ids
    }


class UserRolesConfigFile(WatoSingleConfigFile[Roles]):
    """Handles loading & saving the user roles from/to roles.mk"""

    def __init__(self) -> None:
        super().__init__(
            config_file_path=multisite_dir() / "roles.mk",
            config_variable="roles",
            spec_class=dict[RoleName, CustomUserRole | BuiltInUserRole],
        )

    @override
    def _load_file(self, *, lock: bool) -> Roles:
        # NOTE: Typing chaos...
        default: Roles = _get_builtin_roles()  # type: ignore[assignment]
        cfg = store.load_from_mk_file(
            self._config_file_path,
            key=self._config_variable,
            default=default,
            lock=lock,
        )
        # Make sure that "general." is prefixed to the general permissions
        # (due to a code change that converted "use" into "general.use", etc.
        # TODO: Can't we drop this? This seems to be from very early days of the GUI
        for role in cfg.values():
            for pname, pvalue in role["permissions"].items():
                if "." not in pname:
                    del role["permissions"][pname]
                    role["permissions"]["general." + pname] = pvalue

        return cfg

    # TODO: Why is this not implemented by overriding validate()?
    def read_file_and_validate(self) -> None:
        for role in self.load_for_reading().values():
            if not role["builtin"] and role["basedon"] in builtin_role_ids:
                role["basedon"] = role["basedon"]

    @override
    def save(self, cfg: Roles, pprint_value: bool) -> None:
        hooks.call("roles-saved", cfg)
        super().save(cfg, pprint_value)


def load_roles() -> Roles:
    return UserRolesConfigFile().load_for_modification()


def register_userroles_config_file(config_file_registry: ConfigFileRegistry) -> None:
    config_file_registry.register(UserRolesConfigFile())


@dataclass
class UserRole:
    name: str
    alias: str
    builtin: bool = False
    permissions: dict[str, bool] = field(default_factory=dict)
    two_factor: bool = False
    basedon: BuiltInUserRoleID | None = None

    def to_dict(self) -> CustomUserRole | BuiltInUserRole:
        if self.basedon is None:
            return BuiltInUserRole(
                {
                    "alias": self.alias,
                    "permissions": self.permissions,
                    "builtin": True,
                    "two_factor": self.two_factor,
                }
            )

        return CustomUserRole(
            {
                "alias": self.alias,
                "permissions": self.permissions,
                "builtin": False,
                "two_factor": self.two_factor,
                "basedon": self.basedon,
            }
        )
