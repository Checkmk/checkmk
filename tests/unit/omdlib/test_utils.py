#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from omdlib.utils import site_exists


def test_site_exists(tmp_path: Path) -> None:
    (tmp_path / "sites/dingeling").mkdir(parents=True)

    assert site_exists(tmp_path / "sites/dingeling")

    assert not site_exists(tmp_path / "sites/dingelang")
