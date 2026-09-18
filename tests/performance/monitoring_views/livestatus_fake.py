#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""A Livestatus endpoint that answers out of generated data instead of a monitoring core.

Why this exists
---------------
The question these tests ask is whether the new monitoring pages read a large distributed
estate more expensively than the views they replace. Everything that decides the answer sits
on the *central* site: which queries the page builds, how many round trips it takes, how many
rows come back per site, and what the GUI then does with them in Python. Everything on the
other end of the socket - the core doing the checking, the fetchers, the RRDs, the remote
site's own GUI - is identical for both pages, and none of it is reached by a page that only
reads. So it is not built; a responder that speaks Livestatus and invents plausible rows
stands in for a remote site, and one process can be fifty of them.

What that buys and what it costs
--------------------------------
It makes the remote end near-free and, crucially, *identical* for both pages, so a measured
difference belongs to the central site rather than to the sites answering it. It does not
reproduce a real core's query time or a real network's latency. Both are the same per query,
but the two pages do not issue the same *number* of queries, so leaving latency at zero would
hide a regression that is purely about round trips. Hence ``latency``: set it to what a WAN
link costs and the round-trip difference becomes visible in the measurement.

Honesty rules
-------------
A fake that quietly answers the wrong thing turns a performance experiment into fiction. So
anything this module does not understand raises :class:`UnsupportedQuery` rather than being
skipped: an unhandled header, an unknown table, a filter operator nobody implemented. If a
page starts issuing something new, the tests fail loudly and this module gets extended.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from functools import partial
from typing import Final, Literal

from cmk.livestatus_client.tables import Hosts, Services, Status
from cmk.livestatus_client.types import Column, Table

#: Headers that vary from request to request without changing the answer. They are dropped
#: before a query is used as a cache key, so the same page load hits the same rendered payload
#: every round instead of re-rendering it.
_VOLATILE_HEADERS: Final = frozenset(
    {"Localtime", "KeepAlive", "ResponseHeader", "Cache", "AuthUser"}
)

#: Headers this module reads. Anything else in a query is an unhandled feature, not a
#: formality to ignore - see the honesty rules above.
_KNOWN_HEADERS: Final = _VOLATILE_HEADERS | {
    # Not volatile: it decides how the payload is encoded, so it belongs in the cache key. A
    # Python repr handed to a client that asked for JSON fails to parse, and the central reads
    # that as a broken site rather than as a bad answer.
    "OutputFormat",
    "Columns",
    "Filter",
    "And",
    "Or",
    "Negate",
    "Stats",
    "Limit",
    "OrderBy",
    "ColumnHeaders",
}

_TABLES: Final[Mapping[str, type[Table]]] = {"hosts": Hosts, "services": Services}

#: Each table's own column-name prefix, which Livestatus strips before looking a column up
#: (``Table::column``). It is why the classic views can ask ``GET hosts`` for ``host_state``
#: while the table's column is called ``state`` - and why a fake that does not strip it drops
#: every site as unreachable the moment a classic view is loaded.
_NAME_PREFIXES: Final[Mapping[str, str]] = {"hosts": "host_", "services": "service_"}

#: A fixed instant, so a generated row never depends on when the test runs and a rendered
#: payload can be cached across rounds.
_EPOCH: Final = 1_770_000_000

_DIGITS: Final = re.compile(r"(\d+)")


class UnsupportedQuery(RuntimeError):
    """The responder was asked something it cannot answer faithfully."""


# .
#   .--rows----------------------------------------------------------------.


#: Folder paths generated hosts are spread over, so the Folder column and the folder filter
#: have something to work with. Titles are what Setup shows; the file is what Livestatus has.
_FOLDERS: Final = (
    "",
    "dc_muc",
    "dc_muc/rack1",
    "dc_muc/rack2",
    "dc_ber",
    "dc_ber/rack1",
    "network",
    "network/core",
    "network/edge",
    "cloud",
)

#: Host states in the proportion a healthy estate has them, as a lookup by ``index % 100``.
_HOST_STATES: Final = tuple([0] * 94 + [1] * 4 + [2] * 2)

