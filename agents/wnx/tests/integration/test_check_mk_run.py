#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import List

import pytest
from utils import YamlDict


@pytest.fixture(
    name="work_config",
    params=[
        {"only_from": []},
        {"only_from": ["127.0.0.1", "::1", "10.1.2.3"]},
    ],
    ids=[
        "only_from=None",
        "only_from=127.0.0.1_10.1.2.3",
    ],
)
def work_config_fixture(request, default_yaml_config: YamlDict) -> YamlDict:
    if request.param["only_from"]:
        default_yaml_config["global"]["only_from"] = request.param["only_from"]
    return default_yaml_config


def test_check_mk_controller(
    obtain_output: List[str],
    work_config: YamlDict,
):
    sections = [line for line in obtain_output if line[:3] == "<<<"]
    assert sections[0] == "<<<check_mk>>>"
    assert sections[-1] == "<<<systemtime>>>"
    assert len(sections) >= 17
