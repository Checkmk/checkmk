#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest

# Show the values of a failing assertion in a scenario too, not only in the test module.
# This runs before any scenario is imported, as a module is rewritten only on import.
pytest.register_assert_rewrite(
    *(f"{__name__}.{s.parent.name}.scenario" for s in Path(__file__).parent.glob("*/scenario.py"))
)
