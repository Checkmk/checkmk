#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger
from pathlib import Path
from typing import override

import cmk.utils.paths
from cmk.utils.prediction import PredictionData, PredictionStore

from cmk.agent_based.prediction_backend import PredictionInfo
from cmk.update_config.registry import update_action_registry, UpdateAction


class RemoveUnreadablePredictions(UpdateAction):
    """
    Remove prediction files that are unreadable.

    Prediciton files may have to be re-computed anyway (because parameters
    have been changed or because they're outdated).
    Deleting the unreadable ones allows us to change the format between releases.
    """

    @override
    def __call__(self, logger: Logger) -> None:
        self.cleanup_unreadable_files(cmk.utils.paths.predictions_dir)

    @staticmethod
    def cleanup_unreadable_files(path: Path) -> None:
        for info_file in path.rglob(f"*{PredictionStore.INFO_FILE_SUFFIX}"):
            # It may happen that e.g. hostnames have a ".info" suffix, too. This leads to
            # directories match the pattern. We have to skip those.
            if info_file.is_dir():
                continue
            data_file = info_file.with_suffix(PredictionStore.DATA_FILE_SUFFIX)
            try:
                _ = PredictionInfo.model_validate_json(info_file.read_text())
                _ = PredictionData.model_validate_json(data_file.read_text())
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
