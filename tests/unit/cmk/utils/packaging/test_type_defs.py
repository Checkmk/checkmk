#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.utils.packaging._type_defs import PackageName


class TestPackageName:
    @pytest.mark.parametrize("raw_str", ["", "foo;bar"])
    def test_invalid_name(self, raw_str: str) -> None:
        with pytest.raises(ValueError):
            _ = PackageName(raw_str)
