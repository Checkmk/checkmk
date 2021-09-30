#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest
from _pytest.monkeypatch import MonkeyPatch

import cmk.base.config
from cmk.base.cee.core_cmc import CMC
from cmk.base.cee.microcore_config import CmcPb
from cmk.base.config import get_microcore_config_format
from cmk.base.core_factory import create_core
from cmk.base.core_nagios import NagiosCore


@pytest.mark.parametrize(
    "core_name, expected_class",
    [
        ("nagios", NagiosCore),
        ("cmc", {"binary": CMC, "protobuf": CmcPb}[get_microcore_config_format()]),
    ],
)
def test_create_core(core_name, expected_class):
    assert isinstance(create_core(core_name), expected_class)


@pytest.mark.parametrize(
    "cmc_format, expected_class",
    [
        ("binary", CMC),
        ("protobuf", CmcPb),
    ],
)
def test_create_cmc_core(monkeypatch: MonkeyPatch, cmc_format, expected_class):
    monkeypatch.setattr(
        cmk.base.config,
        "microcore_config_format",
        cmc_format,
    )
    assert isinstance(create_core("cmc"), expected_class)
