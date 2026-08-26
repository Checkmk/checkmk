#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from collections.abc import Mapping
from typing import Annotated, Literal

from annotated_types import MinLen
from pydantic import AfterValidator, PlainValidator, StringConstraints

from cmk.gui.config import active_config
from cmk.gui.openapi.framework.model import api_field, api_model
from cmk.gui.utils.labels import encode_label_for_livestatus, Label
from cmk.livestatus_client import lqencode, quote_dict
from cmk.livestatus_client.expressions import LqSafe

from .._models import ServiceFilter, ServiceState, ServiceStateLabel
from ._validators import validate_label_pairs, validate_uniqueness, validate_unix_timestamp

# NOTE: these models are named with a "Service" prefix (unlike their hosts counterparts) because
# the OpenAPI spec registers component schemas by class name across every endpoint family; an
# unprefixed name would collide with the identically-shaped, but differently-fielded, hosts filter
# models.

_NO_NEWLINES_REGEX = r"^[^\n]*$"

_LABEL_SEPARATOR = ":"

_WILDCARD = "*"

# The names of a dict column live in a list column of their own, which is what a
# key with no value has to be matched against.
_LABEL_NAME_COLUMNS = {"labels": "label_names", "tags": "tag_names"}

type ServiceStringOp = Literal["contains", "matches"]

type ServiceLabelField = Literal["labels", "tags"]

type ServiceNameListField = Literal["contacts", "contact_groups"]

type ServiceTimestampOp = Literal["lt", "lte", "gt", "gte"]


@api_model
class ServiceStringCondition:
    type: Literal["condition"] = api_field(
        description="Node type discriminator", example="condition"
    )
    field: Literal["name", "summary", "contacts"] = api_field(
        description="String service field to filter on", example="name"
    )
    op: ServiceStringOp = api_field(description="String match operation", example="contains")
    value: str = api_field(
        description="Value to match against the field", example="CPU", pattern=_NO_NEWLINES_REGEX
    )


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


@api_model
class ServiceBooleanCondition:
    type: Literal["condition"] = api_field(
        description="Node type discriminator", example="condition"
    )
    field: Literal[
        "acknowledged", "in_downtime", "notifications_enabled", "is_flapping", "stale"
    ] = api_field(description="Boolean service field to filter on", example="acknowledged")
    op: Literal["eq"] = api_field(description="Equality operation", example="eq")
    value: bool = api_field(description="Boolean value to compare against", example=False)


@api_model
class ServiceTimestampCondition:
    type: Literal["condition"] = api_field(
        description="Node type discriminator", example="condition"
    )
    field: Literal["last_check", "last_state_change"] = api_field(
        description="Timestamp service field to filter on", example="last_check"
    )
    op: ServiceTimestampOp = api_field(description="Timestamp comparison operation", example="gte")
    value: Annotated[
        int, PlainValidator(func=validate_unix_timestamp, json_schema_input_type=int)
    ] = api_field(
        description=(
            "Unix timestamp to compare against, in whole seconds since the epoch (UTC). "
            "Formatted timestamps such as ISO-8601 strings are not accepted."
        ),
        example=1752405510,
    )


@api_model
class ServiceLabelChoiceCondition:
    type: Literal["condition"] = api_field(
        description="Node type discriminator", example="condition"
    )
    field: ServiceLabelField = api_field(
        description="Key/value service field to filter on", example="labels"
    )
    op: Literal["one_of"] = api_field(description="Set membership operation", example="one_of")
    value: Annotated[
        list[str],
        MinLen(1),
        AfterValidator(validate_uniqueness),
        AfterValidator(validate_label_pairs),
    ] = api_field(
        description=(
            "Pairs to match, each written as 'key:value'. A service matches when it carries "
            "any one of them. The first colon separates the two halves, so a value may contain "
            "colons. A trailing '*' matches by prefix: 'key:va*' takes every value of that key "
            "starting with 'va', 'ke*' every key starting with 'ke', whatever its value."
        ),
        example=["cmk/os_family:linux"],
    )


@api_model
class ServiceNameChoiceCondition:
    type: Literal["condition"] = api_field(
        description="Node type discriminator", example="condition"
    )
    field: ServiceNameListField = api_field(
        description="List-valued service field to filter on", example="contact_groups"
    )
    op: Literal["one_of"] = api_field(description="Set membership operation", example="one_of")
    value: Annotated[
        list[Annotated[str, StringConstraints(pattern=_NO_NEWLINES_REGEX)]],
        MinLen(1),
        AfterValidator(validate_uniqueness),
    ] = api_field(
        description=(
            "Names to match. A service matches when the field holds any one of them. A trailing "
            "'*' matches by prefix."
        ),
        example=["all"],
    )


type ServiceConditionNode = (
    ServiceStateChoiceCondition
    | ServiceStringCondition
    | ServiceBooleanCondition
    | ServiceTimestampCondition
    | ServiceLabelChoiceCondition
    | ServiceNameChoiceCondition
)


