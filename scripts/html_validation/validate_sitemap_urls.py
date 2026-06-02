#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import argparse
import asyncio
import enum
import json
import os
import sys
from collections import Counter
from collections.abc import Iterable
from pathlib import Path
from typing import Any, NamedTuple

import httpx

from scripts.html_validation.lib.exceptions import AuthMissingError
from scripts.html_validation.lib.http import build_auth_cookies, ResponseInfo
from scripts.html_validation.lib.sitemap import parse_gui_crawl_sitemap
from scripts.html_validation.lib.tag_balance import check_html_tag_balance, TagImbalanceError


class ExitCode(enum.IntEnum):
    SUCCESS = 0
    INVALID_ARGUMENTS = 1
    VALIDATION_ERRORS = 2


SCRIPT_NAME = Path(__file__).name
DESCRIPTION = f"""\
This is a utility script that validates HTML for all URLs extracted from a GUI crawl XML file.

The crawl file is produced by the GUI crawl job and contains all URLs visited during the crawl.
Skipped URLs (e.g. javascript: links or svg/png paths) are automatically filtered out.

Basic usage:

    $ python ./scripts/html_validation/{SCRIPT_NAME} crawl.xml

The crawl file records URLs against the host it ran on. Use --base-url to repoint them to your
local site:

    $ python ./scripts/html_validation/{SCRIPT_NAME} crawl.xml --base-url http://localhost/v260

Auth credentials are read from environment variables by default:

    $ export COOKIE_AUTH_KEY=auth_v260
    $ export COOKIE_AUTH_VAL=cmkadmin:cbe4810b...

Or pass them explicitly:

    $ python ... --auth-key $COOKIE_AUTH_KEY --auth-val $COOKIE_AUTH_VAL

Validation errors are written to stderr as one JSON line per failing URL. Pass -v to also print
a summary line to stdout at the end.

The errors are streamed as the script runs. So, if you want to get them in a valid JSON structure,
you can pipe the stderr output into the following `jq` command (don't use --verbose flag):

    $ python ... 2>&1 | jq -s '.'

The following exit codes are supported:

    {ExitCode.SUCCESS}: All URLs passed
    {ExitCode.INVALID_ARGUMENTS}: Invalid arguments
    {ExitCode.VALIDATION_ERRORS}: One or more URLs failed validation
"""
MAX_REQUEST_TIMEOUT = 60
MAX_NUMBER_OF_CONNECTIONS = 20


async def main() -> None:
    cli = get_cli_parser()
    args = cli.parse_args()

    try:
        cookies = build_auth_cookies(args.auth_key, args.auth_val)
    except AuthMissingError as exc:
        sys.stderr.write(f"Error: {exc}\n")
        cli.print_help()
        sys.exit(ExitCode.INVALID_ARGUMENTS)

    urls = parse_gui_crawl_sitemap(Path(args.sitemap), args.base_url)

    if args.verbose:
        print_metadata(
            "Run information",
            [
                Metadata("URLs to validate", len(urls)),
                Metadata("Concurrent connections", args.concurrency),
                Metadata("Request timeout", args.timeout),
            ],
        )

    if not urls:
        sys.stderr.write("Error: No valid URLs found in sitemap.\n")
        sys.exit(ExitCode.INVALID_ARGUMENTS)

    sem = asyncio.Semaphore(args.concurrency)

    skipped_urls = []

    async def validate(client: httpx.AsyncClient, url: str) -> ResultType:
        async with sem:
            try:
                resp = await client.get(url)
            except httpx.RequestError as exc:
                sys.stderr.write(json.dumps({"url": url, "reason": str(exc)}) + "\n")
                sys.stderr.flush()
                return ResultType.FAILED

        resp_info = ResponseInfo.from_response(resp)

        if resp_info.is_redirect_to_login:
            skipped_urls.append({"url": url, "reason": "redirect"})
            return ResultType.SKIPPED

        if resp_info.not_found:
            skipped_urls.append({"url": url, "reason": "not found"})
            return ResultType.SKIPPED

        if not resp_info.is_html_document:
            skipped_urls.append({"url": url, "reason": "non-HTML"})
            return ResultType.SKIPPED

        try:
            check_html_tag_balance(resp.text)
        except TagImbalanceError as exc:
            sys.stderr.write(json.dumps({"url": url, "reason": exc.get_errors()}) + "\n")
            sys.stderr.flush()
            return ResultType.FAILED
        else:
            return ResultType.PASSED

    limits = httpx.Limits(
        max_connections=args.concurrency,
        max_keepalive_connections=args.concurrency,
    )
    async with httpx.AsyncClient(cookies=cookies, timeout=args.timeout, limits=limits) as client:
        results: list[ResultType] = await asyncio.gather(*[validate(client, url) for url in urls])

    result_counts = Counter(str(result) for result in results)

    if args.verbose:
        skipped_urls_text = (
            "\n " + "\n ".join(f"{su['url']} ({su['reason']})" for su in skipped_urls)
            if skipped_urls
            else None
        )
        print_metadata(
            "Results summary",
            [
                Metadata("Result types", dict(result_counts)),
                Metadata("Skipped URLs", skipped_urls_text),
            ],
        )

    if result_counts.get(ResultType.FAILED, 0):
        sys.exit(ExitCode.VALIDATION_ERRORS)

    sys.exit(ExitCode.SUCCESS)


class ResultType(enum.StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


class Metadata(NamedTuple):
    key: str
    value: Any


def print_metadata(title: str, infos: Iterable[Metadata]) -> None:
    half_length = max(0, (60 - len(title) - 2) // 2)
    content = "\n".join(f"{info.key}:\t{info.value}" for info in infos if info.value is not None)

    metadata = f"""\
{"=" * half_length} {title} {"=" * half_length}
{content}
{"=" * (2 * half_length + len(title) + 2)}
"""

    sys.stdout.write(metadata)
    sys.stdout.flush()


def get_cli_parser() -> argparse.ArgumentParser:
    cli = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        prog=SCRIPT_NAME,
        description=DESCRIPTION,
    )
    cli.add_argument(
        "sitemap",
        metavar="FILE",
        help="path to GUI crawl XML file",
    )
    cli.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="print a summary line (N validated, M failed) to stdout at the end",
    )
    cli.add_argument(
        "--base-url",
        metavar="URL",
        help="base URL to repoint crawl URLs to (e.g. http://localhost/v260)",
    )
    cli.add_argument(
        "--timeout",
        type=int,
        default=30,
        choices=range(1, MAX_REQUEST_TIMEOUT + 1),
        metavar=f"[1-{MAX_REQUEST_TIMEOUT}]",
        help="maximum request timeout (default: 30)",
    )
    cli.add_argument(
        "--concurrency",
        type=int,
        default=20,
        choices=range(1, MAX_NUMBER_OF_CONNECTIONS + 1),
        metavar=f"[1-{MAX_NUMBER_OF_CONNECTIONS}]",
        help="maximum concurrent requests (default: 20)",
    )
    cli.add_argument(
        "--auth-key",
        default=os.environ.get("COOKIE_AUTH_KEY"),
        help="session cookie key. (default: COOKIE_AUTH_KEY from env)",
    )
    cli.add_argument(
        "--auth-val",
        default=os.environ.get("COOKIE_AUTH_VAL"),
        help="session cookie value. (default: COOKIE_AUTH_VAL from env)",
    )
    return cli


if __name__ == "__main__":
    asyncio.run(main())
