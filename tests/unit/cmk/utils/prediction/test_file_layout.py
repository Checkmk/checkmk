#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from cmk.utils.prediction import PredictionFiles


def test_unlink_removes_the_data_although_the_info_is_unremovable(tmp_path: Path) -> None:
    (not_a_directory := tmp_path / "not-a-directory").touch()
    (data := tmp_path / "data").touch()

    PredictionFiles(info=not_a_directory / "prediction.info", data=data).unlink()

    assert not data.exists()
