#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Decide which sites a table search names."""

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass

from cmk.ccc.site import SiteId


@dataclass(frozen=True, kw_only=True)
class MonitorSite:
    id: SiteId
    customer: str | None = None


class MonitorSites:
    def __init__(self, sites: Iterable[MonitorSite] = ()) -> None:
        self._sites = tuple(sites)

    def matching(self, carries: Callable[[str], bool]) -> Sequence[SiteId]:
        """The sites whose ID or customer ``carries`` says the search names."""
        return [
            site.id
            for site in self._sites
            if any(carries(shown) for shown in (site.id, site.customer) if shown)
        ]
