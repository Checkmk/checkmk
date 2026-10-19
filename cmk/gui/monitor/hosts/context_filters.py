#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from collections.abc import Mapping, Sequence
from typing import override

from cmk.ccc.site import SiteId
from cmk.gui.monitor.legacy_context import (
    ContextFilter,
    ContextFilterTranslation,
    ContextFilterTranslator,
    FilterNodeFactory,
    IGNORED_TRISTATE,
    UntranslatableFilterError,
)
from cmk.gui.type_defs import FilterHTTPVariables, FilterName, VisualContext

from ._api._filters import (
    AndNode,
    BooleanCondition,
    BooleanField,
    FilterNode,
    NameChoiceCondition,
    NameListField,
    NotNode,
    NumericCondition,
    NumericField,
    NumericOp,
    SiteChoiceCondition,
    StateChoiceCondition,
    StringCondition,
    StringField,
)
from ._models import HostStateLabel


class _HostFilterNodes(FilterNodeFactory[FilterNode]):
    @override
    def all_of(self, nodes: Sequence[FilterNode]) -> FilterNode:
        return AndNode(type="and", children=list(nodes))

    @override
    def site_choice(self, site_ids: Sequence[SiteId]) -> FilterNode:
        return SiteChoiceCondition(
            type="condition", field="site_id", op="one_of", value=list(site_ids)
        )


_HOST_FILTER_NODES = _HostFilterNodes()


class _TextFilter(ContextFilter[FilterNode]):
    def __init__(
        self,
        request_var: str,
        field: StringField,
        *,
        exact: bool = False,
    ) -> None:
        self._request_var = request_var
        self._field = field
        self._exact = exact

    @override
    def node(self, value: FilterHTTPVariables) -> FilterNode | None:
        if not (text := value.get(self._request_var, "")):
            return None
        if not self._exact:
            self._ensure_valid_regex(text)
        condition = StringCondition(
            type="condition",
            field=self._field,
            op="matches" if self._exact else "contains",
            value=f"^{re.escape(text)}$" if self._exact else text,
        )
        if value.get(f"neg_{self._request_var}"):
            return NotNode(type="not", child=condition)
        return condition

    @staticmethod
    def _ensure_valid_regex(text: str) -> None:
        # Best effort: Livestatus matches with RE2, so a pattern only RE2 rejects (e.g. a
        # lookahead or a backreference) still passes here and fails in the query.
        try:
            re.compile(text)
        except re.error as exc:
            raise UntranslatableFilterError from exc


class _AddressFilter(ContextFilter[FilterNode]):
    @override
    def node(self, value: FilterHTTPVariables) -> FilterNode | None:
        if not (address := value.get("host_address", "")):
            return None
        prefix = value.get("host_address_prefix") == "yes"
        return StringCondition(
            type="condition",
            field="address",
            op="matches",
            value=f"^{re.escape(address)}" if prefix else f"^{re.escape(address)}$",
        )


class _NameChoiceFilter(ContextFilter[FilterNode]):
    def __init__(self, request_var: str, field: NameListField, *, separator: str | None) -> None:
        self._request_var = request_var
        self._field: NameListField = field
        self._separator = separator

    @override
    def node(self, value: FilterHTTPVariables) -> FilterNode | None:
        if not (text := value.get(self._request_var, "").strip()):
            return None
        names = text.split(self._separator) if self._separator else [text]
        if any(name.endswith("*") for name in names):
            raise UntranslatableFilterError
        condition = NameChoiceCondition(
            type="condition", field=self._field, op="one_of", value=list(dict.fromkeys(names))
        )
        if value.get(f"neg_{self._request_var}"):
            return NotNode(type="not", child=condition)
        return condition


class _FlagFilter(ContextFilter[FilterNode]):
    def __init__(self, request_var: str, field: BooleanField) -> None:
        self._request_var = request_var
        self._field = field

    @override
    def node(self, value: FilterHTTPVariables) -> FilterNode | None:
        pick = value.get(self._request_var, IGNORED_TRISTATE)
        if pick not in ("0", "1"):
            return None
        return BooleanCondition(
            type="condition",
            field=self._field,
            op="eq",
            value=pick == "1",
        )


class _StateFilter(ContextFilter[FilterNode]):
    _STATES: Mapping[str, HostStateLabel] = {
        "hst0": "UP",
        "hst1": "DOWN",
        "hst2": "UNREACHABLE",
        "hstp": "PENDING",
    }

    @override
    def node(self, value: FilterHTTPVariables) -> FilterNode | None:
        picked = [state for var, state in self._STATES.items() if value.get(var)]
        if not picked or len(picked) == len(self._STATES):
            return None
        return StateChoiceCondition(type="condition", field="state", op="one_of", value=picked)


class _NumberRangeFilter(ContextFilter[FilterNode]):
    _BOUNDS: Sequence[tuple[NumericOp, str]] = (("gte", "_from"), ("lte", "_until"))

    def __init__(self, ident: str, field: NumericField) -> None:
        self._ident = ident
        self._field = field

    @override
    def node(self, value: FilterHTTPVariables) -> FilterNode | None:
        bounds = [
            NumericCondition(
                type="condition",
                field=self._field,
                op=op,
                value=bound,
            )
            for op, suffix in self._BOUNDS
            if (bound := self._bound(value.get(f"{self._ident}{suffix}", ""))) is not None
        ]
        return _HOST_FILTER_NODES.combined(bounds)

    @staticmethod
    def _bound(text: str) -> int | None:
        if not text:
            return None
        try:
            return int(text)
        except ValueError as exc:
            raise UntranslatableFilterError from exc


_CONTEXT_FILTERS: Mapping[FilterName, ContextFilter[FilterNode]] = {
    "host": _TextFilter("host", "name", exact=True),
    "hostregex": _TextFilter("host_regex", "name"),
    "hostalias": _TextFilter("hostalias", "alias"),
    "host_address": _AddressFilter(),
    "host_ctc": _NameChoiceFilter("host_ctc", "contacts", separator=None),
    "opthost_contactgroup": _NameChoiceFilter(
        "opthost_contact_group", "contact_groups", separator="|"
    ),
    "hoststate": _StateFilter(),
    "host_staleness": _FlagFilter("is_host_staleness", "stale"),
    "host_acknowledged": _FlagFilter("is_host_acknowledged", "acknowledged"),
    "host_notifications_enabled": _FlagFilter(
        "is_host_notifications_enabled", "notifications_enabled"
    ),
    "host_in_notification_period": _FlagFilter(
        "is_host_in_notification_period", "in_notification_period"
    ),
    "host_in_service_period": _FlagFilter("is_host_in_service_period", "in_service_period"),
    "host_scheduled_downtime_depth": _FlagFilter("is_host_scheduled_downtime_depth", "in_downtime"),
    "host_num_services": _NumberRangeFilter("host_num_services", "num_services"),
}


class HostContextFilters:
    _TRANSLATOR = ContextFilterTranslator(_CONTEXT_FILTERS, _HOST_FILTER_NODES)

    @classmethod
    def translate(cls, context: VisualContext) -> ContextFilterTranslation[FilterNode]:
        return cls._TRANSLATOR.translate(context)
