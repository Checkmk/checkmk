#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger
from pathlib import Path
from typing import override

import cmk.utils.paths
from cmk.agent_based.prediction_backend import PredictionInfo
from cmk.update_config.lib import ExpiryVersion
from cmk.update_config.registry import update_action_registry, UpdateAction
from cmk.utils.prediction import iter_prediction_files, PredictionData
from cmk.utils.prediction import Paths as PredictionPaths


class RemoveUnreadablePredictions(UpdateAction):
    """
    Remove prediction files that are unreadable.

    Prediciton files may have to be re-computed anyway (because parameters
    have been changed or because they're outdated).
    Deleting the unreadable ones allows us to change the format between releases.
    """

    @override
    def __call__(self, logger: Logger) -> None:
        self.cleanup_unreadable_files(PredictionPaths(cmk.utils.paths.omd_root).predictions_dir)

    @staticmethod
    def cleanup_unreadable_files(path: Path) -> None:
        for files in iter_prediction_files(path):
            try:
                _ = PredictionInfo.model_validate_json(files.info.read_text())
                _ = PredictionData.model_validate_json(files.data.read_text())
            except ValueError, FileNotFoundError:
                files.unlink()


update_action_registry.register(
    RemoveUnreadablePredictions(
        name="remove_unreadable_predictions",
        title="Remove unreadable prediction files",
        sort_index=101,  # can run whenever
        expiry_version=ExpiryVersion.NEVER,
    )
)
