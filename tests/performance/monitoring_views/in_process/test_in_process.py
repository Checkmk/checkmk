#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Does reading a large distributed estate cost more through the new monitoring pages?

The comparison runs the GUI in this process against a fleet of fake Livestatus sites, so the
number of remote sites is a parameter rather than a machine requirement. Two kinds of result
come out of it, and they answer different halves of the question:

*Round trips and rows*, counted rather than timed. How many Livestatus queries a page load
costs, how many of them fan out to every site, and how many rows come back. These are exact and
machine-independent, and they are where a distributed setup gets expensive: a query that fans
out to fifty sites costs fifty round trips whether or not this machine notices.

*Seconds*, measured with pytest-benchmark. What the central site spends turning those rows into
a page. Absolute values belong to the machine that produced them; the number to read is the
ratio between the two generations of the same page at the same size, which the summary table
printed at the end of the run works out.

Run the whole matrix::

    bazel test //tests/performance/monitoring_views/in_process:in_process --test_output=all

Or one shape of it::

    bazel test //tests/performance/monitoring_views/in_process:in_process --test_output=all \
        --test_arg=--remote-sites=25 --test_arg=--hosts-per-site=5000 \
        --test_arg=--remote-latency-ms=20
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from time import perf_counter
from dataclasses import dataclass
from typing import Literal

import pytest
from pytest_benchmark.fixture import BenchmarkFixture

from tests.performance.monitoring_views.in_process.components import (
    ComponentProfile,
    profile_page,
)
from tests.performance.monitoring_views.in_process.fleet import (
    CENTRAL_SITE_ID,
    FleetBuilder,
    remote_site_id,
)
from tests.performance.monitoring_views.livestatus_fake import EstateShape, QueryLog, RowFactory
from tests.performance.monitoring_views.report import Measurement, Report
from tests.performance.monitoring_views.scenarios import (
    HttpCaller,
    ALL_HOSTS_CLASSIC,
    ALL_HOSTS_VUE,
    API_ROOT,
    COMPARISONS,
    HOST_SERVICES_CLASSIC,
    HOST_SERVICES_VUE,
    LimitTier,
    Page,
    PageContext,
    PAGES,
    SITE_SCOPED_PAGES,
    TIERS,
)
from tests.testlib.gui.web_test_app import CmkTestResponse, WebTestAppForCMK

#: What a scenario hands the probe: the requests one page load is made of.
type PageRequests = Callable[[HttpCaller, PageContext], None]

_JSON_HEADERS = {"Content-Type": "application/json", "Accept": "application/json"}


@dataclass(kw_only=True)
class Probe:
    """Runs one page's requests and reports what the fleet was asked for."""

    app: WebTestAppForCMK
    context: PageContext
    log: QueryLog
    #: What the last request of the last run returned. For a Vue page that is the JSON the
    #: table is built from; for a classic view, the rendered document. Kept so a test can ask
    #: how many rows actually arrived, rather than trusting that they did.
    last_response: CmkTestResponse | None = None

    def run(self, requests: PageRequests) -> None:
        requests(self._call, self.context)

    def observe(self, requests: PageRequests) -> QueryLog:
        """Run once with a cleared log, and hand back what the fleet saw."""
        self.log.clear()
        self.run(requests)
        # A query the fake cannot answer reaches the central as a broken connection, which it
        # handles by dropping that site. The page then renders without it - quickly, and
        # wrongly. So the run only counts as a measurement if nothing was refused.
        assert not self.log.failures, "the fake fleet could not answer: " + "; ".join(
            self.log.failures
        )
        return self.log

    def _call(self, method: Literal["get", "post"], url: str, *, body: str | None = None) -> None:
        response = (
            self.app.get(url, status=200)
            if method == "get"
            else self.app.post(url, data=body, headers=_JSON_HEADERS, status=200)
        )
        # A page that errors is fast, and an unnoticed error would be reported as a good
        # measurement. The status check above catches most of it; this catches the classic
        # views' habit of rendering their problems into a 200.
        if method == "get" and b"MKGeneralException" in response.data:
            raise AssertionError(f"{url} rendered an exception page")
        self.last_response = response


