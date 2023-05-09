#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.api.agent_based import utils
from cmk.base.plugins.agent_based.agent_based_api.v1 import Result


def test_check_levels_predictive_default_render_func(mocker):
    mocker.patch("cmk.base.check_api._prediction.get_levels",
                 return_value=(None, (2.2, 4.2, None, None)))
    mocker.patch("cmk.base.check_api_utils._hostname", value="unittest")
    mocker.patch("cmk.base.check_api_utils._service_description",
                 value="unittest-service-description")

    result = next(utils.check_levels_predictive(42.42, metric_name="metric_name", levels={}))
    assert isinstance(result, Result)
    assert result.summary.startswith("42.42")
