#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import argparse
import enum
import json
import os
import sys
from pathlib import Path

import requests

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
REQUEST_TIMEOUT = 30


def main() -> None:
    cli = get_cli_parser()
    args = cli.parse_args()

    auth_missing = not args.auth_key or not args.auth_val

    if auth_missing and not args.no_auth:
        err_msg = "Error: Missing auth credentials. Either pass to command or set in environment.\n"
        sys.stderr.write(err_msg)
        cli.print_help()
        sys.exit(ExitCode.INVALID_ARGUMENTS)

    cookies = None if args.no_auth else {args.auth_key: args.auth_val}

    resp = requests.get(args.url, cookies=cookies, timeout=REQUEST_TIMEOUT)

    # Unfortunately, we need to check the history because the redirected response returns 200.
    if resp.history and "login.py" in resp.history[0].headers.get("Location", ""):
        err_msg = "Error: Request was redirected to login page. Did you pass valid credentials?\n"
        sys.stderr.write(err_msg)
        sys.exit(ExitCode.INVALID_ARGUMENTS)

    if args.verbose:
        sys.stdout.write("=" * 60 + "\n")
        sys.stdout.write(f"URL: {args.url}\n")
        sys.stdout.write(f"Status code: {resp.status_code}\n")
        sys.stdout.write(f"Content type: {resp.headers.get('Content-Type')}\n")
        sys.stdout.write("=" * 60 + "\n")

    if "text/html" not in resp.headers.get("Content-Type", ""):
        sys.stderr.write("Error: Can only validate HTML documents. Try another URL.\n")
        sys.exit(ExitCode.INVALID_ARGUMENTS)

    try:
        check_html_tag_balance(str(resp.content))
    except TagImbalanceError as exc:
        err_msg = json.dumps({"url": args.url, "result": exc.get_errors()})
        sys.stderr.write(f"{err_msg}\n")
        sys.exit(ExitCode.VALIDATION_ERRORS)
    else:
        sys.exit(ExitCode.SUCCESS)


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
    main()
