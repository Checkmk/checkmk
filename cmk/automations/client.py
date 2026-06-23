#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""CLI to send a command to the running automation-helper daemon and print its raw JSON response.

This talks to the long-running automation helper over its unix socket instead of spawning a fresh
``cmk --automation`` process, which makes it convenient for debugging the helper itself or
reproducing behavior against its cached configuration and plugins.

This is an internal debugging tool and NOT a stable API: its name, arguments, behavior and output
may change or be removed at any time without notice.
"""

import argparse
import logging
import os
import sys
from pathlib import Path

import requests

from cmk.automations.models.helper import (
    AUTOMATION_HELPER_BASE_URL,
    AUTOMATION_HELPER_SOCKET_RELATIVE_PATH,
    AutomationPayload,
)
from cmk.automations.types import AutomationID
from cmk.utils.unixsocket_http import make_session


def _socket_path() -> Path:
    try:
        omd_root = os.environ["OMD_ROOT"]
    except KeyError:
        sys.stderr.write("OMD_ROOT is not set; run this inside a site.\n")
        raise SystemExit(2)
    return Path(omd_root) / AUTOMATION_HELPER_SOCKET_RELATIVE_PATH


def _parse_arguments(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=(
            "Send a command to the running automation-helper daemon and print its raw "
            "JSON response. Standard input is forwarded to the automation when piped.\n"
            "\n"
            "WARNING: This is an internal debugging tool, NOT a stable API. Its name, "
            "arguments, behavior and output may change or be removed at any time without "
            "notice. Do not build scripts, integrations or automation on top of it."
        ),
        epilog=("Internal debugging use only — no compatibility guarantees of any kind."),
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--health",
        action="store_true",
        help="query the GET /health endpoint instead of running an automation",
    )
    mode.add_argument(
        "command",
        nargs="*",  # yes, '*'. The 'required=True' of the group makes it effectively '+'
        default=[],
        metavar="COMMAND [ARG ...]",
        help="automation command name followed by its arguments",
    )
    parser.add_argument(
        "--log-level",
        choices=["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"],
        default="INFO",
        help=(
            "log level forwarded to the helper when running an automation; "
            "ignored with --health (default: %(default)s)"
        ),
    )
    return parser.parse_args(argv)


def main() -> int:
    args = _parse_arguments(sys.argv[1:])
    socket_path = _socket_path()
    session = make_session(socket_path, AUTOMATION_HELPER_BASE_URL)

    try:
        if args.health:
            response = session.get(f"{AUTOMATION_HELPER_BASE_URL}/health", timeout=10.0)
        else:
            command, *automation_args = args.command
            stdin = "" if sys.stdin.isatty() else sys.stdin.read()
            payload = AutomationPayload(
                name=AutomationID(command),
                args=automation_args,
                stdin=stdin,
                log_level=logging.getLevelNamesMapping()[args.log_level],
            ).model_dump(mode="json")
            response = session.post(f"{AUTOMATION_HELPER_BASE_URL}/automation", json=payload)
    except requests.ConnectionError as e:
        sys.stderr.write(
            f"Could not connect to automation helper at {socket_path}. "
            f"Is the 'automation-helper' site service running? Error: {e}\n"
        )
        return 2

    sys.stdout.write(response.text.rstrip("\n") + "\n")
    return 0 if response.ok else 1


if __name__ == "__main__":
    sys.exit(main())
