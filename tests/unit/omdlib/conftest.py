#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest
from _pytest.monkeypatch import MonkeyPatch

import omdlib
from omdlib.contexts import SiteContext
from omdlib.version_info import VersionInfo


@pytest.fixture(autouse=True)
def omd_base_path(monkeypatch: MonkeyPatch, tmp_path: Path):
    monkeypatch.setattr(omdlib.utils, "omd_base_path", lambda: str(tmp_path))


@pytest.fixture()
def version_info() -> VersionInfo:
    return VersionInfo(omdlib.__version__)


@pytest.fixture()
def site_context(tmp_path: Path, monkeypatch: MonkeyPatch) -> SiteContext:
    monkeypatch.setattr(
        SiteContext, "dir", property(lambda s: "%s/omd/sites/%s" % (tmp_path, s.name))
    )
    monkeypatch.setattr(
        SiteContext,
        "real_dir",
        property(lambda s: "%s/opt/omd/sites/%s" % (tmp_path, s.name)),
    )

    return SiteContext("unit")
