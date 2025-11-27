#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""agent_azure_status

Checkmk special agent for monitoring Azure service status.
"""

# mypy: disable-error-code="no-untyped-call"

import argparse
import json
import sys
from collections.abc import Iterable, Iterator, Sequence

import feedparser
import requests
from feedparser.util import FeedParserDict
from lxml.html import fromstring
from pydantic import BaseModel

from cmk.plugins.azure_status.lib.azure_regions import AZURE_REGIONS
from cmk.server_side_programs.v1_unstable import report_agent_crashes, vcrtrace

__version__ = "2.5.0b1"

AGENT = "azure_status"


class AzureIssue(BaseModel, frozen=True):
    region: str
    title: str
    description: str


class AzureStatus(BaseModel, frozen=True):
    link: str
    regions: Sequence[str]
    issues: Sequence[AzureIssue]


def parse_arguments(argv: Sequence[str] | None) -> argparse.Namespace:
    prog, description = __doc__.split("\n\n", maxsplit=1)
    parser = argparse.ArgumentParser(
        prog=prog, description=description, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "--debug",
        "-d",
        action="store_true",
        help="Enable debug mode (keep some exceptions unhandled)",
    )
    parser.add_argument("--verbose", "-v", action="count", default=0)
    parser.add_argument(
        "--vcrtrace",
        "--tracefile",
        default=False,
        action=vcrtrace(
            # This is the result of a refactoring.
            # I did not check if it makes sense for this special agent.
            filter_headers=[("authorization", "****")],
        ),
    )
    parser.add_argument(
        "regions",
        type=str,
        nargs="*",
        metavar="REGION1 REGION2",
        help="Monitored Azure regions",
    )

    return parser.parse_args(argv)


def get_affected_regions(all_regions: Iterable[str], entry: FeedParserDict) -> set[str]:
    """Fetch regions affected by the issue

    Some regions are substrings of other regions e.g. (Central US of North Central US).
    This function makes sure that we don't return both regions when only the one with
    the longer name is present.
    all_regions list has to be sorted by length to produce a correct result.
    """
    affected_regions = set()
    title, summary = entry.title, entry.summary
    tags = entry.get("tags")

    for region in all_regions:
        if region in title:
            affected_regions.add(region)
            title = title.replace(region, "")

        if region in summary:
            affected_regions.add(region)
            summary = summary.replace(region, "")

        if tags is not None:
            if any(t for t in tags if t["term"] == region):
                affected_regions.add(region)

    return affected_regions


def get_azure_issues(
    entries: Iterable[FeedParserDict], selected_regions: list[str]
) -> Iterator[AzureIssue]:
    all_regions = sorted(list(AZURE_REGIONS.values()), key=len, reverse=True)

    for entry in entries:
        affected_regions = get_affected_regions(all_regions, entry)
        summary = fromstring(entry.summary).text_content()

        if not affected_regions:
            yield AzureIssue(region="Global", title=entry.title, description=summary)

        for region in affected_regions:
            if region in selected_regions:
                yield AzureIssue(region=region, title=entry.title, description=summary)


def write_section(args: argparse.Namespace) -> int:
    response = requests.get("https://status.azure.com/en-us/status/feed/", timeout=900)
    feed = feedparser.parse(response.text)  # type: ignore[attr-defined]

    selected_regions = [AZURE_REGIONS[r] for r in args.regions]
    selected_regions.append("Global")
    azure_issues = list(get_azure_issues(feed.entries, selected_regions))

    azure_status = AzureStatus(link=feed.feed.link, regions=selected_regions, issues=azure_issues)

    section_payload = json.dumps(azure_status.model_dump(), sort_keys=True)
    sys.stdout.write(f"<<<azure_status:sep(0)>>>\n{section_payload}\n")
    return 0


@report_agent_crashes(AGENT, __version__)
def main() -> int:
    return write_section(parse_arguments(sys.argv[1:]))


if __name__ == "__main__":
    main()
