#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.ccc.version import __version__
from cmk.werks.utils import resolve_version


def test_resolve_version_without_version() -> None:
    assert resolve_version(None) == __version__


def test_resolve_version_keeps_the_version() -> None:
    assert resolve_version("2.4.0p1") == "2.4.0p1"
