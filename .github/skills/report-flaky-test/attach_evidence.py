#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Attach CI evidence files to a Jira ticket."""

import argparse
import os
import sys

from jira import JIRA


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ticket_key", help="Jira ticket key, e.g. CMK-12345")
    parser.add_argument(
        "files",
        nargs="+",
        help="Files to attach (text logs, screenshots, etc.)",
    )
    args = parser.parse_args()

    token = os.environ.get("JIRA_API_TOKEN")
    if not token:
        sys.exit("Error: JIRA_API_TOKEN environment variable is not set")

    jira = JIRA("https://jira.lan.tribe29.com", token_auth=token)
    issue = jira.issue(args.ticket_key)

    for path in args.files:
        jira.add_attachment(issue=issue, attachment=path)
        print(f"Attached {path} to {args.ticket_key}")


if __name__ == "__main__":
    main()
