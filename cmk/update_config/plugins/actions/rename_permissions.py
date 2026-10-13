#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Follow permission renames in the explicit per-permission settings stored in roles.mk."""

from collections.abc import Mapping
from logging import Logger
from typing import Final, override

from cmk.gui.config import active_config
from cmk.gui.role_types import UserRoleBase
from cmk.gui.userdb import UserRolesConfigFile
from cmk.update_config.lib import ExpiryVersion
from cmk.update_config.registry import update_action_registry, UpdateAction
from cmk.utils.log import VERBOSE

_RENAMED_PERMISSIONS: Final[Mapping[str, str]] = {
    "general.query_metric_backend_from_custom_graph_editor": (
        "general.query_telemetry_metrics_from_custom_graph_editor"
    ),
}


class RenamePermissions(UpdateAction):
    @override
    def __call__(self, logger: Logger) -> None:
        config_file = UserRolesConfigFile()
        roles = config_file.load_for_modification()
        if rename_permissions(roles, logger):
            config_file.save(roles, pprint_value=active_config.wato_pprint_config)


def rename_permissions(roles: Mapping[str, UserRoleBase], logger: Logger) -> bool:
    changed = False
    for role_id, role in roles.items():
        permissions = role["permissions"]
        for old_name, new_name in _RENAMED_PERMISSIONS.items():
            if old_name not in permissions:
                continue
            permissions[new_name] = permissions.pop(old_name)
            changed = True
            logger.log(
                VERBOSE,
                "Renamed permission %(old)s to %(new)s in role %(role)s",
                {"old": old_name, "new": new_name, "role": role_id},
            )
    return changed


update_action_registry.register(
    RenamePermissions(
        name="rename_permissions",
        title=(
            "Rename the custom graph editor query permission "
            "from metric backend to telemetry metrics"
        ),
        sort_index=100,
        expiry_version=ExpiryVersion.CMK_310,
    )
)