def _probe_for(
    app: WebTestAppForCMK, log: QueryLog, *, remote_count: int, limit: LimitTier
) -> Probe:
    # The services pages address one host on one site. It is a remote's host whenever there is
    # a remote, because a host on the central site would not exercise a distributed read at all.
    host_site = remote_site_id(0) if remote_count else CENTRAL_SITE_ID
    return Probe(
        app=app,
        context=PageContext(
            site_prefix=f"/{CENTRAL_SITE_ID}/check_mk",
            limit=limit,
            host_name=f"{host_site}-host-000000",
            host_site_id=host_site,
        ),
        log=log,
    )


@pytest.fixture(name="probe")
def fixture_probe(
    fake_fleet: WebTestAppForCMK,
    query_log: QueryLog,
    limit_tier: LimitTier,
    remote_count: int,
) -> Probe:
    return _probe_for(fake_fleet, query_log, remote_count=remote_count, limit=limit_tier)


# .
#   .--what a page costs-----------------------------------------------------


@dataclass(frozen=True, kw_only=True)
class Cost:
    """What one page load asked of the fleet."""

    queries: int
    rows: int
    payload_bytes: int
    per_site: dict[str, int]
    queries_by_kind: dict[str, int]
    rows_by_kind: dict[str, int]
    sites_by_kind: dict[str, frozenset[str]]

    @classmethod
    def of(cls, log: QueryLog) -> Cost:
        return cls(
            queries=len(log),
            rows=log.rows,
            payload_bytes=log.payload_bytes,
            per_site=dict(log.by_site()),
            queries_by_kind=dict(log.queries_by_kind()),
            rows_by_kind=dict(log.rows_by_kind()),
            sites_by_kind={kind: log.sites_asked(kind) for kind in log.queries_by_kind()},
        )

    def listed_rows(self, subject: str) -> int:
        """Rows of the listing itself, leaving out the counts and the connection handshake."""
        return self.rows_by_kind.get(subject, 0)

    def fan_outs(self, site_count: int) -> float:
        """How many times the page asked *every* site something.

        This is the figure a WAN link multiplies. It is derived rather than counted per query,
        because the multi-site connection sends one query to every site in parallel and each of
        those is a round trip of its own.
        """
        return self.queries / site_count if site_count else 0.0

    def as_measurement(
        self,
        *,
        scenario: str,
        page: Page,
        phase: str,
        sites: int,
        hosts_per_site: int,
        seconds: float | None = None,
    ) -> Measurement:
        return Measurement(
            scenario=scenario,
            page=page.id,
            phase=phase,
            sites=sites,
            hosts_per_site=hosts_per_site,
            queries=self.queries,
            fan_outs=self.fan_outs(sites),
            rows=self.rows,
            payload_bytes=self.payload_bytes,
            queries_by_kind=self.queries_by_kind,
            seconds=seconds,
        )


