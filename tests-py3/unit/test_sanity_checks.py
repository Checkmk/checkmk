#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from pathlib import Path
import pytest  # type: ignore[import]
from testlib import (cmk_path, utils)

# Use this list in order to allow the deletion of specific check plugins
CHECKS_ALLOWED_TO_VANISH = ["a_very_bad_check_plugin"]


@pytest.mark.parametrize("dir_to_check", [
    Path(cmk_path(), "cmk", "base", "plugins", "agent_based"),
    Path(cmk_path(), "checks"),
])
def test_keep_already_existing_checks(dir_to_check):

    not_allowed_to_vanished = []
    for deleted_file in utils.find_git_rm_mv_files(dir_to_check):

        if ".include" in deleted_file or deleted_file in CHECKS_ALLOWED_TO_VANISH:
            # Skip .include files as they are allowed to vanish
            continue

        not_allowed_to_vanished.append(deleted_file)

    if not_allowed_to_vanished:
        pytest.fail(
            "It seems you're trying to remove or rename already existing check(s): %s.\n"
            "This may break existing site configurations.\n"
            "In case you're *absolutley* sure what you're doing, perform the following steps:\n"
            "* Create an *incompatible* werk for this change\n"
            "* Give the user hints what he might need to do (change rules, remove graph history, perform rediscovery\n"
            "* Add you're deleted check to the exception list (CHECKS_ALLOWED_TO_VANISH) found in this test."
            % str(not_allowed_to_vanished))
