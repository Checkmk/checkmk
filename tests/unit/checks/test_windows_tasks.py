#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from testlib import Check  # type: ignore[import]
import cmk.gui.plugins.wato.check_parameters.windows_tasks as wato_windows_tasks

import pytest  # type: ignore[import]

# Mark all tests in this file as check related tests
pytestmark = pytest.mark.checks


def test_default_exit_codes():
    check = Check("windows_tasks")
    assert wato_windows_tasks._MAP_EXIT_CODES == check.context["_MAP_EXIT_CODES"]
