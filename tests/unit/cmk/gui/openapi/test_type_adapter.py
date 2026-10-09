#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import operator
from dataclasses import dataclass
from functools import partial

from pydantic import ConfigDict
from pydantic.config import JsonDict

from cmk.gui.openapi._type_adapter import get_cached_type_adapter


@dataclass
class _First:
    value: int


@dataclass
class _Second:
    value: int


def test_configs_differing_only_in_key_order_share_a_type_adapter() -> None:
    adapter = get_cached_type_adapter(int, config=ConfigDict(strict=True, title="X"))

    reordered = get_cached_type_adapter(int, config=ConfigDict(title="X", strict=True))

    assert reordered is adapter


def test_changing_a_config_after_use_takes_effect() -> None:
    config = ConfigDict(strict=True)
    get_cached_type_adapter(int, config=config)
    config["strict"] = False

    adapter = get_cached_type_adapter(int, config=config)

    assert adapter.validate_python("1") == 1


def test_changing_a_nested_config_value_after_use_gives_a_new_type_adapter() -> None:
    json_schema_extra: JsonDict = {"examples": [1]}
    config = ConfigDict(json_schema_extra=json_schema_extra)
    adapter = get_cached_type_adapter(int, config=config)
    json_schema_extra["examples"] = [2]

    changed = get_cached_type_adapter(int, config=config)

    assert changed is not adapter


def test_config_value_only_equal_to_itself_shares_a_type_adapter() -> None:
    config = ConfigDict(alias_generator=partial(operator.add, "prefix_"))
    adapter = get_cached_type_adapter(int, config=config)

    again = get_cached_type_adapter(int, config=config)

    assert again is adapter


def test_reordered_union_prefers_its_own_first_member() -> None:
    get_cached_type_adapter(_First | _Second)

    adapter = get_cached_type_adapter(_Second | _First)

    assert adapter.validate_python({"value": 1}) == _Second(1)


def test_reordered_nested_union_prefers_its_own_first_member() -> None:
    get_cached_type_adapter(list[_First | _Second])

    adapter = get_cached_type_adapter(list[_Second | _First])

    assert adapter.validate_python([{"value": 1}]) == [_Second(1)]