#: Service states, likewise. A real estate is mostly OK with a long tail of warnings.
_SERVICE_STATES: Final = tuple([0] * 88 + [1] * 7 + [2] * 3 + [3] * 2)

_SERVICE_NAMES: Final = (
    "Check_MK",
    "Check_MK Discovery",
    "CPU load",
    "CPU utilization",
    "Memory",
    "Uptime",
    "Filesystem /",
    "Filesystem /var",
    "Filesystem /home",
    "Interface 1",
    "Interface 2",
    "NTP Time",
    "Number of threads",
    "Kernel Context Switches",
    "Kernel Major Page Faults",
    "Kernel Process Creations",
    "Systemd Service Summary",
    "Mount options of /",
    "TCP Connections",
    "Postfix status",
)

_TAGS: Final = {
    "address_family": "ip-v4-only",
    "agent": "cmk-agent",
    "criticality": "prod",
    "networking": "lan",
    "piggyback": "auto-piggyback",
    "site": "SITE",
    "snmp_ds": "no-snmp",
    "tcp": "tcp",
}


def _host_labels(site_id: str, index: int) -> dict[str, str]:
    return {
        "cmk/site": site_id,
        "cmk/os_family": "linux",
        "cmk/os_name": "Ubuntu",
        "cmk/check_mk_server": "yes" if index % 500 == 0 else "no",
        "cmk/device_type": "server",
    }


def _address(index: int) -> str:
    return f"10.{(index // 65536) % 256}.{(index // 256) % 256}.{index % 256}"


@dataclass(frozen=True, kw_only=True)
class EstateShape:
    """How much of a monitored estate one fake site pretends to have."""

    hosts: int
    services_per_host: int = 20

    @property
    def services(self) -> int:
        return self.hosts * self.services_per_host


