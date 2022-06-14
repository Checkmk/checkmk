#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging

import pytest

import cmk.utils.bi.bi_legacy_config_converter

from cmk.gui.utils.script_helpers import application_and_request_context

from .bi_test_data import sample_config  # type: ignore[import] # pylint: disable=import-error


def test_bi_legacy_config_conversion(monkeypatch) -> None:
    monkeypatch.setattr(
        "cmk.utils.bi.bi_legacy_config_converter.BIManagement._get_config_string",
        lambda x: sample_config.LEGACY_BI_PACKS_CONFIG_STRING,
    )

    with application_and_request_context():
        schema_from_legacy_packs = cmk.utils.bi.bi_legacy_config_converter.BILegacyConfigConverter(
            logging.Logger("unit test")
        ).get_schema_for_packs()
    assert sample_config.bi_packs_config["packs"] == schema_from_legacy_packs


@pytest.mark.parametrize(
    "old_config,expected_config",
    [
        (
            ("worst", ()),
            {
                "type": "worst",
                "count": 1,
                "restrict_state": 2,
            },
        ),
        (
            ("worst", (2, 1)),
            {
                "type": "worst",
                "count": 2,
                "restrict_state": 1,
            },
        ),
        (
            ("best", ()),
            {
                "type": "best",
                "count": 1,
                "restrict_state": 2,
            },
        ),
        (
            ("best", (2, 1)),
            {
                "type": "best",
                "count": 2,
                "restrict_state": 1,
            },
        ),
        (
            ("count_ok", ()),
            {
                "type": "count_ok",
                "levels_ok": {"type": "count", "value": 2},
                "levels_warn": {"type": "count", "value": 1},
            },
        ),
        (
            ("count_ok", (2, 1)),
            {
                "type": "count_ok",
                "levels_ok": {"type": "count", "value": 2},
                "levels_warn": {"type": "count", "value": 1},
            },
        ),
        (
            ("count_ok", ("5%", "6")),
            {
                "type": "count_ok",
                "levels_ok": {"type": "percentage", "value": 5},
                "levels_warn": {"type": "count", "value": 6},
            },
        ),
        (
            ("count_ok", (5, "6%")),
            {
                "type": "count_ok",
                "levels_ok": {"type": "count", "value": 5},
                "levels_warn": {"type": "percentage", "value": 6},
            },
        ),
    ],
)
def test_aggregation_function_conversion(old_config, expected_config) -> None:
    schema_converter = cmk.utils.bi.bi_legacy_config_converter.BIRuleSchemaConverter
    assert (
        schema_converter.convert_aggr_func_old_to_new(None, old_config) == expected_config  # type: ignore[arg-type]  # irrelevant for test
    )
