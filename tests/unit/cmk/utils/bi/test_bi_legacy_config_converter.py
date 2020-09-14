#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import cmk.utils.bi.bi_legacy_config_converter
import bi_test_data.sample_config as sample_config


def test_bi_legacy_config_conversion(monkeypatch):
    monkeypatch.setattr("cmk.utils.bi.bi_legacy_config_converter.BIManagement._get_config_string",
                        lambda x: sample_config.LEGACY_BI_PACKS_CONFIG_STRING)

    schema_from_legacy_packs = cmk.utils.bi.bi_legacy_config_converter.BILegacyConfigConverter(
    ).get_schema_for_packs()
    assert sample_config.bi_packs_config["packs"] == schema_from_legacy_packs