@pytest.mark.parametrize("page", PAGES, ids=lambda page: page.id)
def test_livestatus_cost_of_a_page_load(
    probe: Probe,
    page: Page,
    report: Report,
    remote_count: int,
    fleet_shape: EstateShape,
    limit_tier: LimitTier,
) -> None:
    """Record what one load and one refresh of each page cost the fleet, and check it stays sane.

    The assertions are deliberately few: this records a shape rather than policing a budget
    nobody has agreed. What it does refuse is the two ways a distributed read goes wrong -
    asking a site for something that is not there, and pulling back rows the page throws away.
    """
    site_count = remote_count + 1
    for phase, requests in (("load", page.load), ("refresh", page.poll)):
        cost = Cost.of(probe.observe(requests))
        report.add(
            cost.as_measurement(
                scenario="configured shape",
                page=page,
                phase=phase,
                sites=site_count,
                hosts_per_site=fleet_shape.hosts,
            )
        )

    load_cost = Cost.of(probe.observe(page.load))
    assert load_cost.queries, "a page that reads nothing cannot be compared"
    assert set(load_cost.per_site) == {
        CENTRAL_SITE_ID,
        *(remote_site_id(index) for index in range(remote_count)),
    }, "every configured site should have been asked, or the fleet silently shrank"

    if page.subject == "hosts":
        # The listing is capped per site, so a multi-site fetch legitimately carries up to
        # limit * sites rows before the merge throws the surplus away. Beyond that, a cap has
        # gone missing.
        rows = PageContext(site_prefix="", limit=limit_tier, host_name="", host_site_id="").rows
        ceiling = site_count * (fleet_shape.hosts if rows is None else min(rows, fleet_shape.hosts))
        listed = load_cost.listed_rows("hosts")
        assert listed <= ceiling, (
            f"{listed} host rows for a listing capped at {rows} across {site_count} sites"
        )


@pytest.mark.parametrize(
    "page, table", SITE_SCOPED_PAGES, ids=lambda argument: getattr(argument, "id", argument)
)
def test_a_page_scoped_to_one_site_reads_its_rows_from_that_site(
    probe: Probe, page: Page, table: str
) -> None:
    """A listing narrowed to one site must fetch its rows from that site and no other.

    This is the one thing about a distributed read that has to hold exactly rather than
    approximately, and it is not something a timing can show: a page that fans its listing out
    to every site still looks fine on a LAN with a small estate, and falls over on neither
    until somebody has fifty remotes.

    Only the listing query is held to it. Both generations also take counts that are deliberately
    estate-wide - the classic view resolves its folder filter across every site, the new page
    counts the whole estate for its "n of m" - and those legitimately fan out. The summary table
    records how many of each a page takes; the shape below is what must not change.
    """
    cost = Cost.of(probe.observe(page.load))
    reading_sites = cost.sites_by_kind.get(table, frozenset())

    assert reading_sites, f"{page.id} never read the {table} table at all"
    assert len(reading_sites) == 1, (
        f"{page.id} is scoped to one site but read {table} from {sorted(reading_sites)}"
    )


@pytest.mark.parametrize("classic, vue", COMPARISONS, ids=lambda page: page.id)
def test_the_new_page_reaches_no_further_than_the_old_one(
    probe: Probe, classic: Page, vue: Page, remote_count: int
) -> None:
    """Neither page may touch a site the other one did not need.

    Round trips are what a distributed setup pays for twice: once in latency per site, once in
    the work each site is asked to do. The two pages may differ in how many queries they take -
    the summary table records that - but a page reaching sites its predecessor left alone has
    changed the shape of the problem, not just its size.
    """
    classic_sites = set(Cost.of(probe.observe(classic.load)).per_site)
    vue_sites = set(Cost.of(probe.observe(vue.load)).per_site)

    assert vue_sites <= classic_sites, (
        f"{vue.id} read sites {sorted(vue_sites - classic_sites)}, which {classic.id} did not"
    )
    assert len(classic_sites) == remote_count + 1


# .
#   .--seconds---------------------------------------------------------------


def _timed(
    benchmark: BenchmarkFixture, probe: Probe, requests: PageRequests, rounds: int = 5
) -> float:
    benchmark.pedantic(  # type: ignore[no-untyped-call]
        probe.run,
        args=[requests],
        rounds=rounds,
        iterations=1,
        warmup_rounds=1,
    )
    stats = benchmark.stats
    assert stats is not None, "pytest-benchmark recorded no rounds"
    return float(stats.stats.mean)


