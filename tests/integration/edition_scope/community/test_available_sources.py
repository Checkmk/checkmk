#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import cmk.checkengine.sources
from cmk.checkengine.source_abc import OptionalSource
from cmk.checkengine.subclass_discovery import discover, get_default_identifier


def test_available_sources() -> None:
    assert set(discover(cmk.checkengine.sources, OptionalSource, get_default_identifier)) == set()
