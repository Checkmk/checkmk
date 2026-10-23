#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from collections.abc import Callable, Mapping
from typing import Annotated, assert_never, Final, Literal

from annotated_types import MinLen
from pydantic import AfterValidator, PlainValidator, StringConstraints, TypeAdapter

from cmk.ccc.site import SiteId
from cmk.gui.config import active_config
from cmk.gui.openapi.framework.model import api_field, api_model
from cmk.gui.utils.labels import encode_label_for_livestatus, Label
from cmk.livestatus_client import lqencode, quote_dict
from cmk.livestatus_client.expressions import LqSafe

from ._host_folders import folder_matching_filters
from ._host_state import HostState, HostStateLabel
from ._validators import validate_label_pairs, validate_uniqueness, validate_unix_timestamp

# TODO: look into whether we can utilize generics when generating our shared typing. It's not great
# that this functionality is tied to the field names or the state choice enum. This information
# would be ideally passed in the respective endpoint definitions.

_NO_NEWLINES_REGEX = r"^[^\n]*$"

_LABEL_SEPARATOR = ":"

_WILDCARD = "*"

# The names of a dict column live in a list column of their own, which is what a
# key with no value has to be matched against.
_LABEL_NAME_COLUMNS = {"labels": "label_names", "tags": "tag_names"}

type StringOp = Literal["contains", "matches"]

type NumericOp = Literal["lt", "lte", "eq", "gt", "gte"]

type TimestampOp = Literal["lt", "lte", "gt", "gte"]

type LabelField = Literal["labels", "tags"]

type NameListField = Literal["contacts", "contact_groups", "groups"]

type StringField = Literal["name", "alias", "address", "contacts"]

type BooleanField = Literal[
    "acknowledged",
    "in_downtime",
    "notifications_enabled",
    "has_comments",
    "active_checks_disabled",
    "passive_checks_disabled",
    "in_notification_period",
    "in_service_period",
    "in_check_period",
    "is_flapping",
    "stale",
]

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
    field: StringField = api_field(description="String host field to filter on", example="name")
    op: StringOp = api_field(description="String match operation", example="contains")
    value: str = api_field(
        description="Value to match against the field", example="web", pattern=_NO_NEWLINES_REGEX
    )


