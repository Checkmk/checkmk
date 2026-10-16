#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from typing import override

from cmk.ccc.site import SiteId
from cmk.gui.monitor.table_widget import (
    ContextFilter,
    ContextFilterTranslation,
    ContextFilterTranslator,
    FilterNodeFactory,
    UntranslatableFilterError,
)
from cmk.gui.type_defs import FilterHTTPVariables


class _TextNodes(FilterNodeFactory[str]):
    @override
    def all_of(self, nodes: Sequence[str]) -> str:
        return " & ".join(nodes)

    @override
    def site_choice(self, site_ids: Sequence[SiteId]) -> str:
        return f"site in {','.join(site_ids)}"


class _EqualsFilter(ContextFilter[str]):
    def __init__(self, request_var: str) -> None:
        self._request_var = request_var

    @override
    def node(self, value: FilterHTTPVariables) -> str | None:
        if (text := value.get(self._request_var, "")) == "invalid":
            raise UntranslatableFilterError
        return f"{self._request_var} = {text}"


_TRANSLATOR = ContextFilterTranslator({"service": _EqualsFilter("service")}, _TextNodes())


def test_the_nodes_come_from_the_given_factory() -> None:
    translation = _TRANSLATOR.translate({"sites": {"sites": "a|b"}, "service": {"service": "CPU"}})

    assert translation == ContextFilterTranslation(node="site in a,b & service = CPU", unapplied=[])


def test_an_unknown_or_untranslatable_filter_is_reported_unapplied() -> None:
    translation = _TRANSLATOR.translate(
        {"hostregex": {"host_regex": "web"}, "service": {"service": "invalid"}}
    )

    assert translation == ContextFilterTranslation(node=None, unapplied=["hostregex", "service"])