class RowFactory:
    """Builds the value of one column of one row, without ever materialising a row.

    Rows are produced by index rather than stored, so a site of 50,000 hosts costs nothing
    until a query actually asks for rows - and a query with a ``Limit`` only ever pays for the
    rows it keeps.

    Columns nobody models get a value of the right Livestatus type (empty string, 0, [], {}).
    That understates the payload of a page reading a column this module has not thought about,
    which is worth knowing when a measurement looks suspiciously cheap; the columns both
    monitoring pages actually read are modelled explicitly below.
    """

    def __init__(self, site_id: str, shape: EstateShape) -> None:
        self._site_id = site_id
        self._shape = shape

    # -- hosts ---------------------------------------------------------------------------

    def host_name(self, index: int) -> str:
        return f"{self._site_id}-host-{index:06d}"

    def host(self, column: str, index: int) -> object:
        match column:
            case "name":
                return self.host_name(index)
            case "alias":
                return f"Host {index} on {self._site_id}"
            case "address":
                return _address(index)
            case "state":
                return _HOST_STATES[index % len(_HOST_STATES)]
            case "has_been_checked":
                return 1
            case "acknowledged":
                return 1 if index % 97 == 0 else 0
            case "scheduled_downtime_depth":
                return 1 if index % 89 == 0 else 0
            case "num_services":
                return self._shape.services_per_host
            case "num_services_ok":
                return max(self._shape.services_per_host - (index % 4), 0)
            case "num_services_warn":
                return index % 3
            case "num_services_crit":
                return index % 2
            case "num_services_unknown":
                return 0
            case "num_services_pending":
                return 0
            case "filename":
                folder = _FOLDERS[index % len(_FOLDERS)]
                return f"/wato/{folder}/hosts.mk" if folder else "/wato/hosts.mk"
            case "labels":
                return _host_labels(self._site_id, index)
            case "label_sources":
                return dict.fromkeys(_host_labels(self._site_id, index), "discovered")
            case "tags":
                return {**_TAGS, "site": self._site_id}
            case "contacts":
                return ["hh"]
            case "contact_groups":
                return ["all"]
            case "last_check":
                return _EPOCH - (index % 60)
            case "last_state_change":
                return _EPOCH - (index % 86400)
            case "custom_variable_names":
                return ["FILENAME", "ADDRESS_FAMILY", "ADDRESS_4", "ADDRESS_6", "TAGS"]
            case "custom_variable_values":
                # The TAGS value is a long string on every real host and a sizeable part of
                # what the classic view transfers, so it is spelled out rather than defaulted.
                tags = " ".join(f"{key}:{value}" for key, value in _TAGS.items())
                return [
                    str(self.host("filename", index)),
                    "4",
                    _address(index),
                    "",
                    f"/wato/ {tags} site:{self._site_id}",
                ]
            case "check_command":
                return "check-mk-host-smart"
            case "notifications_enabled" | "active_checks_enabled" | "accept_passive_checks":
                return 1
            case "in_check_period" | "in_notification_period" | "in_service_period":
                return 1
            case _:
                return _typed_default(Hosts, column)

    # -- services ------------------------------------------------------------------------

    def service(self, column: str, host_index: int, index: int) -> object:
        match column:
            case "description":
                return self._service_name(index)
            case "host_name":
                return self.host_name(host_index)
            case "state":
                return _SERVICE_STATES[(host_index + index) % len(_SERVICE_STATES)]
            case "has_been_checked":
                return 1
            case "plugin_output":
                return f"OK - {self._service_name(index)} is within bounds, 0.0 sec"
            case "long_plugin_output":
                return ""
            case "perf_data":
                return "load1=0.5;5;10;0; load5=0.4;5;10;0; load15=0.3;5;10;0;"
            case "check_command":
                return "check_mk-cpu.loads"
            case "acknowledged":
                return 1 if index % 41 == 0 else 0
            case "scheduled_downtime_depth":
                return 1 if index % 37 == 0 else 0
            case "notifications_enabled":
                return 1
            case "is_flapping":
                return 0
            case "last_check":
                return _EPOCH - (index % 60)
            case "last_state_change" | "next_check":
                return _EPOCH - (index % 86400)
            case "current_attempt":
                return 1
            case "max_check_attempts":
                return 3
            case "labels":
                return {"cmk/service_type": "standard"}
            case "label_sources":
                return {"cmk/service_type": "discovered"}
            case "tags":
                return {**_TAGS, "site": self._site_id}
            case "contacts":
                return ["hh"]
            case "contact_groups":
                return ["all"]
            case "host_alias":
                return f"Host {host_index} on {self._site_id}"
            case "host_state":
                return _HOST_STATES[host_index % len(_HOST_STATES)]
            case "host_acknowledged" | "host_scheduled_downtime_depth":
                return 0
            case _:
                return _typed_default(Services, column)

    def _service_name(self, index: int) -> str:
        name = _SERVICE_NAMES[index % len(_SERVICE_NAMES)]
        repeat = index // len(_SERVICE_NAMES)
        return name if repeat == 0 else f"{name} {repeat}"


_TYPED_DEFAULTS: Final[Mapping[str, object]] = {
    "string": "",
    "blob": "",
    "int": 0,
    "float": 0.0,
    "time": _EPOCH,
    "list": [],
    "dict": {},
    "dictdouble": {},
}


def resolve_column(table: str, column: str) -> str:
    """The table's own name for a column, the way Livestatus resolves one.

    Livestatus strips its table's prefix off a column name as often as it appears, then tries an
    exact match and finally the prefixed name. So ``host_state`` on ``hosts`` is ``state``,
    while ``host_state`` on ``services`` is a column in its own right.
    """
    prefix = _NAME_PREFIXES[table]
    stripped = column
    while stripped.startswith(prefix):
        stripped = stripped[len(prefix) :]

    model = _TABLES[table]
    for candidate in (stripped, f"{prefix}{stripped}"):
        if isinstance(getattr(model, candidate, None), Column):
            return candidate

    raise UnsupportedQuery(f"table {table!r} has no column {column!r}")


def _typed_default(table: type[Table], column: str) -> object:
    col = getattr(table, column, None)
    if not isinstance(col, Column):
        raise UnsupportedQuery(f"{column!r} is not a column of {table.__tablename__!r}")
    return _TYPED_DEFAULTS[col.type]


# .
#   .--query----------------------------------------------------------------


