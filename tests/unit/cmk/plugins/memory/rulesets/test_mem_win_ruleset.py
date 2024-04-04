#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Literal

import pytest

from cmk.plugins.memory.rulesets.mem_win import migrate


def test_migrate_invalid() -> None:
    with pytest.raises(ValueError):
        migrate(42)


def text_migrate_empty() -> None:
    assert migrate({}) == {}


def text_migrate_average_noop() -> None:
    assert migrate({"average": 180.0}) == {"average": 180.0}


def test_migrate_average() -> None:
    assert migrate({"average": 3}) == {"average": 180.0}


@pytest.mark.parametrize("key", ["memory", "pagefile"])
def test_migrate_abs_free(key: Literal["memory", "pagefile"]) -> None:
    assert migrate({key: (1, 2)}) == {
        key: {
            "abs_free": {
                "lower": ("fixed", (1048576, 2097152)),
                "upper": ("no_levels", None),
            },
        },
    }


@pytest.mark.parametrize("key", ["memory", "pagefile"])
def test_migrate_perc(key: Literal["memory", "pagefile"]) -> None:
    assert migrate({key: (0.1, 0.2)}) == {
        key: {
            "perc_used": {
                "lower": ("no_levels", None),
                "upper": ("fixed", (0.1, 0.2)),
            },
        },
    }


@pytest.mark.parametrize("key", ["memory", "pagefile"])
def test_migrate_memory_abs_used(key: Literal["memory", "pagefile"]) -> None:
    assert migrate(
        {
            key: {
                "period": "minute",
                "horizon": 4,
                "levels_upper": ("absolute", (0.5, 1.0)),
                "levels_lower": ("stdev", (2.0, 4.0)),
                "levels_upper_min": (1.0, 2.0),
            },
        }
    ) == {
        key: {
            "abs_used": {
                "lower": (
                    "cmk_postprocessed",
                    "predictive_levels",
                    {
                        "period": "minute",
                        "horizon": 4,
                        "levels": ("stdev", (2.0, 4.0)),
                        "bound": None,
                    },
                ),
                "upper": (
                    "cmk_postprocessed",
                    "predictive_levels",
                    {
                        "period": "minute",
                        "horizon": 4,
                        "levels": ("absolute", (1024**3 // 2, 1024**3)),
                        "bound": (1024**3, 1024**3 * 2),
                    },
                ),
            },
        },
    }


@pytest.mark.parametrize("key", ["memory", "pagefile"])
def test_migrate_memory_abs_used_no_lower(key: Literal["memory", "pagefile"]) -> None:
    assert migrate(
        {
            key: {
                "period": "minute",
                "horizon": 4,
                "levels_upper": ("absolute", (0.5, 1.0)),
            },
        }
    ) == {
        key: {
            "abs_used": {
                "lower": ("no_levels", None),
                "upper": (
                    "cmk_postprocessed",
                    "predictive_levels",
                    {
                        "period": "minute",
                        "horizon": 4,
                        "levels": ("absolute", (1024**3 // 2, 1024**3)),
                        "bound": None,
                    },
                ),
            },
        },
    }
