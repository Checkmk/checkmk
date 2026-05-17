#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk import graphing_engine


def test_package_imports() -> None:
    assert graphing_engine.__name__ == "cmk.graphing_engine"
