#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from cmk.bakery.internal import LogicalPath, SiteFile
from cmk.bakery.v2_unstable import OS


def test_site_file_treats_an_empty_line_mapping_as_none() -> None:
    with_empty = SiteFile(
        base_os=OS.LINUX, source=Path("source"), location=LogicalPath.LIB, line_mapping={}
    )
    without = SiteFile(base_os=OS.LINUX, source=Path("source"), location=LogicalPath.LIB)

    assert with_empty == without
