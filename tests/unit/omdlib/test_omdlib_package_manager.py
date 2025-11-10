#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from omdlib.package_manager import get_edition

from cmk.ccc import version


@pytest.mark.parametrize("edition", list(version.Edition))
def test_get_edition(edition: version._EditionValue) -> None:
    assert get_edition(f"1.2.3.{edition.long}") != "unknown"
