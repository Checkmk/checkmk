#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import cmk.gui.valuespec as vs


class TestValueSpecPasswordSpec:
    def test_mask(self) -> None:
        assert vs.PasswordSpec().mask("eteer") == "******"
