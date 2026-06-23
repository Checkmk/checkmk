#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Annotated, Literal

from annotated_types import MinLen
from pydantic import AfterValidator

from cmk.gui.openapi.framework.model import api_field, api_model
from cmk.livestatus_client.expressions import LqSafe

from .._models import HostFilter, HostState, HostStateLabel
from ._validators import validate_uniqueness

# TODO: look into whether we can utilize generics when generating our shared typing. It's not great
# that this functionality is tied to the field names or the state choice enum. This information
# would be ideally passed in the respective endpoint definitions.

_NO_NEWLINES_REGEX = r"^[^\n]*$"

type StringOp = Literal["contains", "matches"]

type NumericOp = Literal["lt", "lte", "eq", "gt", "gte"]

type NumericField = Literal[
    "num_services",
    "num_services_crit",
    "num_services_ok",
    "num_services_pending",
    "num_services_unknown",
    "num_services_warn",
]


@api_model
class StringCondition:
    type: Literal["condition"] = api_field(
        description="Node type discriminator", example="condition"
    )
    field: Literal["name", "alias", "address"] = api_field(
        description="String host field to filter on", example="name"
    )
    op: StringOp = api_field(description="String match operation", example="contains")
    value: str = api_field(
        description="Value to match against the field", example="web", pattern=_NO_NEWLINES_REGEX
    )


@api_model
class StateChoiceCondition:
    type: Literal["condition"] = api_field(
        description="Node type discriminator", example="condition"
    )
    field: Literal["state"] = api_field(description="Host state field", example="state")
    op: Literal["one_of"] = api_field(description="Set membership operation", example="one_of")
    value: Annotated[list[HostStateLabel], MinLen(1), AfterValidator(validate_uniqueness)] = (
        api_field(
            description="Host states to match",
            example=["UP", "DOWN"],
        )
    )


@api_model
class NumericCondition:
    type: Literal["condition"] = api_field(
        description="Node type discriminator", example="condition"
    )
    field: NumericField = api_field(
        description="Numeric service count field to filter on", example="num_services"
    )
    op: NumericOp = api_field(description="Numeric comparison operation", example="gt")
    value: int = api_field(description="Integer value to compare against", example=0)


@api_model
class BooleanCondition:
    type: Literal["condition"] = api_field(
        description="Node type discriminator", example="condition"
    )
    field: Literal["acknowledged", "in_downtime"] = api_field(
        description="Host boolean field to filter on", example="acknowledged"
    )
    op: Literal["eq"] = api_field(description="Equality operation", example="eq")
    value: bool = api_field(description="Boolean value to compare against", example=False)


type ConditionNode = StringCondition | StateChoiceCondition | NumericCondition | BooleanCondition


@api_model(slots=False)
class AndNode:
    type: Literal["and"] = api_field(
        description="Logical AND: all children must match", example="and"
    )
    children: Annotated[list["FilterNode"], MinLen(2)] = api_field(
        description="Child filter nodes",
        example=[
            StringCondition(type="condition", field="name", op="matches", value="heute"),
            NumericCondition(type="condition", field="num_services", op="eq", value=42),
        ],
    )


@api_model(slots=False)
class OrNode:
    type: Literal["or"] = api_field(
        description="Logical OR: at least one child must match", example="or"
    )
    children: Annotated[list["FilterNode"], MinLen(2)] = api_field(
        description="Child filter nodes",
        example=[
            StringCondition(type="condition", field="name", op="matches", value="heute"),
            NumericCondition(type="condition", field="num_services", op="eq", value=42),
        ],
    )


@api_model(slots=False)
class NotNode:
    type: Literal["not"] = api_field(
        description="Logical NOT: the child must not match", example="not"
    )
    child: "FilterNode" = api_field(description="Child filter node")


type FilterNode = AndNode | OrNode | NotNode | ConditionNode


def parse_as_livestatus_filter(node: FilterNode) -> HostFilter:
    filters: list[str] = []
    _accumulate_filters(node, filters)
    return HostFilter("\n".join(str(LqSafe(f)) for f in filters))


def _accumulate_filters(node: FilterNode, filters: list[str]) -> None:
    match node:
        case StringCondition():
            filters.append(f"Filter: {node.field} {_STRING_OP_TO_LS[node.op]} {node.value}")

        case NumericCondition():
            filters.append(f"Filter: {node.field} {_NUMERIC_OP_TO_LS[node.op]} {node.value}")

        case BooleanCondition():
            match node.field:
                case "in_downtime":
                    # Livestatus has no boolean downtime column; a host is in a scheduled
                    # downtime when scheduled_downtime_depth is greater than zero.
                    op = ">" if node.value else "="
                    filters.append(f"Filter: scheduled_downtime_depth {op} 0")
                case _:
                    filters.append(f"Filter: {node.field} = {int(node.value)}")

        case StateChoiceCondition():
            for value in node.value:
                filters.append(f"Filter: {node.field} = {HostState[value]}")

            match node.op:
                case "one_of" if len(node.value) > 1:
                    filters.append(f"Or: {len(node.value)}")

        case AndNode() | OrNode():
            for child in node.children:
                _accumulate_filters(child, filters)

            match node.type:
                case "and":
                    filters.append(f"And: {len(node.children)}")
                case "or":
                    filters.append(f"Or: {len(node.children)}")

        case NotNode():
            _accumulate_filters(node.child, filters)
            filters.append("Negate:")


_NUMERIC_OP_TO_LS = {
    "eq": "=",
    "gt": ">",
    "gte": ">=",
    "lt": "<",
    "lte": "<=",
}
_STRING_OP_TO_LS = {
    "contains": "~~",
    "matches": "~",
}