@pytest.mark.parametrize("page", PAGES, ids=lambda page: page.id)
def test_page_load_duration(
    benchmark: BenchmarkFixture,
    probe: Probe,
    page: Page,
    report: Report,
    remote_count: int,
    fleet_shape: EstateShape,
) -> None:
    """Time a first page load: the shell and, for a Vue page, the rows it then fetches."""
    seconds = _timed(benchmark, probe, page.load)
    report.add(
        Cost.of(probe.observe(page.load)).as_measurement(
            scenario="timed",
            page=page,
            phase="load",
            sites=remote_count + 1,
            hosts_per_site=fleet_shape.hosts,
            seconds=seconds,
        )
    )


@pytest.mark.parametrize("page", PAGES, ids=lambda page: page.id)
def test_page_refresh_duration(
    benchmark: BenchmarkFixture,
    probe: Probe,
    page: Page,
    report: Report,
    remote_count: int,
    fleet_shape: EstateShape,
) -> None:
    """Time what an open tab repeats on its refresh timer.

    This is the load a distributed setup actually carries: a page is opened once and then
    refreshes itself every 30 seconds for as long as somebody leaves the tab open. The classic
    view reloads itself whole; the new page re-fetches only its rows, which is the one place
    the new design should be structurally cheaper.
    """
    seconds = _timed(benchmark, probe, page.poll)
    report.add(
        Cost.of(probe.observe(page.poll)).as_measurement(
            scenario="timed",
            page=page,
            phase="refresh",
            sites=remote_count + 1,
            hosts_per_site=fleet_shape.hosts,
            seconds=seconds,
        )
    )


# .
#   .--loading more entries--------------------------------------------------


@pytest.mark.parametrize("classic, vue", COMPARISONS, ids=lambda page: page.id)
def test_cost_of_asking_for_more_rows(
    fake_fleet: WebTestAppForCMK,
    query_log: QueryLog,
    classic: Page,
    vue: Page,
    report: Report,
    remote_count: int,
    fleet_shape: EstateShape,
) -> None:
    """Walk the row limits, which is the only way either page loads additional entries.

    Neither page fetches on scroll: the new table virtualises rows it already holds and neither
    listing endpoint takes an offset, so the whole listing arrives in one response. Asking for
    a bigger limit is therefore not a variation on the measurement above - it *is* the "show me
    more" path, and it is the one that multiplies across a fleet, because the limit is applied
    per site before the merge throws the surplus away.
    """
    for tier in TIERS:
        for page in (classic, vue):
            probe = _probe_for(fake_fleet, query_log, remote_count=remote_count, limit=tier)
            cost = Cost.of(probe.observe(page.load))
            report.add(
                cost.as_measurement(
                    scenario=f"limit={tier}",
                    page=page,
                    phase="load",
                    sites=remote_count + 1,
                    hosts_per_site=fleet_shape.hosts,
                )
            )
            assert cost.queries


@pytest.mark.parametrize("page", PAGES, ids=lambda page: page.id)
def test_one_request_carries_the_whole_listing(
    fake_fleet: WebTestAppForCMK, page: Page, remote_count: int
) -> None:
    """A page's rows must all arrive in the response to a single request.

    This is what makes "shell plus one data request" a faithful model of a page load, and it is
    the assumption every measurement in this suite rests on. It holds because neither listing
    endpoint offers an offset - but the shared frontend service already carries the paging
    machinery (`offset`, `maxOffset`, `nextPage`), unused by these two pages and wired up by
    another. The day it is wired up here, every page of rows becomes a fresh connection
    handshake, an estate-wide count and a fetch across every remote, and the scenarios above
    would go on quietly measuring only the first page. So the response is asked whether it is
    a page of something larger.
    """
    if page.generation != "vue":
        pytest.skip("a classic view renders its rows into the document; it has no paging meta")

    response = fake_fleet.post(
        _listing_url(page, remote_count),
        data='{"limit": 1000}',
        headers=_JSON_HEADERS,
        status=200,
    )
    meta = response.json["meta"]

    paging_keys = {"offset", "max_offset"} & set(meta)
    assert not paging_keys, (
        f"{page.id} now returns {sorted(paging_keys)}: the listing has become pageable, so a "
        "page load is no longer one data request and the scenarios need a paging step"
    )


