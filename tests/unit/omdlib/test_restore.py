#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
from pathlib import Path

from omdlib.restore import _remove_site_home


def _setup_site_home(tmp_path: Path) -> None:
    tmp_path.joinpath("etc/").mkdir()
    tmp_path.joinpath("etc/jaeger/").mkdir()
    tmp_path.joinpath("etc/jaeger/test").touch()
    tmp_path.joinpath("var/").mkdir()
    tmp_path.joinpath("var/clickhouse-server/").mkdir()
    tmp_path.joinpath("var/clickhouse-server/data").touch()


def test_remove_site_home(tmp_path: Path) -> None:
    _setup_site_home(tmp_path)
    _remove_site_home(tmp_path)
    assert os.listdir(tmp_path) == []
