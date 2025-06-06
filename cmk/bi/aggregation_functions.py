#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from typing import Literal, override, TypedDict

from marshmallow import validate
from marshmallow_oneofschema import OneOfSchema

from cmk.bi.lib import (
    ABCBIAggregationFunction,
    AggregationFunctionConfig,
    AggregationKind,
    bi_aggregation_function_registry,
    BIStates,
    ReqConstant,
    ReqInteger,
    ReqNested,
    ReqString,
)
from cmk.bi.schema import Schema

_bi_criticality_level: dict[int, int] = {
    BIStates.OK: 0,
    BIStates.PENDING: 2,
    BIStates.WARN: 4,
    BIStates.UNKNOWN: 6,
    BIStates.CRIT: 8,
}

# The reversed mapping is used to generate aggregation function return value
_reversed_bi_criticality_level = {v: k for k, v in _bi_criticality_level.items()}


def map_states(states: list[int], index: int, restricted_bi_level: int) -> int:
    new_states = sorted(_bi_criticality_level[state] for state in states)
    level = min(restricted_bi_level, new_states[index])
    return _reversed_bi_criticality_level.get(level, BIStates.UNKNOWN)


#   .--Best----------------------------------------------------------------.
#   |                         ____            _                            |
#   |                        | __ )  ___  ___| |_                          |
#   |                        |  _ \ / _ \/ __| __|                         |
#   |                        | |_) |  __/\__ \ |_                          |
#   |                        |____/ \___||___/\__|                         |
#   |                                                                      |
#   +----------------------------------------------------------------------+


class BIAggregationFunctionBestSerialized(AggregationFunctionConfig):
    count: int
    restrict_state: int


@bi_aggregation_function_registry.register
class BIAggregationFunctionBest(ABCBIAggregationFunction):
    @override
    @classmethod
    def kind(cls) -> AggregationKind:
        return "best"

    @override
    @classmethod
    def schema(cls) -> type[BIAggregationFunctionBestSchema]:
        return BIAggregationFunctionBestSchema

    @override
    def serialize(self) -> BIAggregationFunctionBestSerialized:
        return BIAggregationFunctionBestSerialized(
            type=self.kind(),
            count=self.count,
            restrict_state=self.restrict_state,
        )

    @override
    def __init__(self, aggr_function_config: BIAggregationFunctionBestSerialized) -> None:
        super().__init__(aggr_function_config)
        self.count = aggr_function_config["count"]
        self.restrict_state = aggr_function_config["restrict_state"]
        self.restricted_bi_level = _bi_criticality_level[self.restrict_state]

    @override
    def aggregate(self, states: list[int]) -> int:
        index = min(len(states) - 1, self.count - 1)
        return map_states(states, index, self.restricted_bi_level)


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


class BIAggregationFunctionWorstSerialized(AggregationFunctionConfig):
    count: int
    restrict_state: int


@bi_aggregation_function_registry.register
class BIAggregationFunctionWorst(ABCBIAggregationFunction):
    @override
    @classmethod
    def kind(cls) -> AggregationKind:
        return "worst"

    @override
    @classmethod
    def schema(cls) -> type[BIAggregationFunctionWorstSchema]:
        return BIAggregationFunctionWorstSchema

    @override
    def serialize(self) -> BIAggregationFunctionWorstSerialized:
        return BIAggregationFunctionWorstSerialized(
            type=self.kind(),
            count=self.count,
            restrict_state=self.restrict_state,
        )

    @override
    def __init__(self, aggr_function_config: BIAggregationFunctionWorstSerialized) -> None:
        super().__init__(aggr_function_config)
        self.count = aggr_function_config["count"]
        self.restrict_state = aggr_function_config["restrict_state"]
        self.restricted_bi_level = _bi_criticality_level[self.restrict_state]

    @override
    def aggregate(self, states: list[int]) -> int:
        index = max(0, len(states) - self.count)
        return map_states(states, index, self.restricted_bi_level)


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


class BILevelsSerialized(TypedDict):
    type: Literal["count", "percentage"]
    value: float


class BIAggregationFunctionCountOKSerialized(AggregationFunctionConfig):
    levels_ok: BILevelsSerialized
    levels_warn: BILevelsSerialized


@bi_aggregation_function_registry.register
class BIAggregationFunctionCountOK(ABCBIAggregationFunction):
    @override
    @classmethod
    def kind(cls) -> AggregationKind:
        return "count_ok"

    @override
    @classmethod
    def schema(cls) -> type[BIAggregationFunctionCountOKSchema]:
        return BIAggregationFunctionCountOKSchema

    @override
    def serialize(self) -> BIAggregationFunctionCountOKSerialized:
        return BIAggregationFunctionCountOKSerialized(
            type=self.kind(),
            levels_ok=self.levels_ok,
            levels_warn=self.levels_warn,
        )

    @override
    def __init__(self, aggr_function_config: BIAggregationFunctionCountOKSerialized) -> None:
        super().__init__(aggr_function_config)
        self.levels_ok = aggr_function_config["levels_ok"]
        self.levels_warn = aggr_function_config["levels_warn"]

    @override
    def aggregate(self, states: list[int]) -> int:
        ok_nodes = states.count(0)

        if self._check_levels(ok_nodes, len(states), self.levels_ok):
            state = BIStates.OK
        elif self._check_levels(ok_nodes, len(states), self.levels_warn):
            state = BIStates.WARN
        else:
            state = BIStates.CRIT

        return int(state)

    def _check_levels(self, ok_nodes: int, total_nodes: int, levels: BILevelsSerialized) -> bool:
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

    @override
    def get_obj_type(
        self, obj: ABCBIAggregationFunction | AggregationFunctionConfig
    ) -> AggregationKind:
        return obj["type"] if isinstance(obj, dict) else obj.kind()
