#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.utils.bi.bi_packs import bi_packs
import tests.unit.cmk.utils.bi.bi_test_data.sample_config as sample_config


@pytest.fixture(scope="function")
def bi_packs_sample_config(monkeypatch):
    try:
        bi_packs.load_config_from_schema(sample_config.bi_packs_config)
        monkeypatch.setattr("cmk.utils.bi.bi_packs.bi_packs.load_config", lambda: None)
        monkeypatch.setattr("cmk.utils.bi.bi_packs.bi_packs.save_config", lambda: None)
        yield bi_packs
    finally:
        bi_packs.cleanup()