def _listing_url(page: Page, remote_count: int) -> str:
    """The data request of one Vue page, as a URL this test can issue by itself."""
    host_site = remote_site_id(0) if remote_count else CENTRAL_SITE_ID
    root = f"/{CENTRAL_SITE_ID}/check_mk/{API_ROOT}"
    if page.subject == "hosts":
        return f"{root}/monitor/hosts"
    return f"{root}/monitor/hosts/{host_site}-host-000000/services?site_id={host_site}"


# .
#   .--which components matter-----------------------------------------------


@pytest.mark.parametrize("page", PAGES, ids=lambda page: page.id)
def test_where_a_page_load_spends_its_time(
    probe: Probe, page: Page, profiles: list[ComponentProfile]
) -> None:
    """Attribute one page load to the components it passes through.

    Everything else here measures a page from the outside. This says where the time goes, which
    is what turns "these components are the relevant ones" from an argument about the code into
    a measurement - and it is the only check that the fake fleet is not a large part of what is
    being timed. A harness costing a serious share of a page load would mean every ratio in the
    comparison above is partly a measurement of the harness.
    """
    profile = profile_page(page.id, lambda: probe.run(page.load))
    profiles.append(profile)

    assert profile.harness_share < 0.1, (
        f"the harness accounts for {profile.harness_share:.0%} of {page.id}'s load; at that "
        "share the comparison is measuring the test rather than the page"
    )


# .
#   .--loading the whole estate----------------------------------------------


@dataclass(frozen=True, kw_only=True)
class WholeEstate:
    """A fleet holding more than one page's worth, and what "all of it" means there."""

    id: str
    classic: Page
    vue: Page
    sites: int
    shape: EstateShape
    #: The Livestatus table the listing reads, so the rows it carried can be told apart from
    #: the counts taken alongside it.
    table: str
    #: Rows a listing of the whole estate must deliver, which with no limit in play is also the
    #: number Livestatus carries. For hosts that is the fleet; for services it is one host's,
    #: since that is all the services page ever lists.
    everything: int
    #: How many sites a listing of this subject reads from. The hosts pages read the fleet; the
    #: services page reads the one site holding the host, however wide the fleet is.
    reading_sites: int


#: What either page shows before anybody asks for more. Both offer the same first tier.
_PAGE_ROWS = 1000

#: Both estates are deliberately larger per site than the 1000 rows either page shows by
#: default, because otherwise "one page" and "the whole estate" are the same request and the
#: comparison below would have nothing to compare.
WHOLE_ESTATES: Sequence[WholeEstate] = (
    WholeEstate(
        id="all_hosts",
        classic=ALL_HOSTS_CLASSIC,
        vue=ALL_HOSTS_VUE,
        sites=4,
        # One service per host: the hosts pages read service *counts* off the host row and never
        # the services themselves, so generating more would only slow the fake down.
        shape=EstateShape(hosts=2000, services_per_host=1),
        table="hosts",
        everything=4 * 2000,
        reading_sites=4,
    ),
    WholeEstate(
        id="host_services",
        classic=HOST_SERVICES_CLASSIC,
        vue=HOST_SERVICES_VUE,
        sites=2,
        # Few hosts, many services each: the services page lists one host's services, so the
        # estate that matters is the depth of a host rather than the width of the fleet.
        shape=EstateShape(hosts=5, services_per_host=1500),
        table="services",
        everything=1500,
        # One host's services live on one site, so nothing is multiplied here.
        reading_sites=1,
    ),
)


