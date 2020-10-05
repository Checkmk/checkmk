#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import List, Union, Dict, Type, Any
from marshmallow import Schema, validate  # type: ignore[import]
from marshmallow_oneofschema import OneOfSchema  # type: ignore[import]

from cmk.utils.bi.bi_lib import (
    bi_aggregation_function_registry,
    ABCBIAggregationFunction,
    ReqConstant,
    ReqString,
    ReqInteger,
    ReqNested,
)

# State weight. OK, PENDING, WARN, UNKNOWN, CRIT
_state_mappings = {
    0: 0.0,  # OK/UP
    -1: 0.5,  # PENDING
    1: 1.0,  # WARN/DOWN
    3: 3.0,  # UNKNOWN
    4: 4.0,  # UNAVAILABLE
    2: 10.0,  # CRIT
}

# The reversed mapping is used for generating the return value
# Possible return values are OK(0), WARN(1), CRIT(2), UNKNOWN(3)
# Since the original CRIT value was mapped to 10.0, there is no
# reverse mapping of 2.0 -> 2 available.
# A 2.0 can be introduced by the restrict_to_state mechanism
_reversed_mappings = {v: k for k, v in _state_mappings.items()}
_reversed_mappings[2.0] = 2


def mapped_states(func):
    def wrap(self, states: List[int]) -> int:
        new_states = sorted(map(lambda x: _state_mappings[x], states))
        aggr_state = float(func(self, new_states))
        return _reversed_mappings.get(aggr_state, 3)

    return wrap


#   .--Best----------------------------------------------------------------.
#   |                         ____            _                            |
#   |                        | __ )  ___  ___| |_                          |
#   |                        |  _ \ / _ \/ __| __|                         |
#   |                        | |_) |  __/\__ \ |_                          |
#   |                        |____/ \___||___/\__|                         |
#   |                                                                      |
#   +----------------------------------------------------------------------+


@bi_aggregation_function_registry.register
class BIAggregationFunctionBest(ABCBIAggregationFunction):
    @classmethod
    def type(cls) -> str:
        return "best"

    @classmethod
    def schema(cls) -> Type["BIAggregationFunctionBestSchema"]:
        return BIAggregationFunctionBestSchema

    def __init__(self, aggr_function_config: Dict[str, Any]):
        super().__init__(aggr_function_config)
        self.count = aggr_function_config["count"]
        self.restrict_state = aggr_function_config["restrict_state"]

    @mapped_states
    def aggregate(self, states: List[float]) -> Union[int, float]:
        return float(min(self.restrict_state, states[min(len(states) - 1, self.count - 1)]))


class BIAggregationFunctionBestSchema(Schema):
    type = ReqConstant(BIAggregationFunctionBest.type())
    count = ReqInteger(default=1)
    restrict_state = ReqInteger(default=2, validate=validate.OneOf([
        0,
        1,
        2,
    ]))


#   .--Worst---------------------------------------------------------------.
#   |                    __        __             _                        |
#   |                    \ \      / /__  _ __ ___| |_                      |
#   |                     \ \ /\ / / _ \| '__/ __| __|                     |
#   |                      \ V  V / (_) | |  \__ \ |_                      |
#   |                       \_/\_/ \___/|_|  |___/\__|                     |
#   |                                                                      |
#   +----------------------------------------------------------------------+


@bi_aggregation_function_registry.register
class BIAggregationFunctionWorst(ABCBIAggregationFunction):
    @classmethod
    def type(cls) -> str:
        return "worst"

    @classmethod
    def schema(cls) -> Type["BIAggregationFunctionWorstSchema"]:
        return BIAggregationFunctionWorstSchema

    def __init__(self, aggr_function_config: Dict[str, Any]):
        super().__init__(aggr_function_config)
        self.count = aggr_function_config["count"]
        self.restrict_state = aggr_function_config["restrict_state"]

    @mapped_states
    def aggregate(self, states: List[float]) -> Union[int, float]:
        return float(min(self.restrict_state, states[max(0, len(states) - self.count)]))


class BIAggregationFunctionWorstSchema(Schema):
    type = ReqConstant(BIAggregationFunctionWorst.type())
    count = ReqInteger(default=1, example=2)
    restrict_state = ReqInteger(default=2, validate=validate.OneOf([
        0,
        1,
        2,
    ]))


#   .--CountOK-------------------------------------------------------------.
#   |                 ____                  _    ___  _  __                |
#   |                / ___|___  _   _ _ __ | |_ / _ \| |/ /                |
#   |               | |   / _ \| | | | '_ \| __| | | | ' /                 |
#   |               | |__| (_) | |_| | | | | |_| |_| | . \                 |
#   |                \____\___/ \__,_|_| |_|\__|\___/|_|\_\                |
#   |                                                                      |
#   +----------------------------------------------------------------------+


@bi_aggregation_function_registry.register
class BIAggregationFunctionCountOK(ABCBIAggregationFunction):
    @classmethod
    def type(cls) -> str:
        return "count_ok"

    @classmethod
    def schema(cls) -> Type["BIAggregationFunctionCountOKSchema"]:
        return BIAggregationFunctionCountOKSchema

    def __init__(self, aggr_function_config: Dict[str, Any]):
        super().__init__(aggr_function_config)
        self.levels_ok = aggr_function_config["levels_ok"]
        self.levels_warn = aggr_function_config["levels_warn"]

    @mapped_states
    def aggregate(self, states: List[float]) -> Union[int, float]:
        ok_nodes = len([x for x in states if x == 0.0])
        if self._check_levels(ok_nodes, len(states), self.levels_ok):
            return 0.0
        if self._check_levels(ok_nodes, len(states), self.levels_warn):
            return 1.0
        return 2.0

    def _check_levels(self, ok_nodes: int, total_nodes: int, levels: Dict) -> bool:
        if levels["type"] == "count":
            return ok_nodes >= levels["value"]
        return (ok_nodes / total_nodes) * 100 >= levels["value"]


class BIAggregationFunctionCountSettings(Schema):
    type = ReqString(default="count", validate=validate.OneOf(["count", "percentage"]))
    value = ReqInteger(default=1)


class BIAggregationFunctionCountOKSchema(Schema):
    type = ReqConstant(BIAggregationFunctionCountOK.type())
    levels_ok = ReqNested(BIAggregationFunctionCountSettings)
    levels_warn = ReqNested(BIAggregationFunctionCountSettings)


#   .--SchemaReg.----------------------------------------------------------.
#   |       ____       _                          ____                     |
#   |      / ___|  ___| |__   ___ _ __ ___   __ _|  _ \ ___  __ _          |
#   |      \___ \ / __| '_ \ / _ \ '_ ` _ \ / _` | |_) / _ \/ _` |         |
#   |       ___) | (__| | | |  __/ | | | | | (_| |  _ <  __/ (_| |_        |
#   |      |____/ \___|_| |_|\___|_| |_| |_|\__,_|_| \_\___|\__, (_)       |
#   |                                                       |___/          |
#   +----------------------------------------------------------------------+


class BIAggregationFunctionSchema(OneOfSchema):
    type_field = "type"
    type_field_remove = False
    type_schemas = dict((k, v.schema()) for k, v in bi_aggregation_function_registry.items())

    # type_schemas ={
    #    "worst": BIAggregationFunctionWorstSchema,
    #    "best": BIAggregationFunctionBestSchema,
    #    "count_ok": BIAggregationFunctionCountOKSchema,
    #}

    def get_obj_type(self, obj: ABCBIAggregationFunction) -> str:
        return obj.type()
