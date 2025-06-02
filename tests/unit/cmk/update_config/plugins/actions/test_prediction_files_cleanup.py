#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest

from cmk.utils.prediction import DataStat, PredictionData

from cmk.agent_based.prediction_backend import PredictionInfo, PredictionParameters
from cmk.update_config.plugins.actions.prediction_files_cleanup import RemoveUnreadablePredictions

PREDICTION_INFO = PredictionInfo(
    valid_interval=(23, 42),
    metric="kuchen_count",
    direction="upper",
    params=PredictionParameters(horizon=3, period="wday", levels=("absolute", (1, 2))),
).model_dump_json()


@pytest.mark.parametrize(
    ["info_file_content", "file_expected"],
    [
        pytest.param(
            PREDICTION_INFO,
            True,
            id="Valid files are kept",
        ),
        pytest.param("boo", False, id="Corrupt files are removed"),
    ],
)
def test_cleanup_unreadable_files(
    tmp_path: Path, info_file_content: str, file_expected: bool
) -> None:
    info_file = tmp_path / "my_test_prediction.info"
    data_file = tmp_path / "my_test_prediction"

    info_file.write_text(info_file_content)
    data_file.write_text(
        PredictionData(
            points=[
                DataStat(average=1.0, max_=2.0, min_=3.0, stdev=1.0),
                DataStat(average=1.0, max_=2.0, min_=4.0, stdev=5.0),
            ],
            start=1,
            step=2,
        ).model_dump_json(),
    )

    RemoveUnreadablePredictions.cleanup_unreadable_files(tmp_path)

    assert info_file.exists() is file_expected
    assert data_file.exists() is file_expected
