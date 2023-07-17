#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import os
from logging import Logger

import cmk.utils.store as store
from cmk.utils.paths import var_dir

from cmk.update_config.registry import update_action_registry, UpdateAction
from cmk.update_config.update_state import UpdateActionState


class ConvertPersistedSections(UpdateAction):
    def __call__(self, logger: Logger, update_action_state: UpdateActionState) -> None:
        if "converted_to_pickle" in update_action_state:
            return
        for subdir in ("persisted", "persisted_sections"):
            for dirpath, _dirnames, filenames in os.walk(os.path.join(var_dir, subdir)):
                for filename in filenames:
                    try:
                        self._convert_file(os.path.join(dirpath, filename))
                    except UnicodeDecodeError as e:
                        # might be an already converted pickle file
                        # in case cmk-update-config was aborted "somehow"
                        logger.warning(
                            f"Skipping conversion of {os.path.join(dirpath, filename)}: {e}"
                        )
                        continue
        update_action_state["converted_to_pickle"] = "True"

    def _convert_file(self, filename: str) -> None:
        """Converts a persisted ast file into a pickled one, only if it contains valid data"""
        data = store.load_object_from_file(filename, default=None)
        if data is None:
            return

        store.save_object_to_pickle_file(filename, data)


update_action_registry.register(
    ConvertPersistedSections(
        name="persisted_sections",
        title="Convert persisted sections",
        sort_index=41,
    )
)
