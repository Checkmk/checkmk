#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""What "loading the page" means for each of the four pages being compared.

Each page is described by the HTTP requests a browser actually makes, because that is where the
two generations differ before any code runs: a classic view is one request that returns rows
already rendered, while a Vue page is a shell plus a REST call that returns them as JSON. A
comparison that timed only the first request of each would credit the new page with work it has
merely deferred.

The same descriptions serve the in-process runs and the runs against a real site, so a scenario
cannot drift between them.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Literal, Protocol

#: Where the internal REST API the Vue pages use is mounted.
API_ROOT = "api/internal"

type Generation = Literal["classic", "vue"]
type Subject = Literal["hosts", "services"]

#: How many rows the user asked for. Neither page fetches more as you scroll - the new table
#: virtualises what it already holds, and neither listing endpoint takes an offset - so asking
#: for more rows is the *only* way either page loads additional entries, and this is the axis
#: along which "show me more" has to be compared.
type LimitTier = Literal["soft", "hard", "none"]

#: What a tier means to the new pages. The numbers are not a coincidence: the classic views'
#: soft and hard query limits are 1000 and 5000, and those are exactly the two tiers the new
#: pages offer, so one tier is one comparison rather than two different questions.
_TIER_ROWS: Mapping[LimitTier, int | None] = {"soft": 1000, "hard": 5000, "none": None}

#: What a tier means to the classic views, which take a *mode* rather than a number and resolve
#: it against the configured limits. "soft" is the default and needs no variable at all; the
#: other two need permissions the admin measuring this has (`general.ignore_soft_limit` and
#: `general.ignore_hard_limit`), and silently fall back to the soft limit for a user without.
_TIER_VARS: Mapping[LimitTier, str] = {"soft": "", "hard": "&limit=hard", "none": "&limit=none"}

TIERS: Sequence[LimitTier] = ("soft", "hard", "none")


class HttpCaller(Protocol):
    """The one thing a scenario needs: issue a request and fail if it did not work."""

    def __call__(
        self, method: Literal["get", "post"], url: str, *, body: str | None = None
    ) -> None: ...


@dataclass(frozen=True, kw_only=True)
class PageContext:
    """What the URLs of a scenario have to be filled in with."""

    site_prefix: str
    limit: LimitTier
    host_name: str
    host_site_id: str

    def url(self, path: str) -> str:
        return f"{self.site_prefix}/{path}"

    @property
    def classic_limit_var(self) -> str:
        """The URL fragment putting a classic view on this tier."""
        return _TIER_VARS[self.limit]

    @property
    def rows(self) -> int | None:
        """The row count this tier asks the new pages for, None for no limit at all."""
        return _TIER_ROWS[self.limit]


@dataclass(frozen=True, kw_only=True)
class Page:
    """One page, and the requests loading it costs."""

    id: str
    generation: Generation
    subject: Subject
    title: str
    #: The requests a first page load makes: shell, then data for a Vue page.
    load: Callable[[HttpCaller, PageContext], None]
    #: The requests the page repeats on its refresh timer. A classic view reloads itself whole
    #: (``browser_reload``); a Vue page re-fetches only its rows. Both refresh every 30s by
    #: default, so this is what an open tab costs a distributed setup all day.
    poll: Callable[[HttpCaller, PageContext], None]


def _classic_all_hosts(call: HttpCaller, ctx: PageContext) -> None:
    call("get", ctx.url(f"view.py?view_name=allhosts{ctx.classic_limit_var}"))


def _vue_all_hosts_shell(call: HttpCaller, ctx: PageContext) -> None:
    call("get", ctx.url("monitor_all_hosts.py"))


def _vue_all_hosts_data(call: HttpCaller, ctx: PageContext) -> None:
    call(
        "post",
        ctx.url(f"{API_ROOT}/monitor/hosts"),
        body=json.dumps({"limit": ctx.rows}),
    )


def _vue_all_hosts(call: HttpCaller, ctx: PageContext) -> None:
    _vue_all_hosts_shell(call, ctx)
    _vue_all_hosts_data(call, ctx)


def _classic_all_hosts_one_site(call: HttpCaller, ctx: PageContext) -> None:
    # ``allhosts`` carries the optional site filter, and the ``site`` variable fills it in. It
    # becomes the connection's "only sites", so the listing is read from that site alone.
    call(
        "get",
        ctx.url(f"view.py?view_name=allhosts&site={ctx.host_site_id}{ctx.classic_limit_var}"),
    )


