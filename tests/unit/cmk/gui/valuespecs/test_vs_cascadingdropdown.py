#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import cmk.gui.valuespec as vs

from .utils import expect_validate_failure, expect_validate_success


class TestCascadingDropDown:
    def test_validate(self) -> None:
        """Basic test for validate function of CascadingDropdown"""
        valuespec = vs.CascadingDropdown(
            choices=[
                (
                    "direct",
                    "Direct URL",
                    vs.TextInput(),
                ),
            ],
        )

        expect_validate_success(valuespec, ("direct", "smth"))
        expect_validate_failure(
            valuespec, ("zzzzzz", "smth"), match=r"Value \('zzzzzz', 'smth'\) is not allowed here."
        )
