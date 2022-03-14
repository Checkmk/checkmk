#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import List, Sequence, Tuple

from cmk.utils.parameters import (
    boil_down_parameters,
    TimespecificParameters,
    TimespecificParameterSet,
)
from cmk.utils.type_defs import LegacyCheckParameters


def _default() -> LegacyCheckParameters:
    return {"default": 42}


def _tp_values() -> List[Tuple[str, LegacyCheckParameters]]:
    return [("tp1", {"value": "from tp1"}), ("tp2", {"value": "from tp2"})]


class TestTimespecificParameterSet:
    def test_from_parameters_ts_dict(self):

        tsp = TimespecificParameterSet.from_parameters(
            {
                "tp_default_value": _default(),
                "tp_values": _tp_values(),
            }
        )
        assert tsp.default == _default()
        assert tsp.timeperiod_values == tuple(_tp_values())

    def test_from_paramters_legacy_tuple(self):
        tsp = TimespecificParameterSet.from_parameters((1, 2))
        assert tsp.default == (1, 2)
        assert not tsp.timeperiod_values

    def test_from_parameters_constant_dict(self):
        tsp = TimespecificParameterSet.from_parameters(_default())
        assert tsp.default == _default()
        assert not tsp.timeperiod_values

    def test_evaluate_constant_reevaluates_to_itself(self):
        assert TimespecificParameterSet(_default(), ()).evaluate(lambda x: True) == _default()

    def test_evaluate_no_period_active(self):
        assert (
            TimespecificParameterSet(_default(), _tp_values()).evaluate(lambda x: False)
            == _default()
        )

    def test_evaluate_first_period_wins(self):
        assert TimespecificParameterSet(_default(), _tp_values()).evaluate(lambda x: True) == {
            "default": 42,
            "value": "from tp1",
        }

    def test_evaluate_tp_filtering(self):
        assert TimespecificParameterSet(_default(), _tp_values()).evaluate(
            lambda x: x == "tp2"
        ) == {"default": 42, "value": "from tp2"}


class TestTimespecificParameters:
    def test_first_key_wins(self):
        assert TimespecificParameters(
            (
                TimespecificParameterSet(
                    {"key": "I am only default, but the most specific rule!"}, ()
                ),
                TimespecificParameterSet(
                    {"key": "default"},
                    [
                        (
                            "active_tp",
                            {
                                "key": "I am a specificly time-matching value, but from a more general rule!"
                            },
                        )
                    ],
                ),
            )
        ).evaluate(lambda x: True) == {"key": "I am only default, but the most specific rule!"}

    def test_first_tuple_wins(self):
        tuple_1: List[Tuple[str, LegacyCheckParameters]] = [("tp3", (1, 1))]
        tuple_2: List[Tuple[str, LegacyCheckParameters]] = [("tp3", (2, 2))]
        assert TimespecificParameters(
            (
                TimespecificParameterSet(_default(), _tp_values()),
                TimespecificParameterSet(_default(), _tp_values() + tuple_1),
                TimespecificParameterSet(_default(), tuple_2 + _tp_values()),
            )
        ).evaluate(lambda x: True) == (1, 1)


def _all_dicts() -> Sequence[LegacyCheckParameters]:
    return [{"key": "first_value"}, {"key": "second_value"}, {"key2": "some_value"}]


def _with_tuple() -> Sequence[LegacyCheckParameters]:
    return [(23, 23), {"key": "first_value"}, (666, 666)]


def test_boil_down_parameters_good_case():
    assert boil_down_parameters(_all_dicts(), {"default": "some_value"}) == {
        "key": "first_value",
        "key2": "some_value",
        "default": "some_value",
    }
    assert boil_down_parameters(_all_dicts(), None) == {
        "key": "first_value",
        "key2": "some_value",
    }


def test_boil_down_parameters_first_tuple_wins():
    assert boil_down_parameters(_with_tuple(), (42, 42)) == (23, 23)
    assert boil_down_parameters((), (42, 42)) == (42, 42)


def test_boil_down_parameters_default_is_tuple():
    assert boil_down_parameters((), (42, 42)) == (42, 42)
    assert boil_down_parameters(_all_dicts(), (42, 42)) == {
        "key": "first_value",
        "key2": "some_value",
    }
