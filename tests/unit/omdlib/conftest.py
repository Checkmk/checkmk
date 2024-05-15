#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest
from pytest import MonkeyPatch

import omdlib


@pytest.fixture(autouse=True)
def omd_base_path(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(omdlib.utils, "omd_base_path", lambda: str(tmp_path))
