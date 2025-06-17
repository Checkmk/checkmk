#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import argparse
import sys
import urllib.parse
from collections.abc import Sequence
from pathlib import Path

import requests
import urllib3

from cmk.utils import password_store

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# TODO: use these:
__version__ = "2.5.0b1"
USER_AGENT = f"checkmk-active-elasticsearch-query-{__version__}"


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_arguments(argv)
    auth = _make_auth(args.user, args.password, args.password_id)
    try:
        msg, state, perfdata = handle_request(args, auth)
    except Exception as exc:
        sys.stdout.write("UNKNOWN - %s\n" % exc)
        return 3

    sys.stdout.write(f"{msg} | {perfdata}\n")
    return state


def _make_auth(
    user: str | None,
    password: str | None,
    password_ref: str | None,
) -> tuple[str, str] | None:
    if user is None:
        return None
    if password is not None:
        return (user, password)
    if password_ref is not None:
        pw_id, pw_file = password_ref.split(":", 1)
        return (user, password_store.lookup(Path(pw_file), pw_id))
    return None


def handle_request(args: argparse.Namespace, auth: tuple[str, str] | None) -> tuple[str, int, str]:
    url = urllib.parse.urlunparse(
        (
            args.protocol,
            "%s:%d" % (args.hostname, args.port),
            "%s/_count" % args.index.replace(" ", ","),
            None,
            None,
            None,
        )
    )

    query = {
        "query": {
            "bool": {
                "must": [
                    {"query_string": {"query": args.pattern}},
                    {"range": {"@timestamp": {"gte": "now-%ds" % args.timerange, "lt": "now"}}},
                ]
            }
        },
    }

    if args.fieldname:
        query["query"]["bool"]["must"][0]["query_string"]["fields"] = args.fieldname.split(" ")

    raw_response = requests.get(
        url, json=query, auth=auth, timeout=900, verify=args.verify_tls_cert
    )

    msg, state, perfdata = handle_query(
        raw_response,
        _handle_level_command_line_args(args.warn_upper_log_count, args.crit_upper_log_count),
        _handle_level_command_line_args(args.warn_lower_log_count, args.crit_lower_log_count),
    )

    return msg, state, perfdata


def _handle_level_command_line_args(
    warn: float | None, crit: float | None
) -> tuple[float, float] | None:
    return (warn, crit) if warn is not None and crit is not None else None


def _check_lower_levels(
    value: float,
    levels: tuple[float, float] | None,
) -> tuple[int, str]:
    if levels:
        lower_level_state = 2 if value < levels[1] else 1 if value < levels[0] else 0
        if lower_level_state > 0:
            return lower_level_state, "(warn/crit below %d/%d)" % levels
    return 0, ""


def _check_upper_levels(
    value: float,
    levels: tuple[float, float] | None,
) -> tuple[int, str]:
    if levels:
        upper_level_state = 2 if value >= levels[1] else 1 if value >= levels[0] else 0
        if upper_level_state > 0:
            return upper_level_state, "(warn/crit at %d/%d)" % levels
    return 0, ""


def _check_levels(
    value: float,
    label: str,
    metric_name: str,
    upper_levels: tuple[float, float] | None,
    lower_levels: tuple[float, float] | None,
) -> tuple[str, int, str]:
    msg = f"{label}: {value}"

    upper_level_state, upper_level_msg = _check_upper_levels(value, upper_levels)
    if upper_level_msg:
        msg += f" {upper_level_msg}"

    lower_level_state, lower_level_msg = _check_lower_levels(value, lower_levels)
    if lower_level_msg:
        msg += f" {lower_level_msg}"

    return (
        msg,
        max(upper_level_state, lower_level_state),
        f"{metric_name}={value}",
    )


def handle_query(
    raw_response: requests.Response,
    upper_levels: tuple[float, float] | None,
    lower_levels: tuple[float, float] | None,
) -> tuple[str, int, str]:
    response_data = raw_response.json()

    if "count" not in response_data:
        raise ValueError("Missing section count in raw response data")

    return _check_levels(response_data["count"], "Messages", "count", upper_levels, lower_levels)


def parse_arguments(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )

    parser.add_argument(
        "-u",
        "--user",
        default=None,
        help="Username for elasticsearch login",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "-s",
        "--password",
        default=None,
        help="Password for easticsearch login. Preferred over --password-id",
    )
    group.add_argument(
        "--password-id",
        default=None,
        help="Password store reference to the password for easticsearch login",
    )
    parser.add_argument(
        "-P",
        "--protocol",
        default="https",
        help="Use 'http' or 'https' for connection to elasticsearch (default=https)",
    )
    parser.add_argument(
        "-p",
        "--port",
        type=int,
        default=9200,
        help="Use alternative port (default: 9200)",
    )
    parser.add_argument(
        "-q",
        "--pattern",
        help=("Search pattern"),
    )
    parser.add_argument(
        "-f",
        "--fieldname",
        default=None,
        help=("Fieldname to query"),
    )
    parser.add_argument(
        "-i",
        "--index",
        help=("Index to query"),
        default="_all",
    )
    parser.add_argument(
        "-t",
        "--timerange",
        type=int,
        default=60,
        help=("The timerange to query, eg. x minutes from now."),
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help=("Debug mode: let Python exceptions come through"),
    )
    parser.add_argument(
        "--warn-upper-log-count",
        type=int,
        default=None,
        help=("number of log messages above which the check will warn"),
    )
    parser.add_argument(
        "--crit-upper-log-count",
        type=int,
        default=None,
        help=("number of log messages above which the check will become critical"),
    )
    parser.add_argument(
        "--warn-lower-log-count",
        type=int,
        default=None,
        help=("number of log messages below which the check will warn"),
    )
    parser.add_argument(
        "--crit-lower-log-count",
        type=int,
        default=None,
        help=("number of log messages below which the check will become critical"),
    )
    parser.add_argument(
        "-H",
        "--hostname",
        help=("Defines the elasticsearch instances to query."),
    )
    parser.add_argument(
        "--verify-tls-cert",
        type=bool,
        default=True,
        action=argparse.BooleanOptionalAction,
        help=("Enable or disable TLS cert validation."),
    )

    return parser.parse_args(argv)
