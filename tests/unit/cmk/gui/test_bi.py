#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]

import cmk.gui.bi as bi


# NOTE: The host_aggregations variable only contains necessary elements.
# Usually the tuple contains more elements.
@pytest.mark.parametrize(
    "host_aggregations, expected",
    [
        (  # elements are combined:
            [({}, ["1", "2"]), ({}, ["3", "4"])],
            ["1", "2", "3", "4"],
        ),
        (  # elements of disabled aggregations are discarded:
            [({
                "disabled": True
            }, ["1", "2"]), ({}, ["3", "4"])],
            ["3", "4"],
        ),
        (  # elements shall only appear once:
            [({}, ["1", "2"]), ({}, ["2", "3"])],
            ["1", "2", "3"],
        ),
        (  # the output should be sorted:
            [({}, ["3"]), ({}, ["2", "1"])],
            ["1", "2", "3"],
        ),
        (  # paths are not treated specially:
            [({}, ["foo/bar"]), ({}, ["1"])],
            ["1", "foo/bar"],
        ),
    ],
)
def test_get_aggregation_group_trees(monkeypatch, host_aggregations, expected):
    monkeypatch.setattr(bi.config, "aggregations", [])
    monkeypatch.setattr(bi.config, "host_aggregations", host_aggregations)
    assert bi.get_aggregation_group_trees() == expected
