#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Dict, List, Type, Union

from marshmallow import validate
from marshmallow_oneofschema import OneOfSchema  # type: ignore[import]

from cmk.utils.bi.bi_lib import (
    ABCBIAggregationFunction,
    bi_aggregation_function_registry,
    BIStates,
    ReqConstant,
    ReqInteger,
    ReqNested,
    ReqString,
)
from cmk.utils.bi.bi_schema import Schema

_bi_criticality_level = {
    BIStates.OK: 0,
    BIStates.PENDING: 2,
    BIStates.WARN: 4,
    BIStates.UNKNOWN: 6,
    BIStates.CRIT: 8,
}

# The reversed mapping is used to generate aggregation function return value
_reversed_bi_criticality_level = {v: k for k, v in _bi_criticality_level.items()}


def mapped_states(func):
    def wrap(self, states: List[int]) -> int:
        new_states = sorted(map(lambda x: _bi_criticality_level[x], states))
        return _reversed_bi_criticality_level.get(func(self, new_states), BIStates.UNKNOWN)

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

    def serialize(self):
        return {
            "type": self.type(),
            "count": self.count,
            "restrict_state": self.restrict_state,
        }

    def __init__(self, aggr_function_config: Dict[str, Any]) -> None:
        super().__init__(aggr_function_config)
        self.count = aggr_function_config["count"]
        self.restrict_state = aggr_function_config["restrict_state"]
        self.restricted_bi_level = _bi_criticality_level[self.restrict_state]

    @mapped_states
    def aggregate(self, states: List[int]) -> int:
        return min(self.restricted_bi_level, states[min(len(states) - 1, self.count - 1)])


class BIAggregationFunctionBestSchema(Schema):
    type = ReqConstant(BIAggregationFunctionBest.type())
    count = ReqInteger(dump_default=1)
    restrict_state = ReqInteger(
        dump_default=2,
        validate=validate.OneOf(
            [
                0,
                1,
                2,
            ]
        ),
    )


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

    def serialize(self):
        return {
            "type": self.type(),
            "count": self.count,
            "restrict_state": self.restrict_state,
        }

    def __init__(self, aggr_function_config: Dict[str, Any]) -> None:
        super().__init__(aggr_function_config)
        self.count = aggr_function_config["count"]
        self.restrict_state = aggr_function_config["restrict_state"]
        self.restricted_bi_level = _bi_criticality_level[self.restrict_state]

    @mapped_states
    def aggregate(self, states: List[int]) -> int:
        return min(self.restricted_bi_level, states[max(0, len(states) - self.count)])


class BIAggregationFunctionWorstSchema(Schema):
    type = ReqConstant(BIAggregationFunctionWorst.type())
    count = ReqInteger(dump_default=1, example=2)
    restrict_state = ReqInteger(
        dump_default=2,
        validate=validate.OneOf(
            [
                0,
                1,
                2,
            ]
        ),
    )


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

    def serialize(self):
        return {
            "type": self.type(),
            "levels_ok": self.levels_ok,
            "levels_warn": self.levels_warn,
        }

    def __init__(self, aggr_function_config: Dict[str, Any]) -> None:
        super().__init__(aggr_function_config)
        self.levels_ok = aggr_function_config["levels_ok"]
        self.levels_warn = aggr_function_config["levels_warn"]

    def aggregate(self, states: List[int]) -> int:
        ok_nodes = states.count(0)
        if self._check_levels(ok_nodes, len(states), self.levels_ok):
            return BIStates.OK
        if self._check_levels(ok_nodes, len(states), self.levels_warn):
            return BIStates.WARN
        return BIStates.CRIT

    def _check_levels(self, ok_nodes: int, total_nodes: int, levels: Dict) -> bool:
        if levels["type"] == "count":
            return ok_nodes >= levels["value"]
        return (ok_nodes / total_nodes) * 100 >= levels["value"]


class BIAggregationFunctionCountSettings(Schema):
    type = ReqString(dump_default="count", validate=validate.OneOf(["count", "percentage"]))
    value = ReqInteger(dump_default=1)


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
    # }

    def get_obj_type(self, obj: Union[ABCBIAggregationFunction, dict]) -> str:
        if isinstance(obj, dict):
            return obj["type"]
        return obj.type()
