#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger

from cmk.utils.paths import profile_dir

from cmk.update_config.registry import update_action_registry, UpdateAction
from cmk.update_config.update_state import UpdateActionState


class RemovePersistedGraphRanges(UpdateAction):
    def __call__(self, logger: Logger, update_action_state: UpdateActionState) -> None:
        for path in profile_dir.glob("*/graph_range.mk"):
            path.unlink()


update_action_registry.register(
    RemovePersistedGraphRanges(
        name="remove_persisted_graph_ranges",
        title="Remove persisted graph ranges",
        sort_index=150,
    )
)
