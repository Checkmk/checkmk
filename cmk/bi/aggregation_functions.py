#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from marshmallow import validate
from marshmallow_oneofschema import OneOfSchema

from cmk.bi.lib import (
    ABCBIAggregationFunction,
    AggregationKind,
    bi_aggregation_function_registry,
    BIStates,
    ReqConstant,
    ReqInteger,
    ReqNested,
    ReqString,
)
from cmk.bi.schema import Schema

_bi_criticality_level = {
    BIStates.OK: 0,
    BIStates.PENDING: 2,
    BIStates.WARN: 4,
    BIStates.UNKNOWN: 6,
    BIStates.CRIT: 8,
}

# The reversed mapping is used to generate aggregation function return value
_reversed_bi_criticality_level = {v: k for k, v in _bi_criticality_level.items()}


def mapped_states(f: Callable[[Any, list[int]], int]) -> Callable[[Any, list[int]], int]:
    def wrapped_f(self: ABCBIAggregationFunction, states: list[int]) -> int:
        new_states = sorted(_bi_criticality_level[state] for state in states)
        return _reversed_bi_criticality_level.get(f(self, new_states), BIStates.UNKNOWN)

    return wrapped_f


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
    def kind(cls) -> AggregationKind:
        return "best"

    @classmethod
    def schema(cls) -> type[BIAggregationFunctionBestSchema]:
        return BIAggregationFunctionBestSchema

    def serialize(self):
        return {
            "type": self.kind(),
            "count": self.count,
            "restrict_state": self.restrict_state,
        }

    def __init__(self, aggr_function_config: dict[str, Any]) -> None:
        super().__init__(aggr_function_config)
        self.count = aggr_function_config["count"]
        self.restrict_state = aggr_function_config["restrict_state"]
        self.restricted_bi_level = _bi_criticality_level[self.restrict_state]

    @mapped_states
    def aggregate(self, states: list[int]) -> int:
        return min(self.restricted_bi_level, states[min(len(states) - 1, self.count - 1)])


class BIAggregationFunctionBestSchema(Schema):
    type = ReqConstant(
        BIAggregationFunctionBest.kind(), description="Take the best state from all child nodes."
    )
    count = ReqInteger(dump_default=1, description="Take the nth best state.")
    restrict_state = ReqInteger(
        dump_default=2,
        validate=validate.OneOf(
            [
                0,
                1,
                2,
            ]
        ),
        description="Maximum severity for this node.",
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
    def kind(cls) -> AggregationKind:
        return "worst"

    @classmethod
    def schema(cls) -> type[BIAggregationFunctionWorstSchema]:
        return BIAggregationFunctionWorstSchema

    def serialize(self):
        return {
            "type": self.kind(),
            "count": self.count,
            "restrict_state": self.restrict_state,
        }

    def __init__(self, aggr_function_config: dict[str, Any]) -> None:
        super().__init__(aggr_function_config)
        self.count = aggr_function_config["count"]
        self.restrict_state = aggr_function_config["restrict_state"]
        self.restricted_bi_level = _bi_criticality_level[self.restrict_state]

    @mapped_states
    def aggregate(self, states: list[int]) -> int:
        return min(self.restricted_bi_level, states[max(0, len(states) - self.count)])


class BIAggregationFunctionWorstSchema(Schema):
    type = ReqConstant(
        BIAggregationFunctionWorst.kind(), description="Take the worst state from all child nodes."
    )
    count = ReqInteger(dump_default=1, example=2, description="Take the nth worst state.")
    restrict_state = ReqInteger(
        dump_default=2,
        validate=validate.OneOf([0, 1, 2]),
        description="Maximum severity for this node.",
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
    def kind(cls) -> AggregationKind:
        return "count_ok"

    @classmethod
    def schema(cls) -> type[BIAggregationFunctionCountOKSchema]:
        return BIAggregationFunctionCountOKSchema

    def serialize(self):
        return {
            "type": self.kind(),
            "levels_ok": self.levels_ok,
            "levels_warn": self.levels_warn,
        }

    def __init__(self, aggr_function_config: dict[str, Any]) -> None:
        super().__init__(aggr_function_config)
        self.levels_ok = aggr_function_config["levels_ok"]
        self.levels_warn = aggr_function_config["levels_warn"]

    def aggregate(self, states: list[int]) -> int:
        ok_nodes = states.count(0)
        if self._check_levels(ok_nodes, len(states), self.levels_ok):
            return BIStates.OK
        if self._check_levels(ok_nodes, len(states), self.levels_warn):
            return BIStates.WARN
        return BIStates.CRIT

    def _check_levels(self, ok_nodes: int, total_nodes: int, levels: dict) -> bool:
        if levels["type"] == "count":
            return ok_nodes >= levels["value"]
        return (ok_nodes / total_nodes) * 100 >= levels["value"]


class BIAggregationFunctionCountSettings(Schema):
    type = ReqString(
        dump_default="count",
        validate=validate.OneOf(["count", "percentage"]),
        description="Explicit number or percentage.",
    )
    value = ReqInteger(dump_default=1, description="Value.")


class BIAggregationFunctionCountOKSchema(Schema):
    type = ReqConstant(
        BIAggregationFunctionCountOK.kind(),
        description="Count states from child nodes, defaulting to CRIT if both levels aren't met.",
    )
    levels_ok = ReqNested(
        BIAggregationFunctionCountSettings,
        description="Required number of OK child nodes for total state of OK.",
    )
    levels_warn = ReqNested(
        BIAggregationFunctionCountSettings,
        description="Required number of OK child nodes for total state of WARN.",
    )


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
    type_schemas = {k: v.schema() for k, v in bi_aggregation_function_registry.items()}

    # type_schemas ={
    #    "worst": BIAggregationFunctionWorstSchema,
    #    "best": BIAggregationFunctionBestSchema,
    #    "count_ok": BIAggregationFunctionCountOKSchema,
    # }

    def get_obj_type(self, obj: ABCBIAggregationFunction | dict) -> str:
        return obj["type"] if isinstance(obj, dict) else obj.kind()
