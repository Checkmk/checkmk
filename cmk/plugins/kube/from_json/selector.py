# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Mapping, Sequence
from typing import cast, Literal, TypedDict

from ..schemata import api
from ..transform_any import parse_match_labels


class JSONSelectorRequirement(TypedDict):
    key: str
    operator: str
    values: Sequence[str] | None


class JSONSelector(TypedDict, total=False):
    matchLabels: Mapping[str, str]
    matchExpressions: Sequence[JSONSelectorRequirement]


def _parse_match_expression_from_json(
    match_expressions: Iterable[JSONSelectorRequirement] | None,
) -> api.MatchExpressions:
    return [
        api.MatchExpression(
            key=api.LabelName(expression["key"]),
            operator=cast(Literal["In", "NotIn", "Exists", "DoesNotExist"], expression["operator"]),
            values=[api.LabelValue(v) for v in expression["values"] or []],
        )
        for expression in match_expressions or []
    ]


def _selector_from_json(selector: JSONSelector) -> api.Selector:
    return api.Selector(
        match_labels=parse_match_labels(selector.get("matchLabels", {})),
        match_expressions=_parse_match_expression_from_json(selector.get("matchExpressions", [])),
    )
