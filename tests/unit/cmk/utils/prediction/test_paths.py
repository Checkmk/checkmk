#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from cmk.ccc.hostaddress import HostName
from cmk.utils.prediction import Paths as PredictionPaths


def test_predictions_dir(tmp_path: Path) -> None:
    assert PredictionPaths(tmp_path).predictions_dir == tmp_path / "var/check_mk/prediction"


def test_service_dir_cleans_the_service_name(tmp_path: Path) -> None:
    assert PredictionPaths(tmp_path).service_dir(HostName("hostname"), "CPU load / 5 min") == (
        tmp_path / "var/check_mk/prediction/hostname/CPU_load___5_min"
    )
