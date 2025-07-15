#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Check Checkmk BI aggregations"""

import argparse
import json
import os
import sys
import time
import traceback
from collections.abc import Sequence
from pathlib import Path

import requests
import urllib3

from cmk.ccc.user import UserId

from cmk.utils import password_store
from cmk.utils.local_secrets import AutomationUserSecret

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def parse_arguments(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument(
        "-b",
        "--base-url",
        metavar="BASE_URL",
        required=True,
        help="The base URL to the monitoring environment, e.g. http://<hostname>/<site-id>",
    )
    parser.add_argument(
        "-a",
        "--aggr-name",
        metavar="AGGR_NAME",
        required=True,
        help=(
            "Name of the aggregation, not the aggregation group."
            " It is possible that there are multiple aggregations with an equal name,"
            " but you should ensure that it is a unique one to prevent confusion."
        ),
    )
    parser.add_argument(
        "-u",
        "--user-name",
        metavar="USER",
        required=False,  # depends on --use-automation-user
        help=(
            "User ID of an automation user which is permitted to see all contents of the aggregation."
        ),
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--secret-reference",
        help="Password store reference of the automation secret of the user.",
    )
    group.add_argument(
        "-s",
        "--secret",
        metavar="SECRET",
        help="Automation secret of the user.",
    )
    parser.add_argument(
        "--use-automation-user",
        action="store_true",
        help="Use credentials from the local 'automation' user.",
    )
    parser.add_argument(
        "-m",
        "--auth-mode",
        metavar="AUTH_MODE",
        default="header",
        # Kerberos auth support was removed with 2.4.0 but kept here to show a helpful error message
        # in case a user still has configured it. Can be removed with 2.5.
        choices=["basic", "digest", "header", "kerberos"],
        help="Authentication mode, defaults to 'header'.",
    )
    parser.add_argument(
        "-t",
        "--timeout",
        metavar="TIMEOUT",
        type=int,
        default=60,
        help="HTTP connect timeout in seconds (Default: 60).",
    )
    parser.add_argument(
        "-r",
        "--track-downtimes",
        action="store_true",
        help="Track downtimes. This requires the hostname to be set.",
    )
    parser.add_argument(
        "-n",
        "--hostname",
        metavar="HOSTNAME",
        default=None,
        help="The hostname for which this check is run.",
    )
    parser.add_argument(
        "--in-downtime",
        metavar="S",
        choices=["normal", "ok", "warn"],
        default="normal",
        help=(
            "S can be 'ok' or 'warn'. Force this state if the aggregate is in scheduled downtime."
            " OK states will always be unchanged."
        ),
    )
    parser.add_argument(
        "--acknowledged",
        metavar="S",
        choices=["normal", "ok", "warn"],
        default="normal",
        help=("Same as --in-downtime, but for acknowledged aggregates."),
    )
    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="Enable debug mode.",
    )

    return parser.parse_args(argv)


def _make_credentials(args: argparse.Namespace) -> tuple[str, str]:
    if args.use_automation_user:
        try:
            return "automation", AutomationUserSecret(UserId("automation")).read()
        except (OSError, ValueError):
            sys.stderr.write('Unable to read credentials for "automation" user.\n')
            sys.exit(1)

    if (user := args.user_name) is None:
        sys.stderr.write("Please provide a valid user name.\n")
        sys.exit(1)

    if (ref := args.secret_reference) is not None:
        pw_id, pw_file = ref.split(":", 1)
        return user, password_store.lookup(Path(pw_file), pw_id)

    if args.secret is not None:
        return user, args.secret

    sys.stderr.write("Please provide a valid login secret.\n")
    sys.exit(1)