type _Predicate = Callable[[Callable[[str], object]], bool]

_OPERATORS: Final[Mapping[str, Callable[[object, str], bool]]] = {
    "=": lambda value, wanted: _as_str(value) == wanted,
    "!=": lambda value, wanted: _as_str(value) != wanted,
    "~": lambda value, wanted: re.search(wanted, _as_str(value)) is not None,
    "!~": lambda value, wanted: re.search(wanted, _as_str(value)) is None,
    "~~": lambda value, wanted: re.search(wanted, _as_str(value), re.IGNORECASE) is not None,
    "!~~": lambda value, wanted: re.search(wanted, _as_str(value), re.IGNORECASE) is None,
    "<": lambda value, wanted: _as_number(value) < float(wanted),
    ">": lambda value, wanted: _as_number(value) > float(wanted),
    "<=": lambda value, wanted: _as_number(value) <= float(wanted),
    ">=": lambda value, wanted: _as_number(value) >= float(wanted),
}


def _as_str(value: object) -> str:
    return value if isinstance(value, str) else str(value)


def _as_number(value: object) -> float:
    return float(value) if isinstance(value, int | float) else 0.0


@dataclass(frozen=True, kw_only=True)
class ParsedQuery:
    table: str
    columns: tuple[str, ...]
    predicate: _Predicate | None
    stats: tuple[str, ...]
    limit: int | None
    order_by: tuple[str, Literal["asc", "desc"], bool] | None

    @property
    def is_stats(self) -> bool:
        return bool(self.stats)


def parse_query(query: str) -> ParsedQuery:
    """Turn a Livestatus query into what this module needs to answer it.

    Filters are combined the way Livestatus combines them: every ``Filter:`` line pushes onto a
    stack, ``And:``/``Or:`` pop the given number and push the combination, ``Negate:`` inverts
    the top, and whatever is left at the end is ANDed together.
    """
    lines = [line for line in query.splitlines() if line.strip()]
    if not lines or not lines[0].startswith("GET "):
        raise UnsupportedQuery(f"Not a Livestatus query: {query!r}")

    table = lines[0][4:].strip()
    if table not in _TABLES:
        raise UnsupportedQuery(f"Table {table!r} is not served by the fake")

    columns: tuple[str, ...] = ()
    stats: list[str] = []
    limit: int | None = None
    order_by: tuple[str, Literal["asc", "desc"], bool] | None = None
    stack: list[_Predicate] = []

    for line in lines[1:]:
        header, _, value = line.partition(":")
        value = value.strip()
        if header not in _KNOWN_HEADERS:
            raise UnsupportedQuery(f"Header {header!r} is not handled by the fake: {line!r}")

        match header:
            case "Columns":
                columns = tuple(resolve_column(table, name) for name in value.split())
            case "Filter":
                stack.append(_parse_filter(table, value))
            case "And" | "Or":
                count = int(value)
                if count > len(stack):
                    raise UnsupportedQuery(f"{header}: {count} with only {len(stack)} filters")
                popped = [stack.pop() for _ in range(count)]
                stack.append(_all_of(popped) if header == "And" else _any_of(popped))
            case "Negate":
                if not stack:
                    raise UnsupportedQuery("Negate: with no filter to negate")
                stack.append(_negated(stack.pop()))
            case "Stats":
                stats.append(value)
            case "Limit":
                limit = int(value)
            case "OrderBy":
                order_by = _parse_order_by(value)
            case "OutputFormat":
                pass  # read where the payload is encoded, not where it is computed
            case _:
                pass  # a volatile header, or ColumnHeaders which the client never sets

    return ParsedQuery(
        table=table,
        columns=columns,
        predicate=_all_of(stack) if stack else None,
        stats=tuple(stats),
        limit=limit,
        order_by=order_by,
    )


def _parse_filter(table: str, value: str) -> _Predicate:
    column, _, rest = value.partition(" ")
    operator, _, wanted = rest.partition(" ")
    if operator not in _OPERATORS:
        raise UnsupportedQuery(f"Filter operator {operator!r} is not implemented: {value!r}")
    resolved = resolve_column(table, column)
    compare = _OPERATORS[operator]

    def matches(get: Callable[[str], object]) -> bool:
        return compare(get(resolved), wanted)

    return matches