# Only "contains" is offered: it is what the funnel in the Folder column produces, and the value
# is matched against Setup's folder titles here rather than by Livestatus (see ``.._folder``).
@api_model
class FolderCondition:
    type: Literal["condition"] = api_field(
        description="Node type discriminator", example="condition"
    )
    field: Literal["folder"] = api_field(description="Setup folder field", example="folder")
    op: Literal["contains"] = api_field(description="Substring match operation", example="contains")
    value: str = api_field(
        description=(
            "Substring to look for in the folder title, as the Folder column shows it: the titles "
            "down to the folder, e.g. 'Data center Munich / Rack 1', and 'Main' for the root "
            "folder. A host whose folder Setup does not know - one not managed via Setup, or one "
            "a remote site owns - has no title and is never selected."
        ),
        example="Data center Munich",
        pattern=_NO_NEWLINES_REGEX,
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
        list[SiteId],
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
    field: BooleanField = api_field(
        description="Host boolean field to filter on", example="acknowledged"
    )
    op: Literal["eq"] = api_field(description="Equality operation", example="eq")
    value: bool = api_field(description="Boolean value to compare against", example=False)


@api_model
class LabelChoiceCondition:
    type: Literal["condition"] = api_field(
        description="Node type discriminator", example="condition"
    )
    field: LabelField = api_field(description="Key/value host field to filter on", example="labels")
    op: Literal["one_of", "all_of"] = api_field(
        description="Set membership operation", example="all_of"
    )
    value: Annotated[
        list[Annotated[str, StringConstraints(pattern=_NO_NEWLINES_REGEX)]],
        MinLen(1),
        AfterValidator(validate_uniqueness),
        AfterValidator(validate_label_pairs),
    ] = api_field(
        description=(
            "Pairs to match, each written as 'key:value'. With 'all_of' a host matches only "
            "when it carries every pair, with 'one_of' when it carries any one of them. The "
            "first colon separates the two halves, so a value may contain "
            "colons. A trailing '*' matches by prefix: 'key:va*' takes every value of that key "
            "starting with 'va', 'ke*' every key starting with 'ke', whatever its value."
        ),
        example=["cmk/os_family:linux"],
    )


@api_model
class NameChoiceCondition:
    type: Literal["condition"] = api_field(
        description="Node type discriminator", example="condition"
    )
    field: NameListField = api_field(
        description="List-valued host field to filter on", example="contact_groups"
    )
    op: Literal["one_of"] = api_field(description="Set membership operation", example="one_of")
    value: Annotated[
        list[Annotated[str, StringConstraints(pattern=_NO_NEWLINES_REGEX)]],
        MinLen(1),
        AfterValidator(validate_uniqueness),
    ] = api_field(
        description=(
            "Names to match. A host matches when the field holds any one of them. A trailing "
            "'*' matches by prefix."
        ),
        example=["all"],
    )


type ConditionNode = (
    StringCondition
    | FolderCondition
    | StateChoiceCondition
    | SiteChoiceCondition
    | NumericCondition
    | TimestampCondition
    | BooleanCondition
    | LabelChoiceCondition
    | NameChoiceCondition
)


@api_model(slots=False)
class AndNode:
    type: Literal["and"] = api_field(
        description="Logical AND: all children must match", example="and"
    )
    children: Annotated[list[FilterNode], MinLen(2)] = api_field(
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
    children: Annotated[list[FilterNode], MinLen(2)] = api_field(
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
    child: FilterNode = api_field(description="Child filter node")


type FilterNode = AndNode | OrNode | NotNode | ConditionNode

FILTER_NODE: Final = TypeAdapter[FilterNode](FilterNode)


def validate_host_columns_only(node: FilterNode) -> FilterNode:
    """Accept only the conditions that map 1:1 onto host columns, so that a new condition has to
    be added here before another table's filter tree takes it. 'site_id' restricts which sites are
    queried, and 'folder' is matched against Setup's folder titles."""
    match node:
        case (
            StringCondition()
            | StateChoiceCondition()
            | NumericCondition()
            | TimestampCondition()
            | BooleanCondition()
            | LabelChoiceCondition()
            | NameChoiceCondition()
        ):
            pass
        case SiteChoiceCondition() | FolderCondition():
            raise ValueError(f"A {node.field!r} condition is not supported here.")
        case AndNode() | OrNode():
            for child in node.children:
                validate_host_columns_only(child)
        case NotNode():
            validate_host_columns_only(node.child)
        case _:
            assert_never(node)
    return node


def _no_folders() -> Mapping[str, str]:
    return {}


def livestatus_filter_lines(
    node: FilterNode,
    *,
    setup_folders: Callable[[], Mapping[str, str]] = _no_folders,
    column_prefix: str = "",
) -> list[str]:
    """Render the filter tree as Livestatus filter lines, each column named with
    ``column_prefix``: "host_" filters a table that carries the host columns that way, e.g. the
    services table.

    A folder condition is matched against the folder titles ``setup_folders`` reads from Setup,
    which Livestatus does not know. It renders without a prefix only: no other table is filtered by
    the folder of its host, so it raises a ``ValueError`` there."""
    filters: list[str] = []
    _accumulate_filters(node, filters, setup_folders, column_prefix)
    return [str(LqSafe(f)) for f in filters]


def _anchored(start: str) -> str:
    return f"^{re.escape(start)}"


def _label_choice_filters(field: str, pairs: list[str], column_prefix: str) -> list[str]:
    lines: list[str] = []
    for pair in pairs:
        key, separator, value = pair.partition(_LABEL_SEPARATOR)
        if not separator:
            column = _LABEL_NAME_COLUMNS[field]
            lines.append(
                f"Filter: {column_prefix}{column} ~ {lqencode(_anchored(key.removesuffix(_WILDCARD)))}"
            )
        elif value.endswith(_WILDCARD):
            lines.append(
                f"Filter: {lqencode(column_prefix + field)} ~ {lqencode(quote_dict(key))} "
                f"{lqencode(quote_dict(_anchored(value.removesuffix(_WILDCARD))))}"
            )
        else:
            lines.append(
                encode_label_for_livestatus(column_prefix + field, Label(key, value, False))
            )
    return lines


def _name_choice_filters(field: str, names: list[str], column_prefix: str) -> list[str]:
    return [
        (
            f"Filter: {column_prefix}{field} ~ {lqencode(_anchored(name.removesuffix(_WILDCARD)))}"
            if name.endswith(_WILDCARD)
            else f"Filter: {column_prefix}{field} >= {lqencode(name)}"
        )
        for name in names
    ]


def _manually_disabled_filters(
    attribute: str, column_prefix: str, *, column: str | None = None
) -> list[str]:
    """Match objects whose ``attribute`` a user switched off, not ones that never had it on.

    Mirrors the repository's own derivation: the setting being 0 is not enough, the attribute
    also has to appear in the modified-attributes list. Pass ``column`` where the setting's own
    column is named differently from the modified attribute.
    """
    return [
        f"Filter: {column_prefix}modified_attributes_list >= {attribute}",
        f"Filter: {column_prefix}{column or attribute} = 0",
        "And: 2",
    ]


def _accumulate_filters(
    node: FilterNode,
    filters: list[str],
    setup_folders: Callable[[], Mapping[str, str]],
    column_prefix: str,
) -> None:
    match node:
        case StringCondition():
            filters.append(
                f"Filter: {column_prefix}{node.field} {_STRING_OP_TO_LS[node.op]} {node.value}"
            )

        case FolderCondition():
            if column_prefix:
                raise ValueError("A folder condition only filters the hosts table.")
            # A folder is not a Livestatus column; it is named by the host's config file.
            filters.extend(folder_matching_filters(node.value, setup_folders()))

        case NumericCondition():
            filters.append(
                f"Filter: {column_prefix}{node.field} {_NUMERIC_OP_TO_LS[node.op]} {node.value}"
            )

        case TimestampCondition():
            filters.append(
                f"Filter: {column_prefix}{node.field} {_TIMESTAMP_OP_TO_LS[node.op]} {node.value}"
            )

        case BooleanCondition():
            match node.field:
                case "in_downtime":
                    # Livestatus has no boolean downtime column; a host is in a scheduled
                    # downtime when scheduled_downtime_depth is greater than zero.
                    op = ">" if node.value else "="
                    filters.append(f"Filter: {column_prefix}scheduled_downtime_depth {op} 0")
                case "has_comments":
                    # Livestatus has no comment count; the comment id list is filterable for
                    # emptiness alone, which is exactly the question the icon answers.
                    op = "!=" if node.value else "="
                    filters.append(f"Filter: {column_prefix}comments {op}")
                case "active_checks_disabled":
                    filters.extend(
                        _manually_disabled_filters("active_checks_enabled", column_prefix)
                    )
                    if not node.value:
                        filters.append("Negate:")
                case "passive_checks_disabled":
                    filters.extend(
                        _manually_disabled_filters(
                            "passive_checks_enabled", column_prefix, column="accept_passive_checks"
                        )
                    )
                    if not node.value:
                        filters.append("Negate:")
                case "stale":
                    # Livestatus has no boolean stale column; a host is stale when its
                    # staleness exceeds the configured threshold.
                    op = ">=" if node.value else "<"
                    filters.append(
                        f"Filter: {column_prefix}staleness {op} {active_config.staleness_threshold}"
                    )
                case _:
                    filters.append(f"Filter: {column_prefix}{node.field} = {int(node.value)}")

        case StateChoiceCondition():
            clauses = [
                _state_choice_clause(node.field, value, column_prefix) for value in node.value
            ]
            for clause in clauses:
                filters.extend(clause)

            match node.op:
                case "one_of" if len(clauses) > 1:
                    filters.append(f"Or: {len(clauses)}")

        case LabelChoiceCondition():
            filters.extend(_label_choice_filters(node.field, node.value, column_prefix))

            match node.op:
                case "one_of" if len(node.value) > 1:
                    filters.append(f"Or: {len(node.value)}")
                case "all_of" if len(node.value) > 1:
                    filters.append(f"And: {len(node.value)}")

        case NameChoiceCondition():
            filters.extend(_name_choice_filters(node.field, node.value, column_prefix))

            if len(node.value) > 1:
                filters.append(f"Or: {len(node.value)}")

        case SiteChoiceCondition():
            raise AssertionError("Site conditions are not fully supported as filter nodes.")

        case AndNode() | OrNode():
            for child in node.children:
                _accumulate_filters(child, filters, setup_folders, column_prefix)

            match node.type:
                case "and":
                    filters.append(f"And: {len(node.children)}")
                case "or":
                    filters.append(f"Or: {len(node.children)}")

        case NotNode():
            _accumulate_filters(node.child, filters, setup_folders, column_prefix)
            filters.append("Negate:")


def _state_choice_clause(field: str, value: HostStateLabel, column_prefix: str) -> list[str]:
    """A pending host's raw ``state`` column is meaningless (always 0, coinciding with UP), so
    'PENDING' is matched on ``has_been_checked`` instead, and every other state excludes pending
    hosts the same way rather than silently bucketing them in with a real state."""
    if value == "PENDING":
        return [f"Filter: {column_prefix}has_been_checked = 0"]
    return [
        f"Filter: {column_prefix}{field} = {HostState[value]}",
        f"Filter: {column_prefix}has_been_checked = 1",
        "And: 2",
    ]


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