@pytest.mark.parametrize("estate", WHOLE_ESTATES, ids=lambda estate: estate.id)
def test_the_cost_of_loading_everything_not_just_one_page(
    logged_in_admin_wsgi_app: WebTestAppForCMK,
    fleet_builder: FleetBuilder,
    report: Report,
    estate: WholeEstate,
) -> None:
    """Compare the two pages over the whole estate, not only over the first page of it.

    Timing a default page load compares two answers of a fixed size - a thousand rows each -
    and says nothing about reading everything there is. That flatters whichever page is
    cheaper per row only up to the cap, and it is not the question a distributed setup asks:
    it asks what showing all of it costs.

    Both generations can be told to drop the limit, and both then deliver every row in a single
    response, so the comparison is like for like. What each row *becomes* is where they part:
    the classic view renders all of them into the document it returns, while the new page
    returns them as data and its table builds only the rows on screen. That difference is real
    and is not measured here - it is browser work, and this suite has no browser. What is
    measured is everything up to and including the response.
    """
    tiers: Sequence[tuple[LimitTier, int]] = (
        ("soft", _PAGE_ROWS),
        ("none", estate.everything),
    )
    for tier, shown in tiers:
        for page in (estate.classic, estate.vue):
            read = estate.everything if tier == "none" else _rows_read_for_one_page(page, estate)
            with fleet_builder(estate.sites - 1, estate.shape) as log:
                probe = _probe_for(
                    logged_in_admin_wsgi_app,
                    log,
                    remote_count=estate.sites - 1,
                    limit=tier,
                )
                # One load before the timed one. The first request of a kind in this process
                # pays for warming the framework up, and the fleet renders each site's answer
                # once before serving it from memory; charging either to whichever tier happens
                # to run first would make the cheaper tier look dearer than the estate it reads.
                probe.run(page.load)
                started = perf_counter()
                # `observe` clears the log first, so what it hands back is the timed load
                # alone rather than that load plus the warm-up before it.
                cost = Cost.of(probe.observe(page.load))
                seconds = perf_counter() - started

                _assert_rows(probe, page, estate, tier=tier, shown=shown, read=read, cost=cost)

            report.add(
                cost.as_measurement(
                    scenario=f"whole estate, limit={tier}",
                    page=page,
                    phase="load",
                    sites=estate.sites,
                    hosts_per_site=estate.shape.hosts,
                    seconds=seconds,
                )
            )


def _rows_read_for_one_page(page: Page, estate: WholeEstate) -> int:
    """How many rows a limited listing pulls off the fleet before showing one page of them.

    The limit reaches Livestatus per site, so a fleet carries a page each and the merge throws
    the surplus away. A classic view asks every site for one row *more* than it will show, which
    is how it knows to say that there were more (`cmk.gui.sites.set_limit`); the new pages ask
    for exactly the page and take the count from a `Stats` query instead.
    """
    per_site = _PAGE_ROWS + 1 if page.generation == "classic" else _PAGE_ROWS
    return per_site * estate.reading_sites


def _assert_rows(
    probe: Probe,
    page: Page,
    estate: WholeEstate,
    *,
    tier: str,
    shown: int,
    read: int,
    cost: Cost,
) -> None:
    """Check the load carried the rows it should have, at whichever end can be counted.

    Both generations are held to what Livestatus carried, which is the one number they can be
    compared on. A Vue page is additionally held to its own response, since the rows are in it
    and can simply be counted; a classic view turns them into markup instead, and counting that
    would be asserting on how the table is built rather than on how much of it arrived.
    """
    # The response first: it is what a user would be looking at, and the rows Livestatus
    # carried are the explanation rather than the symptom.
    if page.generation == "vue":
        assert probe.last_response is not None
        body = probe.last_response.json
        delivered = len(body["hosts" if estate.table == "hosts" else "services"])
        assert delivered == shown, (
            f"{page.id} at limit={tier} returned {delivered} rows where the estate holds "
            f"{estate.everything} and this tier should show {shown}"
        )

    carried = cost.listed_rows(estate.table)
    assert carried == read, (
        f"{page.id} at limit={tier} read {carried} {estate.table} rows from the fleet, expected "
        f"{read}"
    )


