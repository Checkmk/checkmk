#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

# Show the values of a failing assertion in the scenario too, not only in the test module.
# This runs before the scenario's first import, as a module is rewritten only on import.
pytest.register_assert_rewrite("tests.performance.system.nagios.scenario")
