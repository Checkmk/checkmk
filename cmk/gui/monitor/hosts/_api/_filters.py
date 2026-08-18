#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Annotated, Literal

from annotated_types import MinLen
from pydantic import AfterValidator, PlainValidator

from cmk.ccc.site import SiteId
from cmk.gui.openapi.framework.model import api_field, api_model
from cmk.gui.openapi.framework.model.converter import SiteIdConverter, TypedPlainValidator
from cmk.livestatus_client.expressions import LqSafe

from .._models import HostFilter, HostState, HostStateLabel
from ._validators import validate_uniqueness, validate_unix_timestamp

# TODO: look into whether we can utilize generics when generating our shared typing. It's not great
# that this functionality is tied to the field names or the state choice enum. This information
# would be ideally passed in the respective endpoint definitions.

_NO_NEWLINES_REGEX = r"^[^\n]*$"

type StringOp = Literal["contains", "matches"]

type NumericOp = Literal["lt", "lte", "eq", "gt", "gte"]

type TimestampOp = Literal["lt", "lte", "gt", "gte"]

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
class SiteChoiceCondition:
    type: Literal["condition"] = api_field(
        description="Node type discriminator", example="condition"
    )
    field: Literal["site_id"] = api_field(description="Site field", example="site_id")
    op: Literal["one_of"] = api_field(description="Set membership operation", example="one_of")
    value: Annotated[
        list[Annotated[SiteId, TypedPlainValidator(str, SiteIdConverter.should_exist)]],
        MinLen(1),
        AfterValidator(validate_uniqueness),
    ] = api_field(description="Site IDs to match", example=["local"])


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
class TimestampCondition:
    type: Literal["condition"] = api_field(
        description="Node type discriminator", example="condition"
    )
    field: Literal["last_check", "last_state_change"] = api_field(
        description="Timestamp host field to filter on", example="last_check"
    )
    op: TimestampOp = api_field(description="Timestamp comparison operation", example="gte")
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
class BooleanCondition:
    type: Literal["condition"] = api_field(
        description="Node type discriminator", example="condition"
    )
    field: Literal["acknowledged", "in_downtime"] = api_field(
        description="Host boolean field to filter on", example="acknowledged"
    )
    op: Literal["eq"] = api_field(description="Equality operation", example="eq")
    value: bool = api_field(description="Boolean value to compare against", example=False)


type ConditionNode = (
    StringCondition
    | StateChoiceCondition
    | SiteChoiceCondition
    | NumericCondition
    | TimestampCondition
    | BooleanCondition
)


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


def extract_site_scope(
    node: FilterNode, all_site_ids: frozenset[SiteId]
) -> tuple[FilterNode | None, list[SiteId] | None]:
    """Split off the tree's 'site_id' condition, if any, as a site scope restriction.

    Site ID isn't a real Livestatus column, so it can't contribute a filter line; it's pushed
    down into which sites get queried instead. Only a single 'site_id' condition is supported,
    optionally wrapped with a 'not' condition. If a site condition is combined with the rest of
    the tree with anything but an 'and' condition, a `ValueError` is raised.

    Additional details:

    - Combining it with an unrelated condition via 'or' would need hosts from every other site
      too (e.g. "site A's hosts OR any DOWN host"), which can't be reduced to a site restriction.
    - Negating a mixed (site + non-site) subtree hits the same problem:
      NOT(site_id=A AND cond) = (site_id!=A OR NOT cond), which turns the 'and' into an 'or'.
    - The only one site condition is done to constrain the current parsing logic. This constraint
      can be lifted when the need arises, but will come with added complexity.
    """
    found: list[tuple[SiteChoiceCondition, bool]] = []

    def record(condition: SiteChoiceCondition, *, negated: bool, and_only: bool) -> None:
        if not and_only:
            raise ValueError(
                "'site_id' conditions may only be combined via 'and'; they cannot appear "
                "inside 'or', or inside 'not' together with other conditions."
            )
        if found:
            raise ValueError("Only one 'site_id' condition is allowed per filter.")
        found.append((condition, negated))

    def walk(current: FilterNode, and_only: bool) -> FilterNode | None:
        match current:
            case SiteChoiceCondition():
                record(current, negated=False, and_only=and_only)
                return None

            case NotNode(child=SiteChoiceCondition() as site_condition):
                record(site_condition, negated=True, and_only=and_only)
                return None

            case NotNode(child=child):
                # Passes through unchanged unless a 'site_id' condition turns up further inside,
                # which `and_only=False` rejects (see docstring: mixed-subtree negation).
                walk(child, and_only=False)
                return current

            case AndNode(children=children):
                residual_children = [
                    residual
                    for residual in (walk(child, and_only) for child in children)
                    if residual is not None
                ]
                match residual_children:
                    case []:
                        return None
                    case [single]:
                        return single
                    case _:
                        return AndNode(type="and", children=residual_children)

            case OrNode(children=children):
                # 'or' can never be reduced to a site restriction, so any 'site_id' condition
                # anywhere inside is rejected by `record`; nothing is ever extracted here.
                for child in children:
                    walk(child, and_only=False)
                return current

            case _:
                return current

    residual = walk(node, and_only=True)

    if not found:
        return residual, None

    condition, negated = found[0]
    extracted_site_ids = {SiteId(site_id) for site_id in condition.value}
    site_ids = list(all_site_ids - extracted_site_ids if negated else extracted_site_ids)

    return residual, site_ids


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

        case TimestampCondition():
            filters.append(f"Filter: {node.field} {_TIMESTAMP_OP_TO_LS[node.op]} {node.value}")

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

        case SiteChoiceCondition():
            raise AssertionError("Site conditions are not fully supported as filter nodes.")

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
_TIMESTAMP_OP_TO_LS = {
    "gt": ">",
    "gte": ">=",
    "lt": "<",
    "lte": "<=",
}
