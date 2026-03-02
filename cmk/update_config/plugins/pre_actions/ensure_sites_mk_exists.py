#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from logging import Logger

from cmk.gui.exceptions import MKUserError
from cmk.gui.watolib.sites import SitesConfigFile
from cmk.update_config.lib import ExpiryVersion
from cmk.update_config.plugins.pre_actions.utils import ConflictMode, continue_per_users_choice
from cmk.update_config.registry import pre_update_action_registry, PreUpdateAction


def _sites_mk_exists() -> bool:
    return SitesConfigFile()._config_file_path.exists()


def _continue_per_users_choice(conflict_mode: ConflictMode, msg: str) -> bool:
    match conflict_mode:
        case ConflictMode.FORCE:
            return True
        case ConflictMode.ABORT:
            return False
        case ConflictMode.ASK:
            return continue_per_users_choice(msg).is_not_abort()


class EnsureSitesMkExist(PreUpdateAction):
    def __call__(self, logger: Logger, conflict_mode: ConflictMode) -> None:
        if _sites_mk_exists():
            return

        if not _continue_per_users_choice(
            conflict_mode,
            "Outdated 2.4 configuration detected. Please abort this process and run "
            "`cmk-update-config` on your Checkmk 2.4 installation before continuing. \n"
            "If you continue without doing so, some existing rules may be flagged as "
            "incompatible during the upgrade [A/c]. \n",
        ):
            raise MKUserError(
                None,
                "Update aborted. Please manually run `cmk-update-config` on your existing site before upgrading.",
            )


pre_update_action_registry.register(
    EnsureSitesMkExist(
        name="ensure_sites_mk_exists",
        title="Ensure sites.mk file exists",
        sort_index=5,
        expiry_version=ExpiryVersion.CMK_260,
    )
)
