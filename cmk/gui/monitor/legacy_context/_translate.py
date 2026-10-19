#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from cmk.ccc.site import SiteId
from cmk.gui.type_defs import FilterHTTPVariables, FilterName, VisualContext

IGNORED_TRISTATE = "-1"


class UntranslatableFilterError(Exception):
    pass


@dataclass(frozen=True)
class ContextFilterTranslation[N]:
    node: N | None
    unapplied: Sequence[FilterName]


class FilterNodeFactory[N](ABC):
    @abstractmethod
    def all_of(self, nodes: Sequence[N]) -> N: ...

    @abstractmethod
    def site_choice(self, site_ids: Sequence[SiteId]) -> N: ...

    def combined(self, nodes: Sequence[N]) -> N | None:
        match nodes:
            case []:
                return None
            case [single]:
                return single
            case _:
                return self.all_of(nodes)


class ContextFilter[N](ABC):
    @abstractmethod
    def node(self, value: FilterHTTPVariables) -> N | None: ...


class ContextFilterTranslator[N]:
    _SITE_FILTERS: Sequence[FilterName] = ("sites", "site", "siteopt")

    def __init__(
        self, filters: Mapping[FilterName, ContextFilter[N]], nodes: FilterNodeFactory[N]
    ) -> None:
        self._filters = filters
        self._nodes = nodes

    def translate(self, context: VisualContext) -> ContextFilterTranslation[N]:
        nodes: list[N] = []
        unapplied: list[FilterName] = []
        if (site_node := self._site_node(context)) is not None:
            nodes.append(site_node)
        for name, value in context.items():
            if name in self._SITE_FILTERS or not self._is_set(value):
                continue
            if (context_filter := self._filters.get(name)) is None or self._spans_lines(value):
                unapplied.append(name)
                continue
            try:
                node = context_filter.node(value)
            except UntranslatableFilterError:
                unapplied.append(name)
                continue
            if node is not None:
                nodes.append(node)
        return ContextFilterTranslation(node=self._nodes.combined(nodes), unapplied=unapplied)

    def _site_node(self, context: VisualContext) -> N | None:
        if sites := context.get("sites", {}).get("sites", "").strip():
            site_ids = [SiteId(site) for site in dict.fromkeys(sites.split("|")) if site]
        else:
            site_ids = [
                SiteId(site)
                for name in ("site", "siteopt")
                if (site := context.get(name, {}).get("site"))
            ][:1]
        if not site_ids:
            return None
        return self._nodes.site_choice(site_ids)

    @staticmethod
    def _spans_lines(value: FilterHTTPVariables) -> bool:
        return any("\n" in text for text in value.values())

    @staticmethod
    def _is_set(value: FilterHTTPVariables) -> bool:
        return any(text and text != IGNORED_TRISTATE for text in value.values())
