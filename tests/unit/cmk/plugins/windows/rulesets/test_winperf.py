#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.plugins.windows.rulesets.winperf import migrate

_MIGRATED = {"counters": [{"section": "processor", "counter": "238"}]}


@pytest.mark.parametrize(
    "old, expected",
    [
        pytest.param([], {"counters": []}, id="empty_list"),
        pytest.param([("processor", "238")], _MIGRATED, id="list_of_tuples"),
        pytest.param([["processor", "238"]], _MIGRATED, id="list_of_lists"),
        pytest.param(_MIGRATED, _MIGRATED, id="already_migrated"),
    ],
)
def test_migrate(old: object, expected: dict[str, object]) -> None:
    assert migrate(old) == expected


@pytest.mark.parametrize(
    "value",
    [
        pytest.param("processor", id="str"),
        pytest.param(None, id="none"),
        pytest.param({}, id="empty_dict"),
        pytest.param([("a", "b", "c")], id="counter_triple"),
        pytest.param([{}], id="empty_counter_dict"),
    ],
)
def test_migrate_rejects_unknown_values(value: object) -> None:
    with pytest.raises(ValueError):
        migrate(value)
