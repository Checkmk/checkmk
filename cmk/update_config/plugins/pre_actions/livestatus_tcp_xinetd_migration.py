#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger
from pathlib import Path
from typing import override

from cmk.ccc.site import omd_site
from cmk.gui.exceptions import MKUserError
from cmk.update_config.lib import ExpiryVersion
from cmk.update_config.plugins.lib.livestatus_tcp_xinetd_migration import (
    xinetd_has_local_modifications,
)
from cmk.update_config.plugins.pre_actions.utils import (
    ConflictMode,
    continue_per_users_choice,
)
from cmk.update_config.registry import pre_update_action_registry, PreUpdateAction
from cmk.utils.paths import omd_root


class LivestatusXinetdMigrationWarning(PreUpdateAction):
    @staticmethod
    def _continue_on_exception(conflict_mode: ConflictMode) -> bool:
        match conflict_mode:
            case ConflictMode.FORCE:
                return True
            case ConflictMode.ABORT:
                return False
            case ConflictMode.ASK:
                return continue_per_users_choice(
                    "You can abort the update process (A) and try to fix "
                    "the incompatibilities or try to continue the update (c).\n"
                    "Abort update? [A/c]\n"
                ).is_not_abort()

    @override
    def __call__(
        self,
        logger: Logger,
        conflict_mode: ConflictMode,
        site_root: Path | None = None,
        site_id: str | None = None,
    ) -> None:
        if site_root is None:
            site_root = Path(omd_root)
        if site_id is None:
            site_id = omd_site()

        if xinetd_has_local_modifications(site_root, site_id):
            logger.warning(
                "This update changes how the livestatus xinetd config is "
                "deployed. If you made local modifications to this file, "
                "your changes will be discarded. You should migrate those "
                "changes using 'omd config' before continuing. "
                "If you have not made changes outside of omd config, "
                "you can safely ignore this message."
            )
            if not self._continue_on_exception(conflict_mode):
                raise MKUserError(None, "Failed to migrate livestatus xinetd.conf")


action = LivestatusXinetdMigrationWarning(
    name="livestatus_xinetd_migration",
    title="Migrate livestatus xinetd configuration",
    sort_index=1,
    expiry_version=ExpiryVersion.CMK_310,
)
pre_update_action_registry.register(action)