# returning int requires more refactoring atm
def main(argv: Sequence[str]) -> None:
    args = parse_arguments(argv=argv)

    username, secret = _make_credentials(args=args)

    if args.track_downtimes and not args.hostname:
        sys.stderr.write("Please provide a hostname when using downtime tracking.\n")
        sys.exit(1)

    def init_auth(pw: str) -> requests.auth.AuthBase | None:
        match args.auth_mode:
            case "kerberos":
                raise ValueError(
                    "Kerberos auth is not supported anymore. Please have a look at "
                    "werk #16569 for further information."
                )
            case "digest":
                return requests.auth.HTTPDigestAuth(username, pw)
            case "basic":
                return requests.auth.HTTPBasicAuth(username, pw)
            case "header":
                return None
            case other:
                raise ValueError(f"Unknown auth mode: {other!r}")

    endpoint_url = f"{args.base_url.rstrip('/')}/check_mk/api/1.0/domain-types/bi_aggregation/actions/aggregation_state/invoke"

    auth = init_auth(secret)

    if args.debug:
        sys.stderr.write("URL: %s\n" % endpoint_url)

    try:
        r = requests.post(
            endpoint_url,
            timeout=args.timeout,
            auth=auth,
            headers={"Authorization": f"Bearer {username} {secret}"} if not auth else None,
            json={"filter_names": [args.aggr_name]},
        )
        r.raise_for_status()
        raw_response = r.text
    except requests.Timeout:
        sys.stdout.write("ERROR: Socket timeout while opening URL: %s\n" % (endpoint_url))
        sys.exit(3)
    except requests.URLRequired as e:
        sys.stdout.write("UNKNOWN: %s\n" % e)
        sys.exit(3)
    except Exception as e:
        sys.stdout.write(
            f"ERROR: Exception while opening URL: {endpoint_url} - {e}\n{traceback.format_exc()}"
        )
        sys.exit(3)

    try:
        response_data = json.loads(raw_response)
    except Exception as e:
        sys.stdout.write(f"ERROR: Invalid response ({e}): {raw_response}\n")
        sys.exit(3)

    try:
        aggr_state = response_data["aggregations"][args.aggr_name]["state"]
    except KeyError:
        sys.stdout.write(
            f"ERROR Aggregation {args.aggr_name} does not exist or user is not permitted"
        )
        sys.exit(3)

    if aggr_state == -1:
        aggr_state = 3

    aggr_output = "Aggregation state is %s" % ["OK", "WARN", "CRIT", "UNKNOWN"][aggr_state]

    # Handle downtimes and acknowledgements
    is_aggr_in_downtime = response_data["aggregations"][args.aggr_name]["in_downtime"]
    if args.in_downtime != "normal" and is_aggr_in_downtime:
        aggr_output += ", currently in downtime"
        if args.in_downtime == "ok":
            aggr_state = 0
        else:  # "warn"
            aggr_state = min(aggr_state, 1)

    if args.track_downtimes:
        # connect to livestatus
        try:
            import livestatus
        except ImportError:
            sys.stderr.write(
                "The python livestatus api module is missing. Please install from\n"
                "Check_MK livestatus sources to a python import path.\n"
            )
            sys.exit(1)

        socket_path = Path(os.environ["OMD_ROOT"]) / "tmp/run/live"

        conn = livestatus.SingleSiteConnection(f"unix:{socket_path}")

        now = time.time()
        # find out if, according to previous tracking, there already is a downtime
        ids = conn.query_table(
            (
                "GET downtimes\n"
                "Columns: id\n"
                "Filter: host_name = %s\n"
                "Filter: service_description = %s\n"
                "Filter: author = tracking\n"
                "Filter: end_time > %d"
            )
            % (args.hostname, args.aggr_name, now)
        )
        downtime_tracked = len(ids) > 0
        if downtime_tracked != is_aggr_in_downtime:
            # there is a discrepance between tracked downtime state and the real state
            if is_aggr_in_downtime:
                # need to track downtime
                conn.command(
                    "[%d] SCHEDULE_SVC_DOWNTIME;%s;%s;%d;%d;1;0;0;"
                    "tracking;Automatic downtime"
                    % (now, args.hostname, args.aggr_name, now, 2147483647)
                )
            else:
                for dt_id in ids:
                    conn.command("[%d] DEL_SVC_DOWNTIME;%d" % (now, dt_id[0]))

    is_aggr_acknowledged = response_data["aggregations"][args.aggr_name]["acknowledged"]
    if args.acknowledged != "normal" and is_aggr_acknowledged:
        aggr_output += ", is acknowledged"
        if args.acknowledged == "ok":
            aggr_state = 0
        else:  # "warn"
            aggr_state = min(aggr_state, 1)

    sys.stdout.write("%s\n" % aggr_output)
    sys.exit(aggr_state)
