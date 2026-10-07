#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Conversion of rule conditions between the REST API and the internal format."""

from collections.abc import Mapping, Sequence
from typing import Literal

from cmk.gui.openapi.api_endpoints.rule.models.request_models import (
    LabelGroupConditionRequestModel,
)
from cmk.gui.openapi.api_endpoints.rule.models.response_models import (
    LabelConditionModel,
    LabelGroupConditionModel,
    MatchExpressionModel,
    TagConditionCollectionModel,
    TagConditionModel,
    TagConditionScalarModel,
)
from cmk.gui.openapi.utils import RestAPIRequestDataValidationException
from cmk.ruleset_matcher.conditions import (
    HostOrServiceConditionRegex,
    HostOrServiceConditions,
    HostOrServiceConditionsSimple,
)
from cmk.ruleset_matcher.labels import LabelGroups
from cmk.ruleset_matcher.matcher import (
    TagCondition,
    TagConditionNE,
    TagConditionNOR,
    TagConditionOR,
)
from cmk.ruleset_matcher.tags import TagGroupID, TagID


def _scalar_value(
    value: str | None, operator: Literal["is", "is_not"]
) -> TagID | None | TagConditionNE:
    """Construct a scalar internal tag value or the negation of it.

    >>> _scalar_value("foo", "is")
    'foo'
    >>> _scalar_value("foo", "is_not")
    {'$ne': 'foo'}
    """
    tag_id = TagID(value) if value is not None else None
    if operator == "is":
        return tag_id
    return {"$ne": tag_id}


def _collection_value(
    value: Sequence[str | None], operator: Literal["one_of", "none_of"]
) -> TagConditionOR | TagConditionNOR:
    """Construct a collection internal tag value.

    >>> _collection_value(["Beavis", "Butthead"], "one_of")
    {'$or': ['Beavis', 'Butthead']}
    >>> _collection_value(["Beavis", "Butthead"], "none_of")
    {'$nor': ['Beavis', 'Butthead']}
    """
    tag_ids = [TagID(v) if v is not None else None for v in value]
    if operator == "one_of":
        return {"$or": tag_ids}
    return {"$nor": tag_ids}


def host_tags_to_internal(
    host_tags: Sequence[TagConditionModel],
) -> dict[TagGroupID, TagCondition]:
    """Convert the API host-tag list into the internal dict keyed by tag name."""
    result: dict[TagGroupID, TagCondition] = {}
    for cond in host_tags:
        key = TagGroupID(cond.key)
        if key in result:
            raise RestAPIRequestDataValidationException(
                title="Invalid condition.",
                detail=f"Key {cond.key!r} may only appear once!",
            )
        if isinstance(cond, TagConditionCollectionModel):
            result[key] = _collection_value(cond.value, cond.operator)
        else:
            result[key] = _scalar_value(cond.value, cond.operator)
    return result


def host_tags_to_api(host_tags: Mapping[TagGroupID, TagCondition]) -> list[TagConditionModel]:
    """Convert the internal host-tag dict into the API list."""
    result: list[TagConditionModel] = []
    for key, value in host_tags.items():
        match value:
            case None | str():
                result.append(TagConditionScalarModel(key=key, operator="is", value=value))
            case {"$ne": str() | None as negated}:
                result.append(TagConditionScalarModel(key=key, operator="is_not", value=negated))
            case {"$or": list() as values}:
                result.append(TagConditionCollectionModel(key=key, operator="one_of", value=values))
            case {"$nor": list() as values}:
                result.append(
                    TagConditionCollectionModel(key=key, operator="none_of", value=values)
                )
            case _:
                raise RestAPIRequestDataValidationException(
                    title="Invalid condition.",
                    detail=f"Unsupported tag condition for {key!r}: {value!r}",
                )
    return result


def _wrap_adaptive(entry: str) -> HostOrServiceConditionRegex | str:
    if entry and entry[0] == "~":
        return {"$regex": f"^{entry[1:]}"}
    return entry


def match_expr_to_internal(
    model: MatchExpressionModel, use_regex: Literal["always", "adaptive"]
) -> HostOrServiceConditions:
    """Convert an API match expression into the internal host/service condition."""
    match_on: HostOrServiceConditionsSimple
    if use_regex == "always":
        match_on = [{"$regex": entry} for entry in model.match_on]
    else:
        match_on = [_wrap_adaptive(entry) for entry in model.match_on]

    if model.operator == "one_of":
        return match_on
    return {"$nor": match_on}


def _unwrap_regex(
    entry: HostOrServiceConditionRegex | str, use_regex: Literal["always", "adaptive"]
) -> str:
    if isinstance(entry, dict):
        regex = entry["$regex"]
        if use_regex == "adaptive" and regex:
            return "~" + (regex[1:] if regex[0] == "^" else regex)
        return regex
    return entry


def match_expr_to_api(
    data: HostOrServiceConditions | None, use_regex: Literal["always", "adaptive"]
) -> MatchExpressionModel | None:
    """Convert the internal host/service condition into an API match expression."""
    operator: Literal["one_of", "none_of"]
    entries: HostOrServiceConditionsSimple
    match data:
        case None:
            return None
        case {"$nor": list() as entries}:
            operator = "none_of"
        case list() as entries:
            operator = "one_of"
        case _:
            return None

    return MatchExpressionModel(
        match_on=[_unwrap_regex(entry, use_regex) for entry in entries],
        operator=operator,
    )


def label_groups_to_internal(
    groups: Sequence[LabelGroupConditionRequestModel] | None,
) -> LabelGroups | None:
    """Convert API label groups into the internal label-group format.

    >>> from cmk.gui.openapi.api_endpoints.rule.models.request_models import (
    ...     LabelConditionRequestModel, LabelGroupConditionRequestModel)
    >>> label_groups_to_internal(
    ...     [LabelGroupConditionRequestModel(operator="and",
    ...         label_group=[LabelConditionRequestModel(operator="and", label="os:windows")])])
    [('and', [('and', 'os:windows')])]
    """
    if groups is None:
        return None
    return [
        (group.operator, [(cond.operator, cond.label) for cond in group.label_group])
        for group in groups
    ]


def label_groups_to_api(label_groups: LabelGroups) -> list[LabelGroupConditionModel]:
    """Convert internal label groups into the API label-group format."""
    return [
        LabelGroupConditionModel(
            operator=group_op,
            label_group=[
                LabelConditionModel(operator=op, label=label) for op, label in label_group
            ],
        )
        for group_op, label_group in label_groups
    ]
