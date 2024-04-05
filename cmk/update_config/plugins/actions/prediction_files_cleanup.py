#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger
from pathlib import Path

import cmk.utils.paths
from cmk.utils.prediction import PredictionData

from cmk.agent_based.prediction_backend import PredictionInfo
from cmk.update_config.registry import update_action_registry, UpdateAction
from cmk.update_config.update_state import UpdateActionState


class RemoveUnreadablePredictions(UpdateAction):
    """
    Remove prediction files that are unreadable.

    Prediciton files may have to be re-computed anyway (because parameters
    have been changed or because they're outdated).
    Deleting the unreadable ones allows us to change the format between releases.
    """

    def __call__(self, logger: Logger, update_action_state: UpdateActionState) -> None:
        self.cleanup_unreadable_files(Path(cmk.utils.paths.var_dir, "prediction"))

    @staticmethod
    def cleanup_unreadable_files(path: Path) -> None:
        for info_file in path.rglob("*.info"):
            data_file = info_file.with_suffix("")
            try:
                _ = PredictionInfo.parse_raw(info_file.read_text())
                _ = PredictionData.parse_raw(data_file.read_text())
            except (ValueError, FileNotFoundError):
                info_file.unlink(missing_ok=True)
                data_file.unlink(missing_ok=True)


update_action_registry.register(
    RemoveUnreadablePredictions(
        name="remove_unreadable_predictions",
        title="Remove unreadable prediction files",
        sort_index=101,  # can run whenever
    )
)