@api_model(slots=False)
class ServiceAndNode:
    type: Literal["and"] = api_field(
        description="Logical AND: all children must match", example="and"
    )
    children: Annotated[list[ServiceFilterNode], MinLen(2)] = api_field(
        description="Child filter nodes",
        example=[
            ServiceStringCondition(type="condition", field="name", op="contains", value="CPU"),
            ServiceStateChoiceCondition(type="condition", field="state", op="one_of", value=["OK"]),
        ],
    )


@api_model(slots=False)
class ServiceOrNode:
    type: Literal["or"] = api_field(
        description="Logical OR: at least one child must match", example="or"
    )
    children: Annotated[list[ServiceFilterNode], MinLen(2)] = api_field(
        description="Child filter nodes",
        example=[
            ServiceStringCondition(type="condition", field="name", op="contains", value="CPU"),
            ServiceStateChoiceCondition(type="condition", field="state", op="one_of", value=["OK"]),
        ],
    )


@api_model(slots=False)
class ServiceNotNode:
    type: Literal["not"] = api_field(
        description="Logical NOT: the child must not match", example="not"
    )
    child: ServiceFilterNode = api_field(description="Child filter node")


type ServiceFilterNode = ServiceAndNode | ServiceOrNode | ServiceNotNode | ServiceConditionNode


def parse_as_livestatus_filter(node: ServiceFilterNode) -> ServiceFilter:
    filters: list[str] = []
    _accumulate_filters(node, filters)
    return ServiceFilter("\n".join(str(LqSafe(f)) for f in filters))


def _anchored(prefix: str) -> str:
    return f"^{re.escape(prefix)}"


def _label_choice_filters(field: str, pairs: list[str]) -> list[str]:
    lines: list[str] = []
    for pair in pairs:
        key, separator, value = pair.partition(_LABEL_SEPARATOR)
        if not separator:
            column = _LABEL_NAME_COLUMNS[field]
            lines.append(f"Filter: {column} ~ {lqencode(_anchored(key.removesuffix(_WILDCARD)))}")
        elif value.endswith(_WILDCARD):
            lines.append(
                f"Filter: {lqencode(field)} ~ {lqencode(quote_dict(key))} "
                f"{lqencode(quote_dict(_anchored(value.removesuffix(_WILDCARD))))}"
            )
        else:
            lines.append(encode_label_for_livestatus(field, Label(key, value, False)))
    return lines


def _name_choice_filters(field: str, names: list[str]) -> list[str]:
    return [
        (
            f"Filter: {field} ~ {lqencode(_anchored(name.removesuffix(_WILDCARD)))}"
            if name.endswith(_WILDCARD)
            else f"Filter: {field} >= {lqencode(name)}"
        )
        for name in names
    ]


def _accumulate_filters(node: ServiceFilterNode, filters: list[str]) -> None:
    match node:
        case ServiceStringCondition():
            column = _LIVESTATUS_FIELD_OVERRIDES.get(node.field, node.field)
            filters.append(f"Filter: {column} {_STRING_OP_TO_LS[node.op]} {node.value}")

        case ServiceStateChoiceCondition():
            for value in node.value:
                filters.append(f"Filter: {node.field} = {ServiceState[value]}")

            match node.op:
                case "one_of" if len(node.value) > 1:
                    filters.append(f"Or: {len(node.value)}")

        case ServiceTimestampCondition():
            filters.append(f"Filter: {node.field} {_TIMESTAMP_OP_TO_LS[node.op]} {node.value}")

        case ServiceBooleanCondition():
            match node.field:
                case "in_downtime":
                    # Livestatus has no boolean downtime column; a service is in a scheduled
                    # downtime when scheduled_downtime_depth is greater than zero.
                    op = ">" if node.value else "="
                    filters.append(f"Filter: scheduled_downtime_depth {op} 0")
                case "stale":
                    # Livestatus has no boolean stale column; a service is stale when its
                    # staleness exceeds the configured threshold.
                    op = ">=" if node.value else "<"
                    filters.append(f"Filter: staleness {op} {active_config.staleness_threshold}")
                case _:
                    filters.append(f"Filter: {node.field} = {int(node.value)}")

        case ServiceLabelChoiceCondition():
            filters.extend(_label_choice_filters(node.field, node.value))

            if len(node.value) > 1:
                filters.append(f"Or: {len(node.value)}")

        case ServiceNameChoiceCondition():
            filters.extend(_name_choice_filters(node.field, node.value))

            if len(node.value) > 1:
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


_STRING_OP_TO_LS = {
    "contains": "~~",
    "matches": "~",
}
_TIMESTAMP_OP_TO_LS = {
    "lt": "<",
    "lte": "<=",
    "gt": ">",
    "gte": ">=",
}
# The domain names these fields after what the table shows, which for some of them differs from
# the livestatus column they are read from.
_LIVESTATUS_FIELD_OVERRIDES: Mapping[str, str] = {
    "name": "description",
    "summary": "plugin_output",
}
