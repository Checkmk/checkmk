#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Turn a global search spec (see ``cmk.gui.search.spec``) into the All services filter tree

Each clause of the spec becomes one condition on the top level of the tree, so the column filters
show it. Labels are the exception: a column filter shows only one condition per field, so their
clauses become a single "all_of" condition, which filters the same.
"""

from collections.abc import Sequence
from typing import Literal

from cmk.gui.i18n import _
from cmk.gui.search.spec import (
    HostName,
    PrefixedSearch,
    ServiceGroup,
    ServiceLabel,
    ServiceName,
    ServiceState,
    ServiceStateName,
    Term,
    UnsupportedSearchError,
)

from ._api._filters import (
    ServiceAndNode,
    ServiceFilterNode,
    ServiceLabelChoiceCondition,
    ServiceNameChoiceCondition,
    ServiceStateChoiceCondition,
    ServiceStringCondition,
)
from ._models import ServiceStateLabel

_STATE_LABELS: dict[ServiceStateName, ServiceStateLabel] = {
    "ok": "OK",
    "warn": "WARN",
    "crit": "CRIT",
    "unkn": "UNKNOWN",
    "pend": "PENDING",
}


def service_search_filter(spec: PrefixedSearch) -> ServiceFilterNode:
    """The All services filter tree for the spec

    Raises:
        UnsupportedSearchError: if All services can't filter on the spec.
    """
    conditions: list[ServiceFilterNode | None] = []
    labels: dict[str, None] = {}
    for clause in spec.clauses:
        match clause:
            case [ServiceLabel(key=key, value=value)]:
                if not labels:
                    conditions.append(None)
                labels[key if value is None else f"{key}:{value}"] = None
            case _:
                conditions.append(_condition(clause))

    nodes = [
        ServiceLabelChoiceCondition(
            type="condition", field="labels", op="all_of", value=list(labels)
        )
        if node is None
        else node
        for node in conditions
    ]
    return nodes[0] if len(nodes) == 1 else ServiceAndNode(type="and", children=nodes)


def _condition(clause: Sequence[Term]) -> ServiceFilterNode:
    match clause:
        case [ServiceName(), *_]:
            return _contains("name", [t.pattern for t in clause if isinstance(t, ServiceName)])
        case [HostName(), *_]:
            return _contains("host_name", [t.pattern for t in clause if isinstance(t, HostName)])
        case [ServiceState(), *_]:
            return ServiceStateChoiceCondition(
                type="condition",
                field="state",
                op="one_of",
                value=list(
                    dict.fromkeys(
                        _STATE_LABELS[t.state] for t in clause if isinstance(t, ServiceState)
                    )
                ),
            )
        case [ServiceGroup(), *_]:
            return ServiceNameChoiceCondition(
                type="condition",
                field="groups",
                op="one_of",
                value=list(dict.fromkeys(t.name for t in clause if isinstance(t, ServiceGroup))),
            )
        case _:
            raise UnsupportedSearchError(
                _(
                    "All services can only be searched by host name, service name, state, label"
                    " and group."
                )
            )


def _contains(
    field: Literal["name", "host_name"], patterns: Sequence[str]
) -> ServiceStringCondition:
    return ServiceStringCondition(
        type="condition", field=field, op="contains", value="|".join(patterns)
    )
