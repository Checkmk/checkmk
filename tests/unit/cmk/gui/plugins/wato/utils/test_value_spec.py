#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pytest

from cmk.gui.plugins.wato.utils import Levels


def test_raises_with_wrong_levels_unit_type():
    with pytest.raises(ValueError):
        Levels(unit=1)  # type: ignore
