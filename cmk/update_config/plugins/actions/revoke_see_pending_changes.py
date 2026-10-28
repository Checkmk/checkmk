#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Keep roles that may not activate changes from seeing them through the new permission.

wato.see_pending_changes defaults to the same roles as wato.activate. Without this action, a role
whose admin revoked wato.activate would inherit the new permission from its base role and start
seeing the pending changes.
"""

import os
from collections.abc import Mapping
from logging import Logger
from typing import Final, override

from cmk.ccc.version import Version
from cmk.gui.config import active_config
from cmk.gui.role_types import UserRoleBase
from cmk.gui.userdb import UserRolesConfigFile
from cmk.update_config.lib import ExpiryVersion
from cmk.update_config.registry import update_action_registry, UpdateAction
from cmk.utils.log import VERBOSE

_SEE_PENDING_CHANGES: Final = "wato.see_pending_changes"

# The 2.5.0 patch that brings the permission. Rerunning after it would override admins' choices.
_FIRST_VERSION_WITH_THE_PERMISSION: Final = Version.from_str("2.5.0p20")


class RevokeSeePendingChanges(UpdateAction):
    @override
    def __call__(self, logger: Logger) -> None:
        if not is_update_from_before_the_permission(os.environ.get("OMD_FROM_VERSION"), logger):
            return
        config_file = UserRolesConfigFile()
        roles = config_file.load_for_modification()
        if revoke_see_pending_changes(roles, logger):
            config_file.save(roles, pprint_value=active_config.wato_pprint_config)


def is_update_from_before_the_permission(from_version: str | None, logger: Logger) -> bool:
    """Whether omd update comes from a version without wato.see_pending_changes.

    ``from_version`` is ``OMD_FROM_VERSION``; unset or unparsable means no such update.
    """
    if from_version is None:
        return False
    try:
        # OMD_FROM_VERSION carries the edition suffix, e.g. "2.5.0p17.ultimate"
        version = Version.from_str(from_version.rsplit(".", 1)[0])
    except ValueError:
        logger.warning(
            'Cannot parse OMD_FROM_VERSION "%(version)s", assuming it has the permission',
            {"version": from_version},
        )
        return False
    return version < _FIRST_VERSION_WITH_THE_PERMISSION


def revoke_see_pending_changes(roles: Mapping[str, UserRoleBase], logger: Logger) -> bool:
    changed = False
    for role_id, role in roles.items():
        permissions = role["permissions"]
        # An unset wato.activate takes the base role's default, which the new permission shares.
        if permissions.get("wato.activate") is not False or _SEE_PENDING_CHANGES in permissions:
            continue
        permissions[_SEE_PENDING_CHANGES] = False
        changed = True
        logger.log(
            VERBOSE,
            "Revoked permission %(permission)s in role %(role)s, which may not activate changes",
            {"permission": _SEE_PENDING_CHANGES, "role": role_id},
        )
    return changed


update_action_registry.register(
    RevokeSeePendingChanges(
        name="revoke_see_pending_changes",
        title="Revoke 'See pending changes' from roles that may not activate changes",
        sort_index=100,
        expiry_version=ExpiryVersion.CMK_260,
    )
)
