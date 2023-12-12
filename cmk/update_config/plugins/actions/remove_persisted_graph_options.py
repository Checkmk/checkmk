#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from itertools import chain
from logging import Logger

from cmk.utils.paths import profile_dir

from cmk.update_config.registry import update_action_registry, UpdateAction
from cmk.update_config.update_state import UpdateActionState


class RemovePersistedGraphOptions(UpdateAction):
    _KEY = "persisted_graph_options_removed"

    def __call__(self, logger: Logger, update_action_state: UpdateActionState) -> None:
        if update_action_state.get(self._KEY):
            return

        for path in chain(
            profile_dir.glob("*/graph_range.mk"),
            profile_dir.glob("*/graph_size.mk"),
        ):
            path.unlink()

        update_action_state[self._KEY] = "True"


update_action_registry.register(
    RemovePersistedGraphOptions(
        name="remove_persisted_graph_options",
        title="Remove persisted graph options",
        sort_index=150,
    )
)
