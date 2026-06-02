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
from pathlib import Path

import httpx

from scripts.html_validation.lib.exceptions import AuthMissingError
from scripts.html_validation.lib.http import build_auth_cookies, ResponseInfo
from scripts.html_validation.lib.tag_balance import check_html_tag_balance, TagImbalanceError


class ExitCode(enum.IntEnum):
    SUCCESS = 0
    INVALID_ARGUMENTS = 1
    VALIDATION_ERRORS = 2


SCRIPT_NAME = Path(__file__).name
DESCRIPTION = f"""\
This is a utility script that helps to validate whether a page is rendering valid HTML.

You will first need to fetch a valid auth cookie from a logged in session. You then will either want
to store these in environment variables: `COOKIE_AUTH_KEY` and `COOKIE_AUTH_VAL` so that the script
will automatically fetch them from your environment:

    $ export COOKIE_AUTH_KEY=auth_v260
    $ export COOKIE_AUTH_VAL=cmkadmin:cbe4810b...

Then when you call the command, you don't need to pass them explicitly:

    $ URL="http://localhost/v260/check_mk/dashboard.py?name=main&owner="
    $ python ./scripts/html_validation/{SCRIPT_NAME} $URL

However, you can always pass the auth explicitly via the `--auth-key` and `--auth-val` flags:

    $ python ... --auth-key $COOKIE_AUTH_KEY --auth-val $COOKIE_AUTH_VAL

By default, the script will use this authentication cookie, but for some endpoints, you don't want
to pass them, e.g. the login page. To override this behavior, you need to pass the `--no-auth` flag.
Also by default, the script will only output to standard output if there are errors. This is
intended to make the script more composable with other utilities.

If you want to see more information regarding the response, pass the `-v` or `--verbose` flag when
calling.

The following exit codes are supported by the script:

    {ExitCode.SUCCESS}: Success
    {ExitCode.INVALID_ARGUMENTS}: Invalid arguments
    {ExitCode.VALIDATION_ERRORS}: Validation errors

This is useful if you want to just collect all the URLs that resulted in errors. Use the `$?` in
bash to extract this value.
"""
MAX_REQUEST_TIMEOUT = 60


async def main() -> None:
    cli = get_cli_parser()
    args = cli.parse_args()

    try:
        cookies = build_auth_cookies(args.auth_key, args.auth_val, args.no_auth)
    except AuthMissingError as exc:
        sys.stderr.write(f"Error: {exc}\n")
        cli.print_help()
        sys.exit(ExitCode.INVALID_ARGUMENTS)

    async with httpx.AsyncClient(cookies=cookies, timeout=args.timeout) as client:
        resp = await client.get(args.url)

    resp_info = ResponseInfo.from_response(resp)

    if args.verbose:
        print_response_info(resp_info)

    if resp_info.is_redirect_to_login:
        err_msg = f"Request redirected to {resp_info.redirect_location}. Did you pass credentials?"
        sys.stderr.write(f"Error: {err_msg}\n")
        sys.exit(ExitCode.INVALID_ARGUMENTS)

    if not resp_info.is_html_document:
        sys.stderr.write("Error: Can only validate HTML documents. Try another URL.\n")
        sys.exit(ExitCode.INVALID_ARGUMENTS)

    try:
        check_html_tag_balance(resp.text)
    except TagImbalanceError as exc:
        err_msg = json.dumps({"url": args.url, "result": exc.get_errors()})
        sys.stderr.write(f"{err_msg}\n")
        sys.exit(ExitCode.VALIDATION_ERRORS)
    else:
        sys.exit(ExitCode.SUCCESS)


def print_response_info(info: ResponseInfo) -> None:
    sys.stdout.write("=" * 60 + "\n")
    sys.stdout.write(f"URL: {info.url}\n")
    sys.stdout.write(f"Status code: {info.status_code}\n")
    sys.stdout.write(f"Content type: {info.content_type}\n")
    sys.stdout.write("=" * 60 + "\n")


def get_cli_parser() -> argparse.ArgumentParser:
    cli = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        prog=SCRIPT_NAME,
        description=DESCRIPTION,
    )
    cli.add_argument(
        "url",
        help="URL of the page to check.",
    )
    cli.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="flag to print out additional information.",
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
        "--no-auth",
        action="store_true",
        help="flag to not provide auth cookies",
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
