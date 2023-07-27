#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from cmk.utils.prediction import PredictionData, PredictionInfo, PredictionParameters, Timegroup

from cmk.update_config.plugins.actions.prediction_files_cleanup import RemoveUnreadablePredictions


def test_ok_files_are_kept(tmp_path: Path) -> None:
    info_file = tmp_path / "my_test_prediction.info"
    data_file = tmp_path / "my_test_prediction"

    info_file.write_text(
        PredictionInfo(
            name=Timegroup("everyhour"),
            time=123456789,
            range=(23, 42),
            cf="MAX",
            dsname="kuchen_count",
            slice=3600,
            params=PredictionParameters(horizon=3, period="wday"),
        ).json(),
    )
    data_file.write_text(
        PredictionData(
            columns=["average", "max", "min"],
            points=[[1.0, 2.0, 3.0], [4.0, None, 6.0]],
            data_twindow=[1, 10],
            step=2,
        ).json(),
    )

    RemoveUnreadablePredictions.cleanup_unreadable_files(tmp_path)

    assert info_file.exists()
    assert data_file.exists()


def test_corrupt_files_are_removed(tmp_path: Path) -> None:
    info_file = tmp_path / "my_test_prediction.info"
    data_file = tmp_path / "my_test_prediction"

    info_file.write_text("boo")
    data_file.write_text(
        PredictionData(
            columns=["average", "max", "min"],
            points=[[1.0, 2.0, 3.0], [4.0, None, 6.0]],
            data_twindow=[1, 10],
            step=2,
        ).json(),
    )

    RemoveUnreadablePredictions.cleanup_unreadable_files(tmp_path)

    assert not info_file.exists()
    assert not data_file.exists()
