#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger

from cmk.utils import version

from cmk.update_config.registry import update_action_registry, UpdateAction

if version.edition() is version.Edition.CME:
    from cmk.gui.cme.managed_snapshots import save_active_config
else:
    from cmk.gui.mkeventd.helpers import save_active_config


class UpdateECRules(UpdateAction):  # pylint: disable=too-few-public-methods
    def __call__(self, logger: Logger) -> None:
        save_active_config()


update_action_registry.register(
    UpdateECRules(
        name="update_ec_rules",
        title="Event Console: Rewrite active config",
        sort_index=130,
    )
)
