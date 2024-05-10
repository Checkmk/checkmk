#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path
from typing import Any

from cmk.utils import store
from cmk.utils.config_validation_layer.user_roles import validate_userroles

from cmk.gui import hooks
from cmk.gui.config import active_config, builtin_role_ids
from cmk.gui.i18n import _
from cmk.gui.watolib.simple_config_file import ConfigFileRegistry, WatoSingleConfigFile
from cmk.gui.watolib.utils import multisite_dir

RoleSpec = dict[str, Any]  # TODO: Improve this type
Roles = dict[str, RoleSpec]  # TODO: Improve this type


def _get_builtin_roles() -> Roles:
    """Returns a role dictionary containing the bultin default roles"""
    builtin_role_names = {
        "admin": _("Administrator"),
        "user": _("Normal monitoring user"),
        "guest": _("Guest user"),
        "agent_registration": _("Agent registration user"),
    }
    return {
        rid: {
            "alias": builtin_role_names.get(rid, rid),
            "permissions": {},  # use default everywhere
            "builtin": True,
        }
        for rid in builtin_role_ids
    }


class UserRolesConfigFile(WatoSingleConfigFile[Roles]):
    """Handles loading & saving the user roles from/to roles.mk"""

    def __init__(self) -> None:
        super().__init__(
            config_file_path=Path(multisite_dir()) / "roles.mk",
            config_variable="roles",
        )

    def _load_file(self, lock: bool = False) -> Roles:
        cfg = store.load_from_mk_file(
            self._config_file_path,
            key=self._config_variable,
            default=_get_builtin_roles(),
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

        validate_userroles(cfg)
        return cfg

    def save(self, cfg: Roles) -> None:
        validate_userroles(cfg)
        active_config.roles.update(cfg)
        hooks.call("roles-saved", cfg)
        super().save(cfg)


def load_roles() -> Roles:
    roles = UserRolesConfigFile().load_for_modification()
    # Reflect the data in the roles dict kept in the config module needed
    # for instant changes in current page while saving modified roles.
    # Otherwise the hooks would work with old data when using helper
    # functions from the config module
    # TODO: load_roles() should not update global structures
    active_config.roles.update(roles)
    return roles


def register_userroles_config_file(config_file_registry: ConfigFileRegistry) -> None:
    config_file_registry.register(UserRolesConfigFile())
