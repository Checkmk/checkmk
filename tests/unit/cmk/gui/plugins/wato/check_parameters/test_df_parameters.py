#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.exceptions import MKUserError
from cmk.gui.plugins.wato.check_parameters.filesystem import (
    _validate_discovery_filesystem_params,
    _transform_discovery_filesystem_params,
)
from cmk.gui.plugins.wato.check_parameters.utils import (
    _transform_discovered_filesystem_params,)


@pytest.mark.parametrize('params', [
    {
        "item_appearance": "mountpoint",
        "grouping_behaviour": "volume_name_and_mountpoint",
    },
])
def test_invalid_discovery_df_rules(params):
    with pytest.raises(MKUserError):
        _validate_discovery_filesystem_params(params, "varprefix")


@pytest.mark.parametrize('params, result', [
    ({}, {}),
    ({
        "include_volume_name": False,
    }, {
        "item_appearance": "mountpoint",
        "grouping_behaviour": "mountpoint",
    }),
    ({
        "include_volume_name": (True, "mountpoint"),
    }, {
        "item_appearance": "volume_name_and_mountpoint",
        "grouping_behaviour": "mountpoint",
    }),
    ({
        "include_volume_name": (True, "volume_name_and_mountpoint"),
    }, {
        "item_appearance": "volume_name_and_mountpoint",
        "grouping_behaviour": "volume_name_and_mountpoint",
    }),
])
def test__transform_discovery_filesystem_params(params, result):
    assert _transform_discovery_filesystem_params(params) == result


@pytest.mark.parametrize('params, result', [
    ({}, {}),
    ({
        "include_volume_name": False,
    }, {
        "item_appearance": "mountpoint",
    }),
    ({
        "include_volume_name": True,
    }, {
        "item_appearance": "volume_name_and_mountpoint",
    }),
])
def test__transform_discovered_filesystem_params(params, result):
    assert _transform_discovered_filesystem_params(params) == result
