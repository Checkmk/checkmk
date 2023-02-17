#!/usr/bin/env python3
# Copyright (C) 2023 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import calendar
import enum
import itertools
import time
import typing

import feedparser  # type:ignore[import]
import pydantic

from cmk.utils import aws_constants  # pylint: disable=[cmk-module-layer-violation]

from cmk.base.plugins.agent_based.agent_based_api import v1
from cmk.base.plugins.agent_based.agent_based_api.v1 import type_defs


class TitleType(enum.StrEnum):
    """Serverity of a problem indicate by an rss entry.

    From interacting with https://health.aws.amazon.com/health/status it seems, that AWS uses
    these prefixes to indicate the severity of an entry.

    `OK`, `Performance issues` and `Service disruption` were obtained by googling a little, I was
    unable to retrieve real rss data with the messages.
    """

    informational = "Informational message"
    normal = "Service is operating normally"
    ok = "OK"
    performance = "Performance issues"
    disruption = "Service disruption"


Seconds = typing.NewType("Seconds", float)

_IGNORE_ENTRIES_OLDER_THAN = Seconds(60 * 60 * 24 * 3)  # Product-Management decision


class Entry(pydantic.BaseModel):
    """RSS scheme.

    External format, which we obtain from AWS and parse with feedparser.
    """

    title: str
    published_parsed: time.struct_time
    published: str
    summary: str
    link: str
    id_: str = pydantic.Field(alias="id")

    def service_region_id(self) -> str:
        id_suffix = self.id_.removeprefix(self.link)
        return id_suffix.rsplit(sep="_", maxsplit=1)[0]

    def region(self) -> str:
        id_suffix = self.id_.removeprefix(self.link)
        for internal_region, display_region in aws_constants.AWSRegions:
            if internal_region in id_suffix:
                return display_region
        # Global is indicated by omitting the region id
        return "Global"


class AWSRSSFeed(pydantic.BaseModel):
    """RSS scheme.

    External format, which we obtain from AWS and parse with feedparser.
    """

    entries: list[Entry]

    @classmethod
    def parse_rss(cls, element: str) -> "AWSRSSFeed":
        return cls.parse_obj(feedparser.parse(element))


class AgentOutput(pydantic.BaseModel):
    """Section scheme: aws_health

    Internal json, which is used to forward the rss feed between agent_aws_health and the parse
    function.
    """

    rss_str: str


def parse_string_table(string_table: type_defs.StringTable) -> AWSRSSFeed:
    agent_output = AgentOutput.parse_raw(string_table[0][0])
    return AWSRSSFeed.parse_rss(agent_output.rss_str)


class SortedEntries(list[Entry]):
    """RSS entries sorted by their age.

    The newest entry must be the first entry.
    """


v1.register.agent_section(
    name="aws_health",
    parse_function=parse_string_table,
)


def discover_aws_health(section: AWSRSSFeed) -> type_defs.DiscoveryResult:
    yield v1.Service(item="Global")
    for _id, region in aws_constants.AWSRegions:
        yield v1.Service(item=region)


def check_aws_health(item: str, section: AWSRSSFeed) -> type_defs.CheckResult:
    yield from _check_aws_health(Seconds(time.time()), item, section)


def _check_aws_health(
    current_time: Seconds,
    item: str,
    section: AWSRSSFeed,
) -> type_defs.CheckResult:
    entries_for_region = _restrict_to_region(section.entries, item)
    relevant_entries = _obtain_recent_entries(
        current_time,
        _sort_newest_entry_first(entries_for_region),
    )
    if relevant_entries:
        for group in _group_by_service_identifier(relevant_entries):
            yield from _check_aws_health_for_service(group)
    else:
        yield v1.Result(state=v1.State.OK, summary="No issues")


def _restrict_to_region(entries: list[Entry], region: str) -> list[Entry]:
    return [e for e in entries if e.region() == region]


def _sort_newest_entry_first(entries: list[Entry]) -> SortedEntries:
    def key(entry: Entry) -> time.struct_time:
        return entry.published_parsed

    return SortedEntries(sorted(entries, key=key, reverse=True))


def _obtain_recent_entries(
    current_time: Seconds,
    entries: SortedEntries,
    ignore_entries_older_than: Seconds = _IGNORE_ENTRIES_OLDER_THAN,
) -> SortedEntries:
    smallest_accepted_time = current_time - ignore_entries_older_than
    for i, e in enumerate(entries):
        if calendar.timegm(e.published_parsed) < smallest_accepted_time:
            return SortedEntries(entries[:i])
    return entries


def _group_by_service_identifier(entries: SortedEntries) -> list[SortedEntries]:
    def sort_key(entry: Entry) -> tuple[str, time.struct_time]:
        return entry.service_region_id(), entry.published_parsed

    def group_key(entry: Entry) -> str:
        return entry.service_region_id()

    return [
        SortedEntries(group)  # correct by definition of `sort_key`
        for _service_region_id, group in itertools.groupby(
            sorted(entries, key=sort_key, reverse=True),
            key=group_key,
        )
    ]


def _check_aws_health_for_service(entries: SortedEntries) -> type_defs.CheckResult:
    newest_entry = entries[0]
    yield v1.Result(state=_state_from_entry(newest_entry), summary=newest_entry.title)
    for entry in entries:
        yield v1.Result(state=v1.State.OK, notice=f"{entry.published}: {entry.summary}")


def _state_from_entry(entry: Entry) -> v1.State:
    if entry.title.startswith(TitleType.ok) or entry.title.startswith(TitleType.normal):
        return v1.State.OK
    return v1.State.WARN


v1.register.check_plugin(
    name="aws_health",
    # TODO: CMK-8322
    service_name="AWS Health %s",
    discovery_function=discover_aws_health,
    check_function=check_aws_health,
)
