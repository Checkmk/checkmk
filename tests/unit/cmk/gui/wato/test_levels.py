#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from tests.unit.cmk.base.plugins.agent_based.utils.diskstat import LEVELS

from cmk.gui.plugins.wato.utils import PredictiveLevels


def test_load_levels_wato() -> None:
    # when scaling the predictive levels we make certain assumptions about the
    # wato structure of predictive levels here we try to make sure that these
    # assumptions are still correct. if this test fails, fix it and adapt
    # _scale_levels_predictive to handle the changed values
    pl = PredictiveLevels()
    pl.validate_value(LEVELS, "")
    pl.validate_datatype(LEVELS, "")
