#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import cmk.base.plugins.agent_based.windows_tasks as check_windows_tasks

import cmk.gui.plugins.wato.check_parameters.windows_tasks as wato_windows_tasks


def test_default_exit_codes() -> None:
    assert wato_windows_tasks._MAP_EXIT_CODES == check_windows_tasks._MAP_EXIT_CODES