def _vue_all_hosts_one_site_data(call: HttpCaller, ctx: PageContext) -> None:
    call(
        "post",
        ctx.url(f"{API_ROOT}/monitor/hosts"),
        body=json.dumps(
            {
                "limit": ctx.rows,
                "filter": {
                    "type": "condition",
                    "field": "site_id",
                    "op": "one_of",
                    "value": [ctx.host_site_id],
                },
            }
        ),
    )


def _vue_all_hosts_one_site(call: HttpCaller, ctx: PageContext) -> None:
    _vue_all_hosts_shell(call, ctx)
    _vue_all_hosts_one_site_data(call, ctx)


def _classic_host_services(call: HttpCaller, ctx: PageContext) -> None:
    call(
        "get",
        ctx.url(
            f"view.py?view_name=host&host={ctx.host_name}&site={ctx.host_site_id}"
            f"{ctx.classic_limit_var}"
        ),
    )


def _vue_host_services_shell(call: HttpCaller, ctx: PageContext) -> None:
    call(
        "get",
        ctx.url(f"monitor_host_services.py?host={ctx.host_name}&site={ctx.host_site_id}"),
    )


def _vue_host_services_data(call: HttpCaller, ctx: PageContext) -> None:
    call(
        "post",
        ctx.url(f"{API_ROOT}/monitor/hosts/{ctx.host_name}/services?site_id={ctx.host_site_id}"),
        body=json.dumps({"limit": ctx.rows}),
    )


def _vue_host_services(call: HttpCaller, ctx: PageContext) -> None:
    _vue_host_services_shell(call, ctx)
    _vue_host_services_data(call, ctx)


ALL_HOSTS_CLASSIC = Page(
    id="all_hosts_classic",
    generation="classic",
    subject="hosts",
    title="All hosts (classic view)",
    load=_classic_all_hosts,
    poll=_classic_all_hosts,
)

ALL_HOSTS_VUE = Page(
    id="all_hosts_vue",
    generation="vue",
    subject="hosts",
    title="All hosts (new page)",
    load=_vue_all_hosts,
    poll=_vue_all_hosts_data,
)

#: The same listing, narrowed to one site. This is the move a distributed setup makes constantly
#: - "show me what that data centre is doing" - and it is the case where the two generations can
#: diverge in *which* sites they read, not just how much they read from each.
ALL_HOSTS_ONE_SITE_CLASSIC = Page(
    id="all_hosts_one_site_classic",
    generation="classic",
    subject="hosts",
    title="All hosts, one site (classic view)",
    load=_classic_all_hosts_one_site,
    poll=_classic_all_hosts_one_site,
)

ALL_HOSTS_ONE_SITE_VUE = Page(
    id="all_hosts_one_site_vue",
    generation="vue",
    subject="hosts",
    title="All hosts, one site (new page)",
    load=_vue_all_hosts_one_site,
    poll=_vue_all_hosts_one_site_data,
)

HOST_SERVICES_CLASSIC = Page(
    id="host_services_classic",
    generation="classic",
    subject="services",
    title="Services of host (classic view)",
    load=_classic_host_services,
    poll=_classic_host_services,
)

HOST_SERVICES_VUE = Page(
    id="host_services_vue",
    generation="vue",
    subject="services",
    title="Services of host (new page)",
    load=_vue_host_services,
    poll=_vue_host_services_data,
)

PAGES: Sequence[Page] = (
    ALL_HOSTS_CLASSIC,
    ALL_HOSTS_VUE,
    ALL_HOSTS_ONE_SITE_CLASSIC,
    ALL_HOSTS_ONE_SITE_VUE,
    HOST_SERVICES_CLASSIC,
    HOST_SERVICES_VUE,
)

#: Each comparison is a classic page and the page replacing it.
COMPARISONS: Sequence[tuple[Page, Page]] = (
    (ALL_HOSTS_CLASSIC, ALL_HOSTS_VUE),
    (ALL_HOSTS_ONE_SITE_CLASSIC, ALL_HOSTS_ONE_SITE_VUE),
    (HOST_SERVICES_CLASSIC, HOST_SERVICES_VUE),
)

#: The pages that narrow the listing to a single site, and the site-scoped table each should
#: therefore only read from that one site.
SITE_SCOPED_PAGES: Sequence[tuple[Page, str]] = (
    (ALL_HOSTS_ONE_SITE_CLASSIC, "hosts"),
    (ALL_HOSTS_ONE_SITE_VUE, "hosts"),
    (HOST_SERVICES_CLASSIC, "services"),
    (HOST_SERVICES_VUE, "services"),
)
