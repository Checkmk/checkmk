#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import cmk.gui.valuespec as vs

from .utils import expect_validate_failure, expect_validate_success


class TestRegexp:
    def test_validate(self) -> None:
        expect_validate_success(vs.RegExp("infix"), "^$")
        expect_validate_failure(vs.RegExp("infix"), "(", match="Invalid regular expression:")
        expect_validate_failure(
            vs.RegExp("infix", mingroups=1), "^$", match="You need at least <b>1</b> groups."
        )
        expect_validate_success(vs.RegExp("infix", mingroups=1), "^(.+)$")
        expect_validate_failure(
            vs.RegExp("infix", maxgroups=2),
            "^(.)(.)(.)$",
            match="It must have at most <b>2</b> groups.",
        )
        expect_validate_success(vs.RegExp("infix", maxgroups=2), "^(.+)$")
