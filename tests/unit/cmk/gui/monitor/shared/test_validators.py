#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.monitor.shared import validate_uniqueness


def test_validate_uniqueness() -> None:
    with pytest.raises(ValueError, match="Duplicate values are not allowed."):
        validate_uniqueness(["UP", "UP", "DOWN"])
