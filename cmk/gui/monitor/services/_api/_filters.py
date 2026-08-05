#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Annotated, Literal

from annotated_types import MinLen
from pydantic import AfterValidator

from cmk.gui.openapi.framework.model import api_field, api_model
from cmk.livestatus_client.expressions import LqSafe

from .._models import ServiceFilter, ServiceState, ServiceStateLabel
from ._validators import validate_uniqueness

# NOTE: these models are named with a "Service" prefix (unlike their hosts counterparts) because
# the OpenAPI spec registers component schemas by class name across every endpoint family; an
# unprefixed name would collide with the identically-shaped, but differently-fielded, hosts filter
# models.


@api_model
class ServiceStateChoiceCondition:
    type: Literal["condition"] = api_field(
        description="Node type discriminator", example="condition"
    )
    field: Literal["state"] = api_field(description="Service state field", example="state")
    op: Literal["one_of"] = api_field(description="Set membership operation", example="one_of")
    value: Annotated[list[ServiceStateLabel], MinLen(1), AfterValidator(validate_uniqueness)] = (
        api_field(
            description="Service states to match",
            example=["OK", "WARN"],
        )
    )


type ServiceConditionNode = ServiceStateChoiceCondition


@api_model(slots=False)
class ServiceAndNode:
    type: Literal["and"] = api_field(
        description="Logical AND: all children must match", example="and"
    )
    children: Annotated[list["ServiceFilterNode"], MinLen(2)] = api_field(
        description="Child filter nodes",
        example=[
            ServiceStateChoiceCondition(type="condition", field="state", op="one_of", value=["OK"]),
            ServiceStateChoiceCondition(
                type="condition", field="state", op="one_of", value=["WARN"]
            ),
        ],
    )


@api_model(slots=False)
class ServiceOrNode:
    type: Literal["or"] = api_field(
        description="Logical OR: at least one child must match", example="or"
    )
    children: Annotated[list["ServiceFilterNode"], MinLen(2)] = api_field(
        description="Child filter nodes",
        example=[
            ServiceStateChoiceCondition(type="condition", field="state", op="one_of", value=["OK"]),
            ServiceStateChoiceCondition(
                type="condition", field="state", op="one_of", value=["WARN"]
            ),
        ],
    )


@api_model(slots=False)
class ServiceNotNode:
    type: Literal["not"] = api_field(
        description="Logical NOT: the child must not match", example="not"
    )
    child: "ServiceFilterNode" = api_field(description="Child filter node")


type ServiceFilterNode = ServiceAndNode | ServiceOrNode | ServiceNotNode | ServiceConditionNode


def parse_as_livestatus_filter(node: ServiceFilterNode) -> ServiceFilter:
    filters: list[str] = []
    _accumulate_filters(node, filters)
    return ServiceFilter("\n".join(str(LqSafe(f)) for f in filters))


def _accumulate_filters(node: ServiceFilterNode, filters: list[str]) -> None:
    match node:
        case ServiceStateChoiceCondition():
            for value in node.value:
                filters.append(f"Filter: {node.field} = {ServiceState[value]}")

            match node.op:
                case "one_of" if len(node.value) > 1:
                    filters.append(f"Or: {len(node.value)}")

        case ServiceAndNode() | ServiceOrNode():
            for child in node.children:
                _accumulate_filters(child, filters)

            match node.type:
                case "and":
                    filters.append(f"And: {len(node.children)}")
                case "or":
                    filters.append(f"Or: {len(node.children)}")

        case ServiceNotNode():
            _accumulate_filters(node.child, filters)
            filters.append("Negate:")