def _negated(inner: _Predicate) -> _Predicate:
    def inverted(get: Callable[[str], object]) -> bool:
        return not inner(get)

    return inverted


def _parse_order_by(value: str) -> tuple[str, Literal["asc", "desc"], bool]:
    parts = value.split()
    natural = "natural" in parts
    direction: Literal["asc", "desc"] = "desc" if "desc" in parts else "asc"
    return parts[0], direction, natural


def _all_of(predicates: Sequence[_Predicate]) -> _Predicate:
    return lambda get: all(predicate(get) for predicate in predicates)


def _any_of(predicates: Sequence[_Predicate]) -> _Predicate:
    return lambda get: any(predicate(get) for predicate in predicates)


def _natural_key(value: str) -> tuple[int | str, ...]:
    return tuple(int(chunk) if chunk.isdigit() else chunk.lower() for chunk in _DIGITS.split(value))


def cache_key(query: str) -> str:
    """The query with everything that varies per request stripped, for caching a payload."""
    return "\n".join(
        line
        for line in query.splitlines()
        if line.strip() and line.partition(":")[0] not in _VOLATILE_HEADERS
    )


# .
#   .--site-----------------------------------------------------------------


@dataclass(kw_only=True)
class QueryRecord:
    """One query a site was asked, kept so a test can count round trips, not just seconds."""

    site_id: str
    query: str
    #: What the query asked for, as ``hosts``, ``services``, ``status`` or ``<table> (stats)``.
    #: A page's cost breaks down along this: the rows it lists, the counts it takes alongside
    #: them, and the connection handshake every request pays.
    kind: str
    rows: int
    payload_bytes: int


@dataclass
class QueryLog:
    """What every fake site was asked during a measurement."""

    records: list[QueryRecord] = field(default_factory=list)
    #: Queries the fake could not answer. A refusal reaches the client as a socket-level
    #: failure and the central quietly drops that site, so the page still renders - empty, and
    #: fast. Recording them is what turns that into a visible test failure.
    failures: list[str] = field(default_factory=list)

    def clear(self) -> None:
        self.records.clear()
        self.failures.clear()

    def __len__(self) -> int:
        return len(self.records)

    @property
    def rows(self) -> int:
        return sum(record.rows for record in self.records)

    @property
    def payload_bytes(self) -> int:
        return sum(record.payload_bytes for record in self.records)

    def by_site(self) -> Mapping[str, int]:
        counts: dict[str, int] = {}
        for record in self.records:
            counts[record.site_id] = counts.get(record.site_id, 0) + 1
        return counts

    def queries_by_kind(self) -> Mapping[str, int]:
        """How many queries of each kind, which is the round-trip breakdown of a page."""
        counts: dict[str, int] = {}
        for record in self.records:
            counts[record.kind] = counts.get(record.kind, 0) + 1
        return counts

    def sites_asked(self, kind: str) -> frozenset[str]:
        """Which sites were asked a query of this kind.

        A page reading one host's services should reach exactly one site with a ``services``
        query, however many sites its connection handshake and its counts touch.
        """
        return frozenset(record.site_id for record in self.records if record.kind == kind)

    def rows_by_kind(self) -> Mapping[str, int]:
        """How many rows each kind of query carried back."""
        counts: dict[str, int] = {}
        for record in self.records:
            counts[record.kind] = counts.get(record.kind, 0) + record.rows
        return counts


def query_kind(query: str) -> str:
    """Name what a query is after: the listing itself, a count alongside it, or the handshake."""
    first, _, rest = query.partition("\n")
    table = first.removeprefix("GET ").strip()
    return f"{table} (stats)" if "\nStats:" in f"\n{rest}" else table


@dataclass(frozen=True, kw_only=True)
class FakeVersion:
    """What a fake site claims to be, so the central accepts the connection.

    ``cmk.gui.sites._connect_multiple_sites`` reads these off the ``status`` table and drops a
    site whose edition it cannot place or whose licensing does not permit the connection, so a
    site lying badly here simply disappears from every query rather than failing visibly.
    """

    livestatus_version: str
    program_version: str
    edition: str


