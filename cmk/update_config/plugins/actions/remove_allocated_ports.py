#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger

from cmk.utils.paths import omd_root

from cmk.update_config.registry import update_action_registry, UpdateAction
from cmk.update_config.update_state import UpdateActionState


class RemoveAllocatedPorts(UpdateAction):
    def __call__(self, logger: Logger, update_action_state: UpdateActionState) -> None:
        (omd_root / "etc" / "omd" / "allocated_ports").unlink(missing_ok=True)


update_action_registry.register(
    RemoveAllocatedPorts(
        name="remove_allocated_ports",
        title="Removing deprecated allocated_ports file",
        sort_index=120,
    )
)