@pytest.mark.parametrize("estate", WHOLE_ESTATES, ids=lambda estate: estate.id)
def test_an_unlimited_listing_reads_every_row_from_every_site(
    logged_in_admin_wsgi_app: WebTestAppForCMK,
    fleet_builder: FleetBuilder,
    estate: WholeEstate,
) -> None:
    """With the limit dropped, both pages must read the estate entire - and be seen to.

    Checked at the socket rather than in the response, because that is the one place both
    generations are comparable: a classic view's rows end up as markup and a new page's as
    JSON, but both had to be read from the sites first. With no limit in play there is no
    per-site cap and nothing is discarded after the merge, so the rows Livestatus carried are
    exactly the rows the page has.
    """
    for page in (estate.classic, estate.vue):
        with fleet_builder(estate.sites - 1, estate.shape) as log:
            probe = _probe_for(
                logged_in_admin_wsgi_app, log, remote_count=estate.sites - 1, limit="none"
            )
            probe.run(page.load)
            read = Cost.of(log).listed_rows(estate.table)

            assert read == estate.everything, (
                f"{page.id} with no limit read {read} {estate.table} rows, but the estate holds "
                f"{estate.everything}"
            )

            if page.generation == "classic":
                # The document has to carry the far end of the estate, not just its beginning:
                # a listing truncated anywhere would still read the right number of rows if the
                # truncation happened after the read.
                assert probe.last_response is not None
                document = probe.last_response.data
                for edge in _estate_edges(estate):
                    assert edge.encode() in document, (
                        f"{page.id} read every row but {edge!r} is not in the page it rendered"
                    )


def _estate_edges(estate: WholeEstate) -> Sequence[str]:
    """Names that only appear if the listing runs from one end of the estate to the other."""
    if estate.table == "hosts":
        last_site = remote_site_id(estate.sites - 2) if estate.sites > 1 else CENTRAL_SITE_ID
        return (
            f"{remote_site_id(0)}-host-000000",
            f"{last_site}-host-{estate.shape.hosts - 1:06d}",
        )
    # The services of one host. Their names repeat in a cycle, so only the *last* one is
    # peculiar to a listing that reached the end - asking the generator for it rather than
    # spelling it out here keeps the two from drifting apart.
    rows = RowFactory(remote_site_id(0), estate.shape)
    return (
        str(rows.service("description", 0, 0)),
        str(rows.service("description", 0, estate.shape.services_per_host - 1)),
    )


# .
#   .--scaling---------------------------------------------------------------


#: Site counts the scaling walk visits. The estate stays the same size across them, so what
#: changes is only how many places it is spread over.
_SITE_COUNTS: Sequence[int] = (1, 5, 10, 25)


@pytest.mark.parametrize("page", PAGES, ids=lambda page: page.id)
def test_scaling_over_site_count(
    logged_in_admin_wsgi_app: WebTestAppForCMK,
    fleet_builder: FleetBuilder,
    page: Page,
    report: Report,
    limit_tier: LimitTier,
    fleet_shape: EstateShape,
    remote_count: int,
) -> None:
    """Walk the number of sites at a constant total estate and record the curve.

    Splitting a fixed number of hosts over more sites is the move this is really about: the
    rows the page has to show do not change, only how many places they come from. A page whose
    cost tracks the estate scales with the estate; one whose cost tracks the site count does
    not, and that is what a distributed setup runs into.
    """
    total_hosts = fleet_shape.hosts * (remote_count + 1)

    for site_count in _SITE_COUNTS:
        shape = EstateShape(
            hosts=max(total_hosts // site_count, 1),
            services_per_host=fleet_shape.services_per_host,
        )
        with fleet_builder(site_count - 1, shape) as log:
            probe = _probe_for(
                logged_in_admin_wsgi_app,
                log,
                remote_count=site_count - 1,
                limit=limit_tier,
            )
            cost = Cost.of(probe.observe(page.load))
        report.add(
            cost.as_measurement(
                scenario=f"{total_hosts} hosts spread",
                page=page,
                phase="load",
                sites=site_count,
                hosts_per_site=shape.hosts,
            )
        )
        assert cost.queries