class FakeSite:
    """One remote site's worth of Livestatus, answered out of generated data."""

    def __init__(
        self,
        site_id: str,
        shape: EstateShape,
        *,
        version: FakeVersion,
        log: QueryLog | None = None,
        latency: float = 0.0,
    ) -> None:
        self.site_id = site_id
        self.shape = shape
        self._version = version
        self._log = log
        #: What this site's link costs. Waiting for it is left to whoever holds the socket,
        #: because a multi-site connection sends every site's query before reading any of the
        #: answers: a fan-out costs one link's latency, not the sum of them all. Sleeping here
        #: instead would serialise it and multiply the cost by the number of sites.
        self.latency = latency
        self._rows = RowFactory(site_id, shape)
        #: Rendered payloads by stripped query. A page issues the same query every round, so
        #: after the first one the fake costs a dict lookup and the measurement is the central
        #: site's alone.
        self._payloads: dict[str, tuple[bytes, int]] = {}

    def respond(self, query: str) -> bytes:
        """The payload for one query, without the fixed16 response header.

        Raises :class:`UnsupportedQuery` for anything it cannot answer faithfully, after
        recording it, so a fake that has fallen behind the code shows up as a failed test
        rather than as an unexpectedly quick page.
        """
        try:
            return self._respond(query)
        except UnsupportedQuery as exc:
            # The query goes into the message: a refusal reaches its caller as a broken site,
            # often by way of a daemon in between, and by then the only clue left is this text.
            detail = f"{self.site_id}: {exc} -- asked: {query!r}"
            if self._log is not None:
                self._log.failures.append(detail)
            raise UnsupportedQuery(detail) from None

    def _respond(self, query: str) -> bytes:
        key = cache_key(query)
        if (cached := self._payloads.get(key)) is None:
            payload, rows = self._render(key)
            cached = (payload, rows)
            self._payloads[key] = cached
        payload, rows = cached

        if self._log is not None:
            self._log.records.append(
                QueryRecord(
                    site_id=self.site_id,
                    query=key,
                    kind=query_kind(key),
                    rows=rows,
                    payload_bytes=len(payload),
                )
            )
        return payload

    def _render(self, query: str) -> tuple[bytes, int]:
        if query.startswith("GET status"):
            rows = [self._status_row(query)]
        else:
            parsed = parse_query(query)
            rows = list(self._answer(parsed))
        return _encode(rows, _output_format(query)), len(rows)

    def _status_row(self, query: str) -> list[object]:
        """The one row of the ``status`` table.

        Only the columns that have to carry a particular value are spelled out - the version and
        edition the central site checks a remote against, and the counts it reports. Everything
        else falls back to a value of the column's own type, because this table is not read only
        by the GUI: the Livestatus proxy asks it for columns of its own, and a fake that lists
        what it will answer refuses those and takes the whole site down with it.
        """
        values: dict[str, object] = {
            "livestatus_version": self._version.livestatus_version,
            "program_version": self._version.program_version,
            "program_start": _EPOCH,
            "num_hosts": self.shape.hosts,
            "num_services": self.shape.services,
            "max_long_output_size": 2000,
            "core_pid": 1234,
            "edition": self._version.edition,
        }
        return [
            values[column] if column in values else _typed_default(Status, column)
            for column in _status_columns(query)
        ]

    def _answer(self, parsed: ParsedQuery) -> Iterator[list[object]]:
        getters = self._getters(parsed.table)
        if parsed.is_stats:
            yield from self._answer_stats(parsed, getters)
            return

        rows = self._matching(parsed, getters)
        if parsed.order_by is not None:
            rows = self._ordered(rows, parsed.order_by)
        if parsed.limit is not None:
            rows = _take(rows, parsed.limit)
        for get in rows:
            yield [get(column) for column in parsed.columns]

    def _answer_stats(
        self, parsed: ParsedQuery, getters: Iterable[Callable[[str], object]]
    ) -> Iterator[list[object]]:
        """A ``Stats:`` count, optionally grouped by the queried columns.

        Only the counting form is implemented, because it is the only one the monitoring pages
        and the classic views' folder filter use. ``Stats: state >= 0`` counts everything with a
        state, i.e. every row that passed the filters.
        """
        if len(parsed.stats) != 1:
            raise UnsupportedQuery(f"only a single Stats line is implemented: {parsed.stats}")
        stat = _parse_filter(parsed.table, parsed.stats[0])

        counts: dict[tuple[object, ...], int] = {}
        for get in self._matching(parsed, getters):
            if not stat(get):
                continue
            group = tuple(get(column) for column in parsed.columns)
            counts[group] = counts.get(group, 0) + 1

        for group, count in counts.items():
            yield [*group, count]

    def _matching(
        self, parsed: ParsedQuery, getters: Iterable[Callable[[str], object]]
    ) -> Iterator[Callable[[str], object]]:
        if parsed.predicate is None:
            yield from getters
            return
        for get in getters:
            if parsed.predicate(get):
                yield get

    def _ordered(
        self,
        rows: Iterable[Callable[[str], object]],
        order_by: tuple[str, Literal["asc", "desc"], bool],
    ) -> Iterator[Callable[[str], object]]:
        column, direction, natural = order_by

        def key(get: Callable[[str], object]) -> object:
            value = get(column)
            return _natural_key(value) if natural and isinstance(value, str) else value

        yield from sorted(rows, key=key, reverse=direction == "desc")  # type: ignore[arg-type]

    def _getters(self, table: str) -> Iterator[Callable[[str], object]]:
        """One accessor per row, so a column is only ever computed when it is asked for."""
        if table == "hosts":
            for index in range(self.shape.hosts):
                yield partial(_host_column, self._rows, index)
            return

        for host_index in range(self.shape.hosts):
            for index in range(self.shape.services_per_host):
                yield partial(_service_column, self._rows, host_index, index)


