#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Scrape Werks from changes listed in Checkmk repository."""

import os
import re
from argparse import ArgumentParser, Namespace
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from scripts.gerrit_api.client import GerritClient, TChangeStatus
from scripts.gerrit_api.werks import werk_details, WerkImpact

ENV_GERRIT_USER: Final = "GERRIT_USER"
ENV_GERRIT_HTTP_CREDS: Final = "GERRIT_HTTP_CREDS"
# TODO: improve detection of master branch's version.
MASTER_BRANCH: Final = "2.5.0"


class TCliArgs(Namespace):
    age: int
    cmk_version: str
    dir_csv: str
    http_creds: str
    status: str
    username: str


@dataclass(frozen=True)
class CSVEntry:
    change_id: int
    change_status: TChangeStatus
    werk_id: str
    werk_summary: str
    werk_impact: WerkImpact


def parsed_arguments() -> type[TCliArgs]:
    """Parse arguments from the CLI or the environment variables."""
    parser = ArgumentParser(description=__doc__)

    # required arguments

    def cmk_version(value: str) -> str:
        """Validate Checkmk version provided to the script follows an expected convention."""
        if not re.findall(r"2\.\d+\.0(?:[bp]\d+)*$", value.strip()):
            raise ValueError
        return value

    parser.add_argument(
        "--cmk-version",
        dest="cmk_version",
        metavar="2.M.0[pN,bN]",
        type=cmk_version,
        help="List werks corresponding to a certain Checkmk version. M, N are positive integers.",
        required=True,
    )

    # optional arguments

    def gerrit_username(value: str) -> str:
        """Initialize username using the environment variable, if necessary."""
        user = value or os.getenv(ENV_GERRIT_USER, "")
        if not user:
            raise ValueError(f"Initialize `{ENV_GERRIT_USER}` to read the gerrit username!")
        return user

    parser.add_argument(
        "--username",
        dest="username",
        metavar=ENV_GERRIT_USER,
        type=gerrit_username,
        default="",
        help=(
            "Provide the username corresponding to the gerrit-account. "
            f"By default, use the one defined within environment variable `{ENV_GERRIT_USER}`."
        ),
    )

    def http_creds(value: str) -> str:
        creds = value or os.getenv(ENV_GERRIT_HTTP_CREDS, "")
        if not creds:
            raise ValueError(
                f"Initialize `{ENV_GERRIT_HTTP_CREDS}` to read user specific "
                "gerrit HTTP credentials!"
            )
        return creds

    parser.add_argument(
        "--http-creds",
        dest="http_creds",
        metavar=ENV_GERRIT_HTTP_CREDS,
        type=http_creds,
        default="",
        help=(
            "Provide the user specific HTTP credentials required to access gerrit API. "
            f"By default, these are read from the environment variable `{ENV_GERRIT_HTTP_CREDS}`. "
            "Set it up using `https://review.lan.tribe29.com/settings/#HTTPCredentials`."
        ),
    )

    parser.add_argument(
        "--age",
        dest="age",
        metavar="LAST_N_DAYS",
        type=int,
        help="Filter and list werks added in the last `N` days.",
    )

    parser.add_argument(
        "--status",
        dest="status",
        action="store",
        type=str,
        choices=TChangeStatus,
        default=TChangeStatus.ALL,
        help=(
            "List werks based on status of the gerrit change. "
            "By default, werks corresponding to `all` gerrit changes are listed."
        ),
    )

    parser.add_argument(
        "--dir-csv",
        dest="dir_csv",
        metavar="DIR",
        type=str,
        help=(
            "Directory where the list of werks is stored as a CSV file. "
            "By default, the directory where this script is executed from."
        ),
        default=str(Path().cwd()),
    )

    args, _ = parser.parse_known_args(namespace=TCliArgs)
    return args


def create_search_query(args: type[TCliArgs]) -> str:
    """Prepare a search query to scrape changes in gerrit for Werks, based on the CLI arguments."""
    age = "-age"
    branch = "branch"
    status = "status"

    query = {
        "project": "check_mk",
        "path": r"^.*werks/.*md",
        status: "",
        branch: "",
        age: "",
    }

    query[age] = f"{args.age}d" if args.age else ""
    branch_version = (
        args.cmk_version.split("p") if "p" in args.cmk_version else args.cmk_version.split("b")
    )[0]

    query[branch] = "master" if branch_version == MASTER_BRANCH else branch_version
    query[status] = "" if args.status == TChangeStatus.ALL else args.status
    return "+".join([f'{key}:"{query[key]}"' for key in query if query[key]])


def collect_changes_with_werks(args: type[TCliArgs], client: GerritClient) -> list[CSVEntry]:
    details = []
    reverted_changes = []
    for change in client.changes_api.get_changes(query=create_search_query(args)):
        # ignore abandoned changes.
        if change.status is TChangeStatus.ABANDONED:
            continue

        # do not include changes which revert a Werk.
        # TODO: improve revert detection mechanism.
        if change.revert_of != 0:
            reverted_changes.append(change.revert_of)
            continue

        if (
            # ignore changes which are reverted.
            change.virtual_id_number in reverted_changes
            # ignore changes which are WIP.
            or change.work_in_progress
        ):
            continue

        try:
            werk = werk_details(client, change)
        except FileNotFoundError as exc:
            exc.add_note("Skip change...")
            print(exc)
            continue

        if werk.VERSION == args.cmk_version:
            details.append(
                CSVEntry(
                    change_id=change.virtual_id_number,
                    change_status=change.status,
                    werk_id=f"https://checkmk.com/werk/{werk.ID}",
                    werk_summary=werk.SUMMARY,
                    werk_impact=werk.IMPACT,
                )
            )
    return details


def main() -> None:
    args = parsed_arguments()
    client = GerritClient(args.username, args.http_creds)

    # parse changes
    collect_changes_with_werks(args, client)


if __name__ == "__main__":
    main()
