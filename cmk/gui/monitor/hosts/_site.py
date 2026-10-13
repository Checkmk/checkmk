#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Decide which sites a table search names."""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from cmk.ccc.site import SiteId


@dataclass(frozen=True, kw_only=True)
class MonitorSite:
    id: SiteId
    customer: str | None = None

    def carries(self, needle: str) -> bool:
        return any(needle in shown.lower() for shown in (self.id, self.customer) if shown)


class MonitorSites:
    def __init__(self, sites: Iterable[MonitorSite] = ()) -> None:
        self._sites = tuple(sites)

    def matching(self, value: str) -> Sequence[SiteId]:
        needle = value.lower()
        return [site.id for site in self._sites if site.carries(needle)]