def _host_column(rows: RowFactory, index: int, column: str) -> object:
    """One host row's accessor, bound to its index. A ``partial`` rather than a closure so the
    per-row cost stays a C-level call - there is one of these for every row of every site."""
    return rows.host(column, index)


def _service_column(rows: RowFactory, host_index: int, index: int, column: str) -> object:
    return rows.service(column, host_index, index)


def _take[T](items: Iterable[T], count: int) -> Iterator[T]:
    for position, item in enumerate(items):
        if position >= count:
            return
        yield item


def _output_format(query: str) -> str:
    for line in query.splitlines():
        header, _, value = line.partition(":")
        if header == "OutputFormat":
            return value.strip()
    # Livestatus' own default. The GUI always states a format, so this is only reached by
    # something querying the site directly - the Livestatus proxy's heartbeat, for one, which
    # would fail to parse anything else.
    return "csv"


def _encode(rows: Sequence[Sequence[object]], output_format: str) -> bytes:
    match output_format:
        case "python3" | "python":
            return repr([list(row) for row in rows]).encode("utf-8")
        case "json":
            return json.dumps([list(row) for row in rows]).encode("utf-8")
        case "csv":
            # Every row is terminated, the last one included - which is not a detail: the
            # Livestatus proxy's heartbeat rejects a response that does not end in a newline,
            # declares the site dead and closes every connection to it.
            return "".join(";".join(_as_csv(value) for value in row) + "\n" for row in rows).encode(
                "utf-8"
            )
        case _:
            raise UnsupportedQuery(f"output format {output_format!r} is not implemented")


def _as_csv(value: object) -> str:
    """One field in Livestatus' default output: lists comma-joined, dicts as key,value pairs."""
    if isinstance(value, list | tuple):
        return ",".join(str(item) for item in value)
    if isinstance(value, dict):
        return ",".join(f"{key}|{item}" for key, item in value.items())
    return str(value)


def _status_columns(query: str) -> tuple[str, ...]:
    for line in query.splitlines():
        header, _, value = line.partition(":")
        if header == "Columns":
            return tuple(value.split())
    raise UnsupportedQuery("status query without Columns is not served by the fake")
