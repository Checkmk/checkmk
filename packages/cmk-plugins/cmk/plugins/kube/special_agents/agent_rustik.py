#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""agent_rustik

Checkmk special agent for the Kubernetes 3.0 pull-mode backend ("rustik"): a thin
HTTP client that connects to the rustik endpoint and prints the sections it returns
to stdout. It lives alongside the classic agent_kube and shares the same check plugins.
"""

import argparse
import logging
import sys
from collections.abc import MutableMapping, Sequence

import requests
import urllib3

from cmk.password_store.v1_unstable import parser_add_secret_option, resolve_secret_option
from cmk.server_side_programs.v1_unstable import report_agent_crashes, vcrtrace

__version__ = "3.0.0b1"

AGENT = "rustik"

SECRET_OPTION = "secret"

USER_AGENT = f"checkmk-special-{AGENT}-{__version__}"

LOGGER = logging.getLogger("agent_rustik")


def _to_requests_proxies(raw: str) -> MutableMapping[str, str]:
    match raw:
        case "NO_PROXY":
            return {"http": "", "https": ""}
        case "FROM_ENVIRONMENT":
            return {}
        case url:
            return {"http": url, "https": url}


def parse_arguments(argv: Sequence[str]) -> argparse.Namespace:
    prog, description = __doc__.split("\n\n")
    parser = argparse.ArgumentParser(prog=prog, description=description)
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Log the communication path to rustik and raise Python exceptions.",
    )
    parser.add_argument(
        "--vcrtrace",
        "--tracefile",
        default=False,
        action=vcrtrace(filter_headers=[("authorization", "****")]),
        help="Record the HTTP communication to a VCR cassette for debugging.",
    )
    parser.add_argument(
        "--proxy",
        default="FROM_ENVIRONMENT",
        help=(
            "HTTP proxy used to connect to rustik. If not set, the environment settings "
            "will be used."
        ),
    )
    parser.add_argument(
        "--connect-timeout",
        type=float,
        default=10.0,
        help="TCP connect timeout in seconds (default: 10).",
    )
    parser.add_argument(
        "--read-timeout",
        type=float,
        default=30.0,
        help="TCP read timeout in seconds (default: 30).",
    )
    parser.add_argument(
        "--no-cert-check",
        action="store_true",
        help=(
            "Disable SSL certificate verification (certificate verification is enabled by default)."
        ),
    )
    parser_add_secret_option(
        parser,
        short="-s",
        long=f"--{SECRET_OPTION}",
        help="Shared secret for authenticating against rustik.",
        required=False,
    )
    parser.add_argument(
        "url",
        metavar="URL",
        help="The rustik endpoint to fetch the sections from.",
    )
    return parser.parse_args(argv)


def setup_logging(debug: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.WARNING,
        stream=sys.stderr,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    if debug:
        # Surface the wire-level request/response path (still on stderr).
        logging.getLogger("urllib3").setLevel(logging.DEBUG)


@report_agent_crashes(AGENT, __version__)
def main() -> int:
    args = parse_arguments(sys.argv[1:])
    setup_logging(args.debug)

    proxies = _to_requests_proxies(args.proxy)

    if args.no_cert_check:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    headers = {"User-Agent": USER_AGENT}
    if args.secret is not None or args.secret_id is not None:
        # Bearer token, as accepted by rustik's pull endpoint (and matching agent_kube).
        headers["Authorization"] = f"Bearer {resolve_secret_option(args, SECRET_OPTION).reveal()}"

    LOGGER.info("Fetching sections from rustik at %(url)s", {"url": args.url})

    try:
        response = requests.get(
            args.url,
            headers=headers,
            proxies=proxies,
            timeout=(args.connect_timeout, args.read_timeout),
            verify=not args.no_cert_check,
        )
        response.raise_for_status()
    except requests.exceptions.RequestException as error:
        sys.stderr.write(f"Error fetching data from rustik: {error}\n")
        if args.debug:
            raise
        return 1

    LOGGER.info(
        "rustik responded with %(status)s %(reason)s (%(bytes)d bytes in %(seconds).3fs)",
        {
            "status": response.status_code,
            "reason": response.reason,
            "bytes": len(response.content),
            "seconds": response.elapsed.total_seconds(),
        },
    )

    # For now we print rustik's response body as-is.
    sys.stdout.write(response.text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
